import os
from datetime import date, datetime
import json
from os.path import exists
import re
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
                 user_strings=None, groups=None, publisher=None):
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

        self.bildungsloginUsageStatus = bildungslogin_usage_status if bildungslogin_usage_status else '0'
        self.bildungsloginValidityStatus = bildungslogin_validity_status if bildungslogin_validity_status else '1'

        if bildungslogin_expiry_date is not None:
            try:
                self.bildungsloginExpiryDate = datetime.strptime(bildungslogin_expiry_date,
                                                                 '%Y-%m-%d').date()
            except ValueError:
                self.bildungsloginExpiryDate = None

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
        if self.is_expired:
            return 0
        else:
            if self.quantity_assigned > self.quantity:
                return 0
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
    _publishers = None  # type: List[str]
    _workgroups = None  # type: List[LdapGroup]
    _classes = None  # type: List[LdapGroup]
    _users = None  # type: List[LdapUser]
    _metadata = None  # type: List[LdapMetaData]
    _licenses = None  # type: List[LdapLicense]
    _schools = None  # type: List[LdapSchool]

    def __init__(self):
        self._timestamp = None
        self._clear()

    def update(self, start_up=False):
        if not exists(JSON_PATH):
            MODULE.error('JSON file not found at ' + JSON_PATH + '. Please check if it is updating.')
            if not start_up:
                raise Exception("JSON file not found at " + JSON_PATH + ". Please check if it is updating.")
            return

        stat = os.stat(JSON_PATH)
        file_time = stat.st_mtime

        if self._timestamp is None or file_time > self._timestamp:
            self._clear()
            f = open(JSON_PATH, 'r')
            json_string = f.read()
            f.close()
            json_dictionary = json.loads(json_string)
            self._process_entries(json_dictionary)
            self._timestamp = file_time

        biggest_timestamp = self._timestamp
        updates = []
        for (dirpath, dirnames, filenames) in os.walk(JSON_DIR):
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

        for _license in self._licenses:
            if len(license_updates) <= 0 and len(delete_licenses) <= 0:
                break

            deleted = False
            for delete_license in delete_licenses:
                if _license.entryUUID == delete_license['entryUUID']:
                    self._licenses.remove(_license)
                    del _license
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

        for _assignment in self._assignments:
            if len(assignment_updates) <= 0 and len(delete_assignments) <= 0:
                break

            deleted = False
            for delete_assignment in delete_assignments:
                if _assignment.entryUUID == delete_assignment['entryUUID']:
                    self._assignments.remove(_assignment)
                    del _assignment
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

    def get_license_by_uuid(self, uuid):
        # type: (str) -> LdapLicense
        for license in self._licenses:
            if license.entryUUID == uuid:
                return license
        return None

    def get_assignment_by_uuid(self, uuid):
        for assignment in self._assignments:
            if assignment.entryUUID == uuid:
                return assignment
        return None

    def get_license_by_dn(self, dn):
        # type: (str) -> LdapLicense
        for license in self._licenses:
            if license.entry_dn == dn:
                return license
        return None

    def count_objects(self):
        return len(self._users) + len(self._workgroups) + len(self._licenses) + len(self._assignments) + len(
            self._schools) + len(self._classes)

    def _clear(self):
        self._users = []
        self._licenses = []
        self._assignments = []
        self._schools = []
        self._workgroups = []
        self._classes = []
        self._metadata = []
        self._publishers = []

    def _process_entries(self, entries):
        for entry in entries['users']:
            self._users.append(
                LdapUser(entry['entryUUID'], entry['entry_dn'], entry['objectClass'], entry['uid'], entry['givenName'],
                         entry['sn'], entry['ucsschoolSchool'], entry['ucsschoolRole']))
        for entry in entries['licenses']:
            self._licenses.append(LdapLicense(
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
                bildungslogin_expiry_date=entry['bildungsloginExpiryDate']))
        for entry in entries['assignments']:
            self._assignments.append(
                LdapAssignment(entry['entryUUID'], entry['entry_dn'], entry['objectClass'],
                               entry['bildungsloginAssignmentStatus'], entry[
                                   'bildungsloginAssignmentAssignee'] if 'bildungsloginAssignmentAssignee' in entry else '',
                               entry[
                                   'bildungsloginAssignmentTimeOfAssignment'] if 'bildungsloginAssignmentTimeOfAssignment' in entry else ''))
        for entry in entries['schools']:
            self._schools.append(LdapSchool(entry['entryUUID'], entry['entry_dn'], entry['objectClass'], entry['ou']))
        for entry in entries['workgroups']:
            self._workgroups.append(
                LdapGroup(entry['entryUUID'], entry['entry_dn'], entry['cn'], entry['ucsschoolRole'],
                          entry['memberUid']))
        for entry in entries['classes']:
            self._classes.append(LdapGroup(entry['entryUUID'], entry['entry_dn'], entry['cn'], entry['ucsschoolRole'],
                                           entry['memberUid']))
        for entry in entries['metadata']:
            self._metadata.append(LdapMetaData(entry['entryUUID'], entry['entry_dn'], entry['bildungsloginProductId'],
                                               entry['bildungsloginMetaDataTitle'],
                                               entry['bildungsloginMetaDataPublisher'],
                                               entry['bildungsloginMetaDataCover'],
                                               entry['bildungsloginMetaDataCoverSmall'],
                                               entry['bildungsloginMetaDataAuthor'],
                                               entry['bildungsloginMetaDataDescription']))
            if 'bildungsloginMetaDataPublisher' in entry:
                self._publishers.append(entry['bildungsloginMetaDataPublisher'])
        self._publishers = list(dict.fromkeys(self._publishers))

        for _license in self._licenses:
            _license.medium = self.get_metadata_by_product_id(_license.bildungsloginProductId)

    def get_publishers(self):
        return self._publishers

    def get_user(self, userid):
        for user in self._users:
            if hasattr(user, 'uid') and user.uid == userid:
                return user
        return None

    def _get_users_by_school(self, school):
        users = []
        for user in self._users:
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

        if workgroup != '__all__':
            workgroup = self.get_workgroup_by_dn(workgroup)
            users = self._filter_user_by_group(users, workgroup)

        if school_class != '__all__':
            school_class = self.get_class_by_dn(school_class)
            users = self._filter_user_by_group(users, school_class)

        return users

    def filter_metadata(self, pattern):
        filtered_metadata = []
        pattern = re.compile(pattern.lower().replace('*', '.*'))
        for metadata in self._metadata:
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
                        expiry_date_from=None,
                        expiry_date_to=None,
                        ):

        licenses = self._licenses
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
            license_code = re.compile(license_code.replace('*', '.*'))
            licenses = filter(lambda _license: license_code.match(
                _license.bildungsloginLicenseCode) if _license.bildungsloginLicenseCode else False,
                              licenses)

        if product and product != '*':
            product = re.compile(product.lower().replace('*', '.*'))
            licenses = filter(lambda _license: self._match_license_by_product(_license, product), licenses)

        if school_class:
            licenses = filter(lambda _license: school_class in _license.groups, licenses)

        if valid_status:
            licenses = filter(lambda _license: _license.bildungsloginValidityStatus == valid_status, licenses)

        if usage_status:
            licenses = filter(lambda _license: _license.bildungsloginUsageStatus == usage_status, licenses)

        if expiry_date_from:
            licenses = filter(lambda
                                  _license: _license.bildungsloginExpiryDate and _license.bildungsloginExpiryDate >= expiry_date_from,
                              licenses)

        if expiry_date_to:
            licenses = filter(lambda
                                  _license: _license.bildungsloginExpiryDate and _license.bildungsloginExpiryDate <= expiry_date_to,
                              licenses)

        if sizelimit:
            if len(licenses) > sizelimit:
                raise SearchLimitReached

        return licenses

    def get_metadata_by_product_id(self, product_id):
        for metadata in self._metadata:
            if metadata.bildungsloginProductId == product_id:
                return metadata
        return None

    def get_group_by_name(self, name):
        groups = self._workgroups + self._classes
        for group in groups:
            if group.cn == name:
                return group
        return None

    def get_workgroup_by_name(self, name):
        for group in self._workgroups:
            if group.cn == name:
                return group
        return None

    def get_class_by_name(self, name):
        for group in self._classes:
            if group.cn == name:
                return group
        return None

    def get_workgroup_names_by_user(self, user):
        groups = []

        for group in self._workgroups:
            if user.uid in group.memberUid:
                groups.append(group.cn.split('-')[1])
        return groups

    def get_class_names_by_user(self, user):
        groups = []

        for group in self._classes:
            if user.uid in group.memberUid:
                groups.append(group.cn.split('-')[1])
        return groups

    def get_workgroup_by_dn(self, dn):
        for group in self._workgroups:
            if group.entry_dn == dn:
                return group
        return None

    def get_class_by_dn(self, dn):
        for group in self._classes:
            if group.entry_dn == dn:
                return group
        return None

    def get_group_by_uuid(self, entry_uuid):
        for group in self.groups:
            if group.entryUUID == entry_uuid:
                return group
        return None

    def get_workgroup_by_uuid(self, entry_uuid):
        for group in self._workgroups:
            if group.entryUUID == entry_uuid:
                return group
        return None

    def get_assignments_by_assignee(self, assignee):
        assignments = []
        for assignment in self._assignments:
            if assignment.bildungsloginAssignmentAssignee \
                    == assignee.entryUUID:
                assignments.append(assignment)

        return assignments

    def get_license_by_assignment(self, assignment):
        for _license in self._licenses:
            if _license.entry_dn in assignment.entry_dn:
                return _license
        return None

    def get_license_by_code(self, code):
        for _license in self._licenses:
            if _license.bildungsloginLicenseCode == code:
                return _license
        return None

    def get_licenses_by_codes(self, codes):
        licenses = []
        for code in codes:
            licenses.append(self.get_license_by_code(code))
        return licenses

    def get_school(self, name):
        for school in self._schools:
            if name == school.ou:
                return school
        return None

    def get_classes_by_school(self, school):
        classes = []
        for _class in self._classes:
            if _class.ucsschoolRole == "school_class:school:" + school:
                classes.append(_class)
        return classes

    def get_classes(self, school, user):
        classes = []
        for _class in self._classes:
            if _class.ucsschoolRole == "school_class:school:" + school.ou and user.uid in _class.memberUid:
                classes.append(_class)
        return classes

    def get_workgroups_by_school(self, school):
        workgroups = []
        for workgroup in self._workgroups:
            if workgroup.ucsschoolRole == "workgroup:school:" + school:
                workgroups.append(workgroup)
        return workgroups

    def get_workgroups(self, school, user):
        workgroups = []
        for workgroup in self._workgroups:
            if workgroup.ucsschoolRole == "workgroup:school:" + school.ou and user.uid in workgroup.memberUid:
                workgroups.append(workgroup)
        return workgroups

    def get_all_workgroups(self):
        return self._workgroups

    def get_user_by_uuid(self, uuid):
        for user in self._users:
            if user.entryUUID == uuid:
                return user
        return None

    def get_school_by_uuid(self, entry_uuid):
        for school in self._schools:
            if school.entryUUID == entry_uuid:
                return school
        return None

    @property
    def groups(self):
        return self._workgroups + self._classes

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
        assignments = []
        for assignment in self._assignments:
            if license.entry_dn in assignment.entry_dn:
                assignments.append(assignment)

        return assignments

    def get_users_by_group(self, group):
        users = []
        for user in self._users:
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

        licenses_to_use = (
            license
            for license in licenses_assignments
            for _ in range(license['license'].quantity_available)
        )

        if object_type == ObjectType.USER:
            for object_name in object_names:
                license = licenses_to_use.next()
                user = self.get_user(object_name)
                for assignment in license['assignments']:
                    if assignment.bildungsloginAssignmentStatus == Status.AVAILABLE:
                        self.add_user_to_license(license['license'], user)
                        assignment.assign(user.entryUUID)
                        break
                self.cache_single_license(license['license'], license['assignments'])

        elif object_type == ObjectType.GROUP:
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
        licenses = []

        for license in self._licenses:
            if license.bildungsloginProductId == product_id and license.bildungsloginLicenseSchool == school:
                licenses.append(license)
        return licenses

    def get_class_by_uuid(self, uuid):
        for school_class in self._classes:
            if school_class.entryUUID == uuid:
                return school_class
        return None

    def _get_license_cache_file(self, entry_uuid):
        return open(JSON_DIR + 'license-' + entry_uuid + '.json', 'w')

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
        for license_code in license_codes:
            _license = self.get_license_by_code(license_code)
            assignments = self.get_assignments_by_license(_license)

            to_save = {
                'deleted': True,
                'license': _license.get_cache_dictionary(),
                'assignments': [assignment.get_cache_dictionary() for assignment in assignments]
            }
            license_file = self._get_license_cache_file(_license.entryUUID)
            json.dump(to_save, license_file)
            license_file.close()
