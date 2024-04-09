import os
from datetime import date, datetime
import json
from os.path import exists
import re

from typing import List, Dict, Union, Any
from univention.management.console.log import MODULE

from univention.bildungslogin.handlers import (
    AssignmentHandler,
    BiloCreateError,
    LicenseHandler,
    ObjectType
)

from univention.bildungslogin.models import LicenseType, Role, Status
from univention.udm.exceptions import SearchLimitReached

from .constants import JSON_PATH, JSON_DIR, CACHE_BUILD_SCRIPT

today = date.today()


class LdapUser:
    ucsschoolRole = None  # type: list

    def __init__(self,
                 entry_uuid,
                 entry_dn,
                 object_class,
                 user_id,
                 given_name,
                 sn,
                 ucsschool_school,
                 ucsschool_role):
        self.objectClass = object_class
        self.entry_dn = entry_dn
        self.ucsschoolRole = ucsschool_role
        self.entryUUID = entry_uuid
        self.uid = user_id
        self.userId = user_id
        self.givenName = given_name
        self.sn = sn
        self.ucsschoolSchool = ucsschool_school

    def get_roles(self):
        roles = []
        for role in self.ucsschoolRole:
            roles.append(role.split(':', 1)[0])
        return roles


class LdapLicense:
    def __init__(self, entry_uuid, entry_dn, object_class, bildungslogin_license_code,
                 bildungslogin_license_special_type, bildungslogin_product_id, bildungslogin_license_school,
                 bildungslogin_license_type, bildungslogin_ignored_for_display, bildungslogin_delivery_date,
                 bildungslogin_license_quantity=0,
                 bildungslogin_validity_start_date=None,
                 bildungslogin_validity_end_date=None, bildungslogin_purchasing_reference=None,
                 bildungslogin_utilization_systems=None, bildungslogin_validity_duration=None,
                 bildungslogin_usage_status=None, bildungslogin_expiry_date=None, bildungslogin_validity_status=None,
                 quantity_assigned=None,
                 user_strings=None, groups=None, publisher=None, volume_quantity=None):
        if groups:
            self.groups = groups
        else:
            self.groups = []
        self.bildungsloginValidityDuration = bildungslogin_validity_duration
        self.bildungsloginUtilizationSystems = bildungslogin_utilization_systems
        self.bildungsloginPurchasingReference = bildungslogin_purchasing_reference
        self.bildungsloginDeliveryDate = datetime.strptime(bildungslogin_delivery_date,
                                                           '%Y-%m-%d').date()

        if bildungslogin_validity_start_date is not None:
            try:
                self.bildungsloginValidityStartDate = datetime.strptime(bildungslogin_validity_start_date,
                                                                        '%Y-%m-%d').date()
            except ValueError:
                self.bildungsloginValidityStartDate = None
        else:
            self.bildungsloginValidityStartDate = None

        if bildungslogin_validity_end_date is not None:
            self.bildungsloginValidityEndDate = datetime.strptime(bildungslogin_validity_end_date, '%Y-%m-%d').date()
        else:
            self.bildungsloginValidityEndDate = None

        self.bildungsloginIgnoredForDisplay = int(bildungslogin_ignored_for_display)
        if bildungslogin_license_type:
            self.bildungsloginLicenseType = bildungslogin_license_type
        else:
            self.bildungsloginLicenseType = ''
        self.bildungsloginLicenseSchool = bildungslogin_license_school
        self.bildungsloginProductId = bildungslogin_product_id
        self.bildungsloginLicenseSpecialType = bildungslogin_license_special_type
        self.objectClass = object_class
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.bildungsloginLicenseCode = bildungslogin_license_code
        self.bildungsloginLicenseQuantity = bildungslogin_license_quantity
        self.quantity = int(bildungslogin_license_quantity)
        self.quantity_assigned = int(quantity_assigned)
        self.publisher = publisher
        self.user_strings = user_strings
        self.medium = None

        self.bildungsloginUsageStatus = bildungslogin_usage_status
        self.bildungsloginValidityStatus = bildungslogin_validity_status

        if bildungslogin_expiry_date is not None:
            try:
                self.bildungsloginExpiryDate = datetime.strptime(bildungslogin_expiry_date,
                                                                 '%Y-%m-%d').date()
            except ValueError:
                self.bildungsloginExpiryDate = None

        if self.bildungsloginLicenseType == LicenseType.VOLUME and volume_quantity:
            self.volume_quantity = volume_quantity

    def add_user_string(self, user_string):
        self.user_strings.append(user_string)

    def remove_duplicates(self):
        self.user_strings = list(dict.fromkeys(self.user_strings))

    def match_user_regex(self, user_pattern):
        for user_string in self.user_strings:
            if user_pattern.match(user_string):
                return True
        return False

    @property
    def quantity_available(self):
        if self.is_expired or self.bildungsloginValidityStatus == '0':
            return 0
        else:
            if self.quantity_assigned > self.quantity:
                return 0
            else:
                if hasattr(self, 'volume_quantity'):
                    return self.volume_quantity - self.quantity_assigned
                else:
                    return self.quantity - self.quantity_assigned

    @property
    def quantity_expired(self):
        if self.is_expired:
            if self.quantity_assigned > self.quantity:
                return 0
            else:
                return self.quantity - self.quantity_assigned
        else:
            return 0

    @property
    def is_expired(self):
        """ Check if license is expired """
        if self.bildungsloginValidityEndDate is None:
            return False
        return self.bildungsloginValidityEndDate < date.today()

    @property
    def is_available(self):
        if self.bildungsloginValidityStatus == '0':
            return False
        if self.bildungsloginExpiryDate and self.bildungsloginExpiryDate < today:
            return False
        if self.bildungsloginLicenseType in [LicenseType.SINGLE, LicenseType.VOLUME]:
            return self.quantity_available > 0 and not self.is_expired
        elif self.bildungsloginLicenseType == LicenseType.WORKGROUP or self.bildungsloginLicenseType == LicenseType.SCHOOL:
            return self.quantity_assigned == 0 and not self.is_expired
        return False

    @property
    def is_group_type(self):
        if self.bildungsloginLicenseType in [LicenseType.SINGLE, LicenseType.VOLUME]:
            return False
        return True

    def get_cache_dictionary(self):
        return {
            'entryUUID': self.entryUUID,
            'quantity_assigned': self.quantity_assigned,
            'groups': self.groups,
            'user_strings': self.user_strings,
        }


class LdapAssignment:
    def __init__(self, entry_uuid, entry_dn, object_class, bildungslogin_assignment_status,
                 bildungslogin_assignment_assignee, bildungslogin_assignment_time_of_assignment):

        if bildungslogin_assignment_time_of_assignment:
            self.bildungsloginAssignmentTimeOfAssignment = datetime.strptime(
                bildungslogin_assignment_time_of_assignment,
                '%Y-%m-%d').date()
        else:
            self.bildungsloginAssignmentTimeOfAssignment = None
        self.objectClass = object_class
        self.bildungsloginAssignmentStatus = bildungslogin_assignment_status
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.bildungsloginAssignmentAssignee = bildungslogin_assignment_assignee

    def remove(self):
        self.bildungsloginAssignmentAssignee = ''
        self.bildungsloginAssignmentStatus = Status.AVAILABLE
        self.bildungsloginAssignmentTimeOfAssignment = None

    def assign(self, entry_uuid):
        self.bildungsloginAssignmentAssignee = entry_uuid
        self.bildungsloginAssignmentStatus = Status.ASSIGNED
        self.bildungsloginAssignmentTimeOfAssignment = datetime.now().date()

    def get_cache_dictionary(self):
        return {
            'entryUUID': self.entryUUID,
            'bildungsloginAssignmentAssignee': self.bildungsloginAssignmentAssignee,
            'bildungsloginAssignmentStatus': self.bildungsloginAssignmentStatus,
            'bildungsloginAssignmentTimeOfAssignment': self.bildungsloginAssignmentTimeOfAssignment.strftime(
                '%Y-%m-%d') if self.bildungsloginAssignmentTimeOfAssignment else '',
        }


class LdapSchool:
    def __init__(self, entry_uuid, entry_dn, object_class, ou):
        self.objectClass = object_class
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.ou = ou


class LdapGroup:
    def __init__(self, entry_uuid, entry_dn, cn, ucsschool_role, member_uids):
        self.memberUid = member_uids
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.cn = cn
        self.ucsschoolRole = ucsschool_role

    @property
    def name(self):
        """
        In LDAP classes/workgroups are prepended with the school name:
        Example: DEMOSCHOOL-Group

        This function is meant to extract the name of the group
        """
        _, name = self.cn.split('-', 1)
        return name


class LdapMetaData:
    def __init__(self, entry_uuid, entry_dn, bildungslogin_product_id, bildungslogin_metadata_title,
                 bildungslogin_metadata_publisher, bildungslogin_meta_data_cover, bildungslogin_meta_data_cover_small,
                 bildungslogin_meta_data_author, bildungslogin_meta_data_description):
        self.bildungsloginMetaDataDescription = bildungslogin_meta_data_description
        self.bildungsloginMetaDataAuthor = bildungslogin_meta_data_author
        self.entry_uuid = entry_uuid
        self.entry_dn = entry_dn
        self.bildungsloginProductId = bildungslogin_product_id
        self.bildungsloginMetaDataTitle = bildungslogin_metadata_title
        self.bildungsloginMetaDataPublisher = bildungslogin_metadata_publisher
        self.bildungsloginMetaDataCover = bildungslogin_meta_data_cover
        self.bildungsloginMetaDataCoverSmall = bildungslogin_meta_data_cover_small


class LdapRepository:
    _publishers = None  # type: List[str] | None
    _workgroups_by_uuid = None  # type: Dict[str, LdapGroup] | None
    _workgroups_by_cn = None  # type: Dict[str, LdapGroup] | None
    _workgroups_by_dn = None  # type: Dict[str, LdapGroup] | None
    _workgroups_grouped_by_uid = None  # type: Dict[str, List[LdapGroup]] | None
    _classes_by_uuid = None  # type: Dict[str, LdapGroup] | None
    _classes_by_cn = None  # type: Dict[str, LdapGroup] | None
    _classes_by_dn = None  # type: Dict[str, LdapGroup] | None
    _classes_grouped_by_uid = None  # type: Dict[str, List[LdapGroup]] | None
    _users_by_uuid = None  # type: Dict[str, LdapUser] | None
    _users_by_uid = None  # type: Dict[str, LdapUser] | None
    _metadata_by_productid = None  # type: Dict[str, LdapMetaData] | None
    _licenses_by_uuid = None  # type: Dict[str, LdapLicense] | None
    _licenses_by_dn = None  # type: Dict[str, LdapLicense] | None
    _licenses_by_code = None  # type: Dict[str, LdapLicense] | None
    _licenses_grouped_by_school_and_product_id = None  # type: Dict[str, Dict[str, List[LdapLicense]]] | None
    _schools_by_uuid = None  # type: Dict[str, LdapSchool] | None
    _schools_by_ou = None  # type: Dict[str, LdapSchool] | None
    _assignments_by_uuid = None  # type: Dict[str, LdapAssignment] | None
    _assignments_grouped_by_dn = None  # type: Dict[str, List[LdapAssignment]] | None
    _current_school = None

    def __init__(self):
        self._timestamp = None
        self._clear()

    def update(self, school, start_up=False):

        if school:
            school_changed = school != self._current_school
        else:
            school_changed = False

        cache_path = JSON_DIR + 'schools/' + str(school if school_changed else self._current_school) + '/cache.json'

        if not exists(cache_path):
            MODULE.error('JSON file not found at ' + cache_path + '. Please check if it is updating.')
            if not start_up:
                raise Exception("JSON file not found at " + cache_path + ". Please check if it is updating.")
            return

        stat = os.stat(cache_path)
        file_time = stat.st_mtime

        if school_changed or self._timestamp is None or file_time > self._timestamp:
            self._current_school = school
            self._clear()
            f = open(cache_path, 'r')
            json_string = f.read()
            f.close()
            json_dictionary = json.loads(json_string)
            self._process_entries(json_dictionary)
            self._timestamp = file_time

        biggest_timestamp = self._timestamp
        updates = []
        for (dirpath, dirnames, filenames) in os.walk(JSON_DIR + 'schools/' + self._current_school + '/'):
            for filename in filenames:
                regex = re.compile('license-.*json')
                if regex.match(filename):
                    timestamp = os.stat(dirpath + filename).st_mtime
                    if self._timestamp < timestamp:
                        updates.append(dirpath + filename)
                        if biggest_timestamp < timestamp:
                            biggest_timestamp = timestamp
            break

        self._timestamp = biggest_timestamp
        self.apply_json_files(updates)

    def apply_json_files(self, filepaths):
        license_updates = []
        assignment_updates = []
        delete_licenses = []
        delete_assignments = []
        license_object_to_deletes = []
        assignment_object_to_deletes = []

        for filepath in filepaths:
            f = open(filepath, 'r')
            json_string = f.read()
            f.close()
            json_dictionary = json.loads(json_string)
            if 'deleted' in json_dictionary and json_dictionary['deleted']:
                delete_licenses.append(json_dictionary['license'])
                delete_assignments += json_dictionary['assignments']
            else:
                license_updates.append(json_dictionary['license'])
                assignment_updates += json_dictionary['assignments']

        for _license in self._licenses_by_uuid.values():
            if len(license_updates) <= 0 and len(delete_licenses) <= 0:
                break

            deleted = False
            for delete_license in delete_licenses:
                if _license.entryUUID == delete_license['entryUUID']:
                    license_object_to_deletes.append(_license)
                    deleted = True
                    break

            if not deleted:
                for license_update in license_updates:
                    if _license.entryUUID == license_update['entryUUID']:
                        _license.user_strings = license_update['user_strings']
                        _license.groups = license_update['groups']
                        _license.quantity_assigned = license_update['quantity_assigned']
                        license_updates.remove(license_update)
                        break
        for _assignment in self._assignments_by_uuid.values():
            if len(assignment_updates) <= 0 and len(delete_assignments) <= 0:
                break

            deleted = False
            for delete_assignment in delete_assignments:
                if _assignment.entryUUID == delete_assignment['entryUUID']:
                    assignment_object_to_deletes.append(_assignment)
                    deleted = True
                    break

            if not deleted:
                for assignment_update in assignment_updates:
                    if _assignment.entryUUID == assignment_update['entryUUID']:
                        _assignment.bildungsloginAssignmentAssignee = assignment_update[
                            'bildungsloginAssignmentAssignee']
                        _assignment.bildungsloginAssignmentStatus = assignment_update['bildungsloginAssignmentStatus']
                        _assignment.bildungsloginAssignmentTimeOfAssignment = datetime.strptime(
                            assignment_update['bildungsloginAssignmentTimeOfAssignment'],
                            '%Y-%m-%d').date() if assignment_update['bildungsloginAssignmentTimeOfAssignment'] else None
                        assignment_updates.remove(assignment_update)
                        break

        for license_object_to_delete in license_object_to_deletes:
            del self._licenses_by_uuid[license_object_to_delete.entryUUID]

        for assignment_object_to_delete in assignment_object_to_deletes:
            del self._assignments_by_uuid[assignment_object_to_delete.entryUUID]

    def get_license_by_uuid(self, uuid):
        # type: (str) -> LdapLicense
        return self._licenses_by_uuid.get(uuid)

    def get_assignment_by_uuid(self, uuid):
        return self._assignments_by_uuid.get(uuid)

    def get_license_by_dn(self, dn):
        # type: (str) -> LdapLicense
        return self._licenses_by_dn.get(dn)

    def count_objects(self):
        return len(self._users_by_uuid) + len(self._workgroups_by_uuid) + len(self._licenses_by_uuid) + len(self._assignments_by_uuid) + len(
            self._schools_by_uuid) + len(self._classes_by_uuid)

    def _clear(self):
        self._users_by_uuid = {}
        self._users_by_uid = {}
        self._licenses_by_uuid = {}
        self._licenses_by_dn = {}
        self._licenses_by_code = {}
        self._licenses_grouped_by_school_and_product_id = {}
        self._assignments_by_uuid = {}
        self._assignments_grouped_by_dn = {}
        self._schools_by_uuid = {}
        self._schools_by_ou = {}
        self._workgroups_by_uuid = {}
        self._workgroups_by_cn = {}
        self._workgroups_by_dn = {}
        self._workgroups_grouped_by_uid = {}
        self._classes_by_uuid = {}
        self._classes_by_cn = {}
        self._classes_by_dn = {}
        self._classes_grouped_by_uid = {}
        self._metadata_by_productid = {}
        self._publishers = []

    def _process_entries(self, entries):
        for entry in entries['users']:
            user = LdapUser(
                entry["entryUUID"],
                entry["entry_dn"],
                entry["objectClass"],
                entry["uid"],
                entry["givenName"],
                entry["sn"],
                entry["ucsschoolSchool"],
                entry["ucsschoolRole"],
            )
            self._users_by_uuid.update({
                entry["entryUUID"]: user
            })
            self._users_by_uid.update({
                entry["uid"]: user
            })
        for entry in entries['licenses']:
            _license = LdapLicense(
                entry_uuid=entry['entryUUID'],
                entry_dn=entry['entry_dn'],
                object_class=entry['objectClass'],
                bildungslogin_license_code=entry['bildungsloginLicenseCode'],
                bildungslogin_license_special_type=entry[
                    'bildungsloginLicenseSpecialType'],
                bildungslogin_product_id=entry['bildungsloginProductId'],
                bildungslogin_license_school=entry['bildungsloginLicenseSchool'],
                bildungslogin_license_type=entry['bildungsloginLicenseType'],
                bildungslogin_ignored_for_display=entry['bildungsloginIgnoredForDisplay'],
                bildungslogin_delivery_date=entry['bildungsloginDeliveryDate'],
                bildungslogin_license_quantity=entry['bildungsloginLicenseQuantity'],
                bildungslogin_validity_start_date=entry[
                    'bildungsloginValidityStartDate'] if 'bildungsloginValidityStartDate'
                                                         in entry else None,
                bildungslogin_validity_end_date=entry[
                    'bildungsloginValidityEndDate'] if 'bildungsloginValidityEndDate'
                                                       in entry else None,
                bildungslogin_purchasing_reference=entry[
                    'bildungsloginPurchasingReference'] if 'bildungsloginPurchasingReference'
                                                           in entry else None,
                bildungslogin_utilization_systems=entry[
                    'bildungsloginUtilizationSystems'],
                bildungslogin_validity_duration=entry['bildungsloginValidityDuration'],
                quantity_assigned=entry['quantity_assigned'],
                user_strings=entry['user_strings'],
                groups=entry['groups'],
                publisher=entry['bildungsloginLicenseProvider'],
                bildungslogin_validity_status=entry['bildungsloginValidityStatus'],
                bildungslogin_usage_status=entry['bildungsloginUsageStatus'],
                bildungslogin_expiry_date=entry['bildungsloginExpiryDate'],
                volume_quantity=entry.get('volume_quantity'))
            self._licenses_by_uuid.update({
                entry["entryUUID"]: _license
            })
            self._licenses_by_dn.update({
                ','.join(entry["entry_dn"].split(',')[1:]): _license
            })
            self._licenses_by_code.update({
                entry["bildungsloginLicenseCode"]: _license
            })
            _school = entry['bildungsloginLicenseSchool']
            _product_id = entry['bildungsloginProductId']
            if self._licenses_grouped_by_school_and_product_id.get(_school) is None:
                self._licenses_grouped_by_school_and_product_id[_school] = {}
            if self._licenses_grouped_by_school_and_product_id.get(_school).get(_product_id) is None:
                self._licenses_grouped_by_school_and_product_id[_school][_product_id] = []
            self._licenses_grouped_by_school_and_product_id[_school][_product_id].append(_license)

        for entry in entries['assignments']:
            _assignment = LdapAssignment(
                entry['entryUUID'],
                entry['entry_dn'],
                entry['objectClass'],
                entry['bildungsloginAssignmentStatus'],
                entry['bildungsloginAssignmentAssignee'] if 'bildungsloginAssignmentAssignee' in entry else '',
                entry['bildungsloginAssignmentTimeOfAssignment'] if 'bildungsloginAssignmentTimeOfAssignment' in entry else '')
            self._assignments_by_uuid.update({
                entry["entryUUID"]: _assignment
            })
            _dn = ','.join(entry["entry_dn"].split(',')[1:])
            if self._assignments_grouped_by_dn.get(_dn) is None:
                self._assignments_grouped_by_dn[_dn] = []
            self._assignments_grouped_by_dn[_dn].append(_assignment)

        for entry in entries['schools']:
            _school = LdapSchool(
                entry['entryUUID'],
                entry['entry_dn'],
                entry['objectClass'],
                entry['ou']
            )
            self._schools_by_uuid.update({
                entry["entryUUID"]: _school
            })
            self._schools_by_ou.update({
                entry["ou"]: _school
            })

        for entry in entries['workgroups']:
            _workgroup = LdapGroup(
                entry['entryUUID'],
                entry['entry_dn'],
                entry['cn'],
                entry['ucsschoolRole'],
                entry['memberUid']
            )
            self._workgroups_by_uuid.update({
                entry["entryUUID"]: _workgroup
            })
            self._workgroups_by_cn.update({
                entry["cn"]: _workgroup
            })
            self._workgroups_by_dn.update({
                entry["entry_dn"]: _workgroup
            })
            for uid in entry['memberUid']:
                if self._workgroups_grouped_by_uid.get(uid) is None:
                    self._workgroups_grouped_by_uid[uid] = []
                self._workgroups_grouped_by_uid[uid].append(_workgroup)
        for entry in entries['classes']:
            _class = LdapGroup(
                entry['entryUUID'],
                entry['entry_dn'],
                entry['cn'],
                entry['ucsschoolRole'],
                entry['memberUid']
            )
            self._classes_by_uuid.update({
                entry["entryUUID"]: _class
            })
            self._classes_by_cn.update({
                entry["cn"]: _class
            })
            self._classes_by_dn.update({
                entry["entry_dn"]: _class
            })
            for uid in entry['memberUid']:
                if self._classes_grouped_by_uid.get(uid) is None:
                    self._classes_grouped_by_uid[uid] = []
                self._classes_grouped_by_uid[uid].append(_class)
        for entry in entries['metadata']:
            _metadata = LdapMetaData(
                entry['entryUUID'],
                entry['entry_dn'],
                entry['bildungsloginProductId'],
                entry['bildungsloginMetaDataTitle'],
                entry['bildungsloginMetaDataPublisher'],
                entry['bildungsloginMetaDataCover'],
                entry['bildungsloginMetaDataCoverSmall'],
                entry['bildungsloginMetaDataAuthor'],
                entry['bildungsloginMetaDataDescription'],
            )
            self._metadata_by_productid.update({
                entry["bildungsloginProductId"]: _metadata
            })
            if 'bildungsloginMetaDataPublisher' in entry:
                self._publishers.append(entry['bildungsloginMetaDataPublisher'])
        self._publishers = list(dict.fromkeys(self._publishers))

        for _license in self._licenses_by_uuid.values():
            _license.medium = self.get_metadata_by_product_id(_license.bildungsloginProductId)

    def get_publishers(self):
        return self._publishers

    def get_user(self, userid):
        return self._users_by_uid.get(userid)

    def _get_users_by_school(self, school):
        users = []
        for user in self._users_by_uuid.values():
            if school in user.ucsschoolSchool:
                users.append(user)
        return users

    def _filter_user_by_group(self, users, workgroup):
        filtered_users = []
        for user in users:
            if user.userId in workgroup.memberUid:
                filtered_users.append(user)

        return filtered_users

    def filter_users(self, pattern, school, workgroup, school_class):
        users = []
        pattern = re.compile(pattern.replace('*', '.*'))

        for user in self._get_users_by_school(school):
            if pattern.match(user.userId) or pattern.match(user.givenName) or pattern.match(user.sn):
                users.append(user)

        if workgroup != '__all__' and workgroup != '':
            workgroup = self.get_workgroup_by_dn(workgroup)
            users = self._filter_user_by_group(users, workgroup)

        if school_class != '__all__' and school_class != '':
            school_class = self.get_class_by_dn(school_class)
            users = self._filter_user_by_group(users, school_class)

        return users

    def filter_metadata(self, pattern):
        filtered_metadata = []
        pattern = re.compile(pattern.lower().replace('*', '.*'))
        for metadata in self._metadata_by_productid.values():
            if pattern.match(metadata.bildungsloginProductId.lower()) or pattern.match(
                    metadata.bildungsloginMetaDataPublisher.lower()) or pattern.match(
                metadata.bildungsloginMetaDataTitle.lower()):
                filtered_metadata.append(metadata)
        return filtered_metadata

    def _match_license_by_product(self, license, regex):
        metadata = license.medium
        return regex.match(metadata.bildungsloginMetaDataTitle.lower()) if metadata else False

    def _match_license_search_pattern(self, license, regex):
        if regex.match(license.bildungsloginLicenseCode.lower()):
            return True

        if license.medium:
            return regex.match(
                license.medium.bildungsloginMetaDataTitle.lower()) or regex.match(
                license.medium.bildungsloginProductId.lower())

        return False

    def get_user_to_medium_and_license(self, school):
        result = []  # type: List[Dict[str, Union[LdapLicense, LdapMetaData, None, List[Any], LdapUser, LdapAssignment]]]

        for license in self._licenses_by_uuid.values():  # type: LdapLicense
            if (license.bildungsloginLicenseType in [LicenseType.SINGLE, LicenseType.VOLUME]
                    and license.bildungsloginLicenseSchool == school):
                assignments = self.get_assignments_by_license(license)
                for assignment in assignments:  # type: LdapAssignment
                    user = self.get_user_by_uuid(assignment.bildungsloginAssignmentAssignee)
                    if user is not None:
                        result.append({
                            'user': user,
                            'product': self.get_metadata_by_product_id(license.bildungsloginProductId),
                            'license': license,
                            'workgroups': self.get_workgroups_by_user(user),
                            'classes': self.get_classes_by_user(user),
                            'assignment': assignment
                        })

        return result

    def filter_user_to_medium_and_license(self, school,
                                          import_date_start=None,
                                          import_date_end=None,
                                          class_group=None,
                                          workgroup=None,
                                          username=None,
                                          medium=None,
                                          medium_id=None,
                                          publisher=None,
                                          valid_status=None,
                                          usage_status=None,
                                          not_provisioned=None
                                          ):
        results = self.get_user_to_medium_and_license(school)

        if import_date_start:
            results = filter(lambda item: item['license'].bildungsloginDeliveryDate and item[
                'license'].bildungsloginDeliveryDate >= import_date_start, results)

        if import_date_end:
            results = filter(lambda item: item['license'].bildungsloginDeliveryDate and item[
                'license'].bildungsloginDeliveryDate <= import_date_end, results)

        if class_group:
            results = filter(lambda item: class_group in [group.entry_dn for group in item['classes']], results)

        if workgroup:
            results = filter(lambda item: workgroup in [group.entry_dn for group in item['workgroups']], results)

        if username and username != '*':
            user_pattern = re.compile(username.lower().replace('*', '.*'))
            results = filter(lambda item: user_pattern.match(item['user'].uid.lower()), results)

        if medium and medium != '*':
            medium = re.compile(medium.lower().replace('*', '.*'))
            results = filter(lambda item: medium.match(item['product'].bildungsloginMetaDataTitle.lower()), results)

        if medium_id and medium_id != '*':
            medium_id = re.compile(medium_id.lower().replace('*', '.*'))
            results = filter(lambda item: medium_id.match(item['product'].bildungsloginProductId.lower()), results)

        if publisher:
            results = filter(
                lambda item: publisher == item['license'].publisher if item['license'].publisher else False,
                results)

        if valid_status:
            if valid_status == '-':
                results = filter(lambda item: item['license'].bildungsloginValidityStatus == '', results)
            else:
                results = filter(lambda item: item['license'].bildungsloginValidityStatus == valid_status, results)

        if usage_status:
            if usage_status == '-':
                results = filter(lambda item: item['license'].bildungsloginUsageStatus == '', results)
            else:
                results = filter(lambda item: item['license'].bildungsloginUsageStatus == usage_status, results)

        if not_provisioned:
            results = filter(lambda item: item['assignment'].bildungsloginAssignmentStatus == Status.ASSIGNED, results)

        return results

    def get_single_license_assigned_users(self, school):
        result = []

        for license in self._licenses_by_uuid.values():
            if license.bildungsloginLicenseType in [LicenseType.SINGLE, LicenseType.VOLUME] and license.bildungsloginLicenseSchool == school:
                assignments = self.get_assignments_by_license(license)
                for assignment in assignments:
                    if assignment.bildungsloginAssignmentStatus != Status.AVAILABLE:
                        user = self.get_user_by_uuid(assignment.bildungsloginAssignmentAssignee)
                        product = self.get_metadata_by_product_id(license.bildungsloginProductId)
                        if user:
                            result.append([
                                user.userId,
                                ', '.join(group.cn for group in self.get_classes_by_user(user)),
                                ', '.join(group.cn for group in self.get_workgroups_by_user(user)),
                                product.bildungsloginProductId,
                                product.bildungsloginMetaDataTitle,
                                license.bildungsloginLicenseCode,
                                LicenseType.label(license.bildungsloginLicenseType),
                                Status.label(assignment.bildungsloginAssignmentStatus),
                            ])
        return result

    def filter_licenses(self, product_id=None, school=None, license_types=None,
                        is_advanced_search=None,
                        time_from=None,
                        time_to=None,
                        only_available_licenses=None,
                        publisher=None,
                        user_pattern=None,
                        product=None,
                        license_code=None,
                        pattern=None,
                        restrict_to_this_product_id=None,
                        sizelimit=None,
                        school_class=None,
                        valid_status=None,
                        usage_status=None,
                        not_provisioned=None,
                        only_provisioned=None,
                        not_usable=None,
                        expiry_date_from=None,
                        expiry_date_to=None,
                        ):

        licenses = self._licenses_by_uuid.values()
        if restrict_to_this_product_id:
            licenses = filter(lambda _license: _license.bildungsloginProductId == restrict_to_this_product_id, licenses)

        if school:
            licenses = filter(lambda _license: _license.bildungsloginLicenseSchool == school, licenses)

        if product_id and product_id != '*':
            product_id = re.compile(product_id.lower().replace('*', '.*'))
            licenses = filter(lambda _license: product_id.match(_license.bildungsloginProductId.lower()), licenses)

        if license_types:
            licenses = filter(lambda _license: _license.bildungsloginLicenseType in license_types, licenses)

        if is_advanced_search:
            if time_from:
                licenses = filter(lambda _license: _license.bildungsloginDeliveryDate >= time_from, licenses)

            if time_to:
                licenses = filter(lambda _license: _license.bildungsloginDeliveryDate <= time_to, licenses)

        if pattern and pattern != '*':
            pattern = re.compile(pattern.lower().replace('*', '.*'))
            licenses = filter(
                lambda _license: self._match_license_search_pattern(_license, pattern), licenses)

        if publisher:
            licenses = filter(
                lambda _license: publisher == _license.publisher if _license.publisher else False,
                licenses)

        if only_available_licenses:
            licenses = filter(lambda _license: _license.is_available, licenses)

        if user_pattern and user_pattern != '*':
            user_pattern = re.compile(user_pattern.lower().replace('*', '.*'))
            licenses = filter(lambda _license: _license.match_user_regex(user_pattern), licenses)

        if license_code and license_code != '*':
            license_code = re.compile(license_code.lower().replace('*', '.*'))
            licenses = filter(lambda _license: license_code.match(
                _license.bildungsloginLicenseCode.lower()) if _license.bildungsloginLicenseCode else False,
                              licenses)

        if product and product != '*':
            product = re.compile(product.lower().replace('*', '.*'))
            licenses = filter(lambda _license: self._match_license_by_product(_license, product), licenses)

        if school_class:
            licenses = filter(lambda _license: school_class in _license.groups, licenses)

        if valid_status:
            if valid_status == '-':
                licenses = filter(lambda _license: _license.bildungsloginValidityStatus == '', licenses)
            else:
                licenses = filter(lambda _license: _license.bildungsloginValidityStatus == valid_status, licenses)

        if usage_status:
            if usage_status == '-':
                licenses = filter(lambda _license: _license.bildungsloginUsageStatus == '', licenses)
            else:
                licenses = filter(lambda _license: _license.bildungsloginUsageStatus == usage_status, licenses)

        if expiry_date_from:
            licenses = filter(lambda
                                  _license: _license.bildungsloginExpiryDate and _license.bildungsloginExpiryDate >= expiry_date_from,
                              licenses)

        if expiry_date_to:
            licenses = filter(lambda
                                  _license: _license.bildungsloginExpiryDate and _license.bildungsloginExpiryDate <= expiry_date_to,
                              licenses)

        if not_provisioned:
            licenses = filter(lambda _license: self.is_license_only_assigned(_license), licenses)
            
        if only_provisioned:
            licenses = filter(lambda _license: self.is_license_only_provisioned(_license), licenses)

        if not_usable:
            licenses = filter(lambda _license: self.is_license_not_usable(_license), licenses)

        if sizelimit:
            if len(licenses) > sizelimit:
                raise SearchLimitReached

        return licenses

    def is_license_not_usable(self, license):
        """

        @type license: LdapLicense
        """
        if hasattr(license, 'volume_quantity') and license.volume_quantity == 0:
            return True
        if license.bildungsloginLicenseType == LicenseType.SINGLE:
            assignments = self.get_assignments_by_license(license)
            # single licenses only have one assignment
            assignment = assignments[0]
            if assignment.bildungsloginAssignmentStatus != Status.AVAILABLE:
                return not bool(self.get_user_by_uuid(assignment.bildungsloginAssignmentAssignee))
        return False

    def is_license_only_assigned(self, license):
        if license.bildungsloginLicenseType in [LicenseType.SCHOOL, LicenseType.WORKGROUP]:
            return False

        assignments = self.get_assignments_by_license(license)
        for assignment in assignments:
            if assignment.bildungsloginAssignmentStatus == Status.ASSIGNED:
                return True

        return False
    
    def is_license_only_provisioned(self, license):
        assignments = self.get_assignments_by_license(license)
        for assignment in assignments:
            if assignment.bildungsloginAssignmentStatus == Status.PROVISIONED:
                return True

        return False

    def get_metadata_by_product_id(self, product_id):
        return self._metadata_by_productid.get(product_id)

    def get_group_by_name(self, name):
        if self.get_workgroup_by_name(name):
            return self.get_workgroup_by_name(name)
        if self.get_class_by_name(name):
            return self.get_class_by_name(name)
        return None

    def get_workgroup_by_name(self, name):
        return self._workgroups_by_cn.get(name)

    def get_class_by_name(self, name):
        return self._classes_by_cn.get(name)

    def get_workgroup_names_by_user(self, user):
        groups = []

        for group in self._workgroups_by_uuid.values():
            if user.uid in group.memberUid:
                groups.append(group.cn.split('-')[1])
        return groups

    def get_class_names_by_user(self, user):
        groups = []

        for group in self._classes_by_uuid.values():
            if user.uid in group.memberUid:
                groups.append(group.cn.split('-')[1])
        return groups

    def get_workgroup_by_dn(self, dn):
        return self._workgroups_by_dn.get(dn)

    def get_class_by_dn(self, dn):
        return self._classes_by_dn.get(dn)

    def get_group_by_uuid(self, entry_uuid):
        return dict((group.entryUUID, group) for group in self.groups).get(entry_uuid)

    def get_workgroup_by_uuid(self, entry_uuid):
        return self._workgroups_by_uuid.get(entry_uuid)

    def get_assignments_by_assignee(self, assignee):
        assignments = []
        for assignment in self._assignments_by_uuid.values():
            if assignment.bildungsloginAssignmentAssignee \
                    == assignee.entryUUID:
                assignments.append(assignment)

        return assignments

    def get_license_by_assignment(self, assignment):
        return self._licenses_by_dn.get(assignment.entry_dn)

    def get_license_by_code(self, code):
        return self._licenses_by_code.get(code)

    def get_licenses_by_codes(self, codes):
        licenses = []
        for code in codes:
            licenses.append(self.get_license_by_code(code))
        return licenses

    def get_school(self, name):
        return self._schools_by_ou.get(name)

    def get_classes_by_school(self, school):
        classes = []
        for _class in self._classes_by_uuid.values():
            if _class.ucsschoolRole == "school_class:school:" + school:
                classes.append(_class)
        return classes

    def get_classes(self, school, user):
        classes = []
        for _class in self._classes_by_uuid.values():
            if _class.ucsschoolRole == "school_class:school:" + school.ou and user.uid in _class.memberUid:
                classes.append(_class)
        return classes

    def get_workgroups_by_school(self, school):
        workgroups = []
        for workgroup in self._workgroups_by_uuid.values():
            if workgroup.ucsschoolRole == "workgroup:school:" + school:
                workgroups.append(workgroup)
        return workgroups

    def get_workgroups(self, school, user):
        workgroups = []
        for workgroup in self._workgroups_by_uuid.values():
            if workgroup.ucsschoolRole == "workgroup:school:" + school.ou and user.uid in workgroup.memberUid:
                workgroups.append(workgroup)
        return workgroups

    def get_all_workgroups(self):
        return list(self._workgroups_by_uuid.values())

    def get_user_by_uuid(self, uuid):
        return self._users_by_uuid.get(uuid)

    def get_school_by_uuid(self, entry_uuid):
        return self._schools_by_uuid.get(entry_uuid)

    @property
    def groups(self):
        return list(self._workgroups_by_uuid.values()) + list(self._classes_by_uuid.values())

    def get_assigned_users_by_license(self, license):
        users = []

        assignments = self.get_assignments_by_license(license)
        assignments = filter(lambda _assignment: _assignment.bildungsloginAssignmentStatus != 'AVAILABLE', assignments)

        if license.bildungsloginLicenseType in ['SINGLE', 'VOLUME']:
            for assignment in assignments:
                user = self.get_user_by_uuid(assignment.bildungsloginAssignmentAssignee)
                if user:
                    users.append({
                        'dateOfAssignment': assignment.bildungsloginAssignmentTimeOfAssignment,
                        'username': user.userId,
                        'status': assignment.bildungsloginAssignmentStatus,
                        'statusLabel': Status.label(assignment.bildungsloginAssignmentStatus),
                        'roles': user.get_roles(),
                        'roleLabels': Role.label(user.get_roles()),
                        'classes': self.get_class_names_by_user(user),
                        'workgroups': self.get_workgroup_names_by_user(user),
                    })
        elif license.bildungsloginLicenseType == 'WORKGROUP':
            for assignment in assignments:
                group = self.get_group_by_uuid(assignment.bildungsloginAssignmentAssignee)
                if group:
                    for member_uid in group.memberUid:
                        user = self.get_user(member_uid)
                        user_roles = []

                        if user:
                            for role in user.ucsschoolRole:
                                user_roles.append(role.split(':')[0])

                            if license.bildungsloginLicenseSpecialType == "Lehrkraft" and "teacher" not in user_roles:
                                continue

                            users.append({
                                'dateOfAssignment': assignment.bildungsloginAssignmentTimeOfAssignment,
                                'username': user.userId,
                                'status': assignment.bildungsloginAssignmentStatus,
                                'statusLabel': Status.label(assignment.bildungsloginAssignmentStatus),
                                'roles': user.get_roles(),
                                'roleLabels': Role.label(user.get_roles()),
                                'classes': self.get_class_names_by_user(user),
                                'workgroups': self.get_workgroup_names_by_user(user),
                            })
        elif license.bildungsloginLicenseType == 'SCHOOL':
            for assignment in assignments:
                _users = self._get_users_by_school(
                    self.get_school_by_uuid(assignment.bildungsloginAssignmentAssignee).ou)
                for user in _users:
                    user_roles = []

                    for role in user.ucsschoolRole:
                        user_roles.append(role.split(':')[0])

                    if license.bildungsloginLicenseSpecialType == "Lehrkraft" and "teacher" not in user_roles:
                        continue

                    users.append({
                        'dateOfAssignment': assignment.bildungsloginAssignmentTimeOfAssignment,
                        'username': user.userId,
                        'status': assignment.bildungsloginAssignmentStatus,
                        'statusLabel': Status.label(assignment.bildungsloginAssignmentStatus),
                        'roles': user.get_roles(),
                        'roleLabels': Role.label(user.get_roles()),
                        'classes': self.get_class_names_by_user(user),
                        'workgroups': self.get_workgroup_names_by_user(user),
                    })
        else:
            raise RuntimeError("Unknown license type: {}".format(license.license_type))

        return users

    def set_license_ignored(self, license_code, ignored):
        license = self.get_license_by_code(license_code)
        license.bildungsloginIgnoredForDisplay = ignored
        self.cache_single_license(license)

    def get_assignments_by_license(self, license):
        return self._assignments_grouped_by_dn.get(license.entry_dn, [])

    def get_workgroups_by_user(self, user):
        return self._workgroups_grouped_by_uid.get(user.userId, [])

    def get_classes_by_user(self, user):
        return self._classes_grouped_by_uid.get(user.userId, [])

    def get_users_by_group(self, group):
        users = []
        for user in self._users_by_uuid.values():
            if user.userId in group.memberUid:
                users.append(user)

        return users

    def add_user_to_license(self, license, user):
        if license.bildungsloginLicenseSpecialType != 'Lehrkraft' or (
                license.bildungsloginLicenseSpecialType == 'Lehrkraft' and 'teacher' in user.get_roles()):
            license.user_strings.append(user.uid)
            license.user_strings.append(user.givenName)
            license.user_strings.append(user.sn)
            license.quantity_assigned += 1
            return True
        return False

    def remove_user_from_license(self, license, user):
        if license.bildungsloginLicenseSpecialType != 'Lehrkraft' or (
                license.bildungsloginLicenseSpecialType == 'Lehrkraft' and 'teacher' in user.get_roles()):
            license.user_strings.remove(user.uid)
            license.user_strings.remove(user.givenName)
            license.user_strings.remove(user.sn)
            license.quantity_assigned -= 1

    def add_assignments(self, license_codes, object_type, object_names):
        licenses = self.get_licenses_by_codes(license_codes)
        licenses_assignments = []
        for license in licenses:
            assignments = self.get_assignments_by_license(license)
            licenses_assignments.append(
                {'license': license,
                 'assignments': assignments})

        if object_type == ObjectType.USER:
            licenses_to_use = (
                license
                for license in licenses_assignments
                for _ in range(license['license'].quantity_available)
            )
            for object_name in object_names:
                license = licenses_to_use.next()
                user = self.get_user(object_name)
                for assignment in license['assignments']:
                    if assignment.bildungsloginAssignmentStatus == Status.AVAILABLE:
                        if self.add_user_to_license(license['license'], user):
                            assignment.assign(user.entryUUID)
                        break
                self.cache_single_license(license['license'], license['assignments'])

        elif object_type == ObjectType.GROUP:
            licenses_to_use = (
                license
                for license in licenses_assignments
                for _ in range(license['license'].is_available)
            )
            for object_name in object_names:
                group = self.get_group_by_name(object_name)
                if group:
                    license = licenses_to_use.next()
                    for assignment in license['assignments']:
                        if assignment.bildungsloginAssignmentStatus == Status.AVAILABLE:
                            assignment.assign(group.entryUUID)
                            break
                    license['license'].groups.append(group.entry_dn)
                    users = self.get_users_by_group(group)
                    for user in users:
                        self.add_user_to_license(license['license'], user)
                    self.cache_single_license(license['license'], license['assignments'])
                else:
                    MODULE.error("Couldn't find the group in cache.")

        elif object_type == ObjectType.SCHOOL:
            licenses_to_use = (
                license
                for license in licenses_assignments
                for _ in range(license['license'].is_available)
            )
            for object_name in object_names:
                license = licenses_to_use.next()
                school = self.get_school(object_name)
                if school:
                    for assignment in license['assignments']:
                        if assignment.bildungsloginAssignmentStatus == Status.AVAILABLE:
                            assignment.assign(school.entryUUID)
                            break
                    users = self._get_users_by_school(school.ou)
                    for user in users:
                        self.add_user_to_license(license['license'], user)
                    self.cache_single_license(license['license'], license['assignments'])
                else:
                    MODULE.error("Couldn't find the school in cache.")

    def remove_assignments(self, license_code, object_type, object_names):
        license = self.get_license_by_code(license_code)
        assignments = self.get_assignments_by_license(license)

        if object_type == ObjectType.USER:
            for object_name in object_names:
                user = self.get_user(object_name)
                for assignment in assignments:
                    if assignment.bildungsloginAssignmentAssignee == user.entryUUID:
                        assignment.remove()
                        self.remove_user_from_license(license, user)
                        break
        elif object_type == ObjectType.GROUP:
            for object_name in object_names:
                group = self.get_workgroup_by_name(object_name)
                if group:
                    for assignment in assignments:
                        if assignment.bildungsloginAssignmentAssignee == group.entryUUID:
                            assignment.remove()
                    users = self.get_users_by_group(group)
                    for user in users:
                        self.remove_user_from_license(license, user)
                else:
                    school_classes = self.get_class_by_name(object_name)
                    if school_classes:
                        for assignment in assignments:
                            if assignment.bildungsloginAssignmentAssignee == school_classes.entryUUID:
                                assignment.remove()
                    users = self.get_users_by_group(school_classes)
                    for user in users:
                        self.remove_user_from_license(license, user)
        elif object_type == ObjectType.SCHOOL:
            for object_name in object_names:
                school = self.get_school(object_name)
                for assignment in assignments:
                    if assignment.bildungsloginAssignmentAssignee == school.entryUUID:
                        assignment.remove()
                users = self._get_users_by_school(school)
                for user in users:
                    self.remove_user_from_license(license, user)
        self.cache_single_license(license, assignments)

    @staticmethod
    def get_school_roles(user):
        school_roles = []
        for school_role in user.ucsschoolRole:
            school_roles.append(str(school_role))
        return school_roles

    @staticmethod
    def get_object_classes(obj):
        _list = set()
        for object_class in obj.objectClass:
            _list.add(object_class)

        return _list

    def get_licenses_by_product_id(self, product_id, school):
        return self._licenses_grouped_by_school_and_product_id.get(school).get(product_id, [])

    def get_class_by_uuid(self, uuid):
        return self._classes_by_uuid.get(uuid)

    def _get_license_cache_file(self, entry_uuid):
        return open(JSON_DIR + 'schools/' + self._current_school + '/license-' + entry_uuid + '.json', 'w')

    def cache_single_license(self, _license, assignments=None):
        if not assignments:
            assignments = self.get_assignments_by_license(_license)

        to_save = {
            'license': _license.get_cache_dictionary(),
            'assignments': [assignment.get_cache_dictionary() for assignment in assignments]
        }
        license_file = self._get_license_cache_file(_license.entryUUID)
        json.dump(to_save, license_file)
        license_file.close()

    def delete_licenses(self, license_codes):
        licenses = []
        for license_code in license_codes:
            _license = self.get_license_by_code(license_code)
            licenses.append(_license)
            assignments = self.get_assignments_by_license(_license)
            to_save = {
                'deleted': True,
                'license': _license.get_cache_dictionary(),
                'assignments': [assignment.get_cache_dictionary() for assignment in assignments]
            }
            license_file = self._get_license_cache_file(_license.entryUUID)
            json.dump(to_save, license_file)
            license_file.close()
        return licenses

    def cache_date(self):
        if self._current_school:
            return datetime.fromtimestamp(
                os.stat(JSON_DIR + 'schools/' + self._current_school + '/cache.json').st_mtime).strftime(
                '%d.%m.%Y %H:%M:%S')
        else:
            return ''

    def users_has_medium(self, school, medium, users):
        users = list(self.get_user(user) for user in users)
        licenses = self.get_licenses_by_product_id(medium, school)
        entry_uuids = []
        result = []
        for license in licenses:
            if license.bildungsloginLicenseType in [LicenseType.SINGLE, LicenseType.VOLUME]:
                assignments = self.get_assignments_by_license(license)
                for assignment in assignments:
                    if assignment.bildungsloginAssignmentStatus in [Status.ASSIGNED, Status.PROVISIONED]:
                        entry_uuids.append(assignment.bildungsloginAssignmentAssignee)
        for user in users:
            if user.entryUUID in entry_uuids:
                result.append(user.uid)
        return result
