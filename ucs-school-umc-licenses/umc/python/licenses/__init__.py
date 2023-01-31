#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Manage licenses
#
# Copyright 2021 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.
import json
import os
from datetime import date, datetime
from os.path import exists
from typing import Dict, List, Optional, Union
import re

from ucsschool.lib.school_umc_base import SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import USER_WRITE, LDAP_Connection
from univention.admin.syntax import iso8601Date
from univention.bildungslogin.handlers import (
    AssignmentHandler,
    BiloCreateError,
    LicenseHandler,
    ObjectType
)
from univention.bildungslogin.models import LicenseType, Role, Status
from univention.bildungslogin.license_import import import_license, load_license_file
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.error import UMC_Error
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import (
    BooleanSanitizer,
    LDAPSearchSanitizer,
    ListSanitizer,
    StringSanitizer,
)
from univention.udm.exceptions import SearchLimitReached

_ = Translation("ucs-school-umc-licenses").translate
JSON_PATH = '/var/lib/univention-appcenter/apps/ucsschool-apis/data/bildungslogin.json'


def undefined_if_none(value, zero_as_none=False):  # type: (Optional[int], bool) -> Union[unicode, int]
    """
    Return "undefined" if the input value is None
    If zero_as_none is set to True, returns "undefined" if value == 0
    """
    if value is None or zero_as_none and value == 0:
        return _("undefined")
    return value


def optional_date2str(date):
    if date:
        return iso8601Date.from_datetime(date)
    return ""


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
                 bildungslogin_utilization_systems=None, bildungslogin_validity_duration=None, quantity_assigned=None, user_strings=None):
        self.classes = []
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
        self.publisher = None
        self.user_strings = user_strings

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
            return self.quantity - self.quantity_assigned

    @property
    def quantity_expired(self):
        if self.is_expired:
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
        return self.quantity_available > 0 and not self.is_expired

    def add_class(self, school_class):
        self.classes.append(school_class)


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

        if self._timestamp is not None and file_time <= self._timestamp:
            return

        self._clear()
        f = open(JSON_PATH, 'r')
        json_string = f.read()
        f.close()
        json_dictionary = json.loads(json_string)
        self._process_entries(json_dictionary)
        self._timestamp = file_time

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
            user_strings=entry['user_strings']))
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
                    metadata.bildungsloginMetaDataPublisher) or pattern.match(metadata.bildungsloginMetaDataTitle):
                filtered_metadata.append(metadata)
        return filtered_metadata

    def _match_license_by_publisher(self, license, regex):
        metadata = self.get_metadata_by_product_id(license.bildungsloginProductId)
        return regex.match(metadata.bildungsloginMetaDataPublisher)

    def _match_license_by_product(self, license, regex):
        metadata = self.get_metadata_by_product_id(license.bildungsloginProductId)
        return regex.match(metadata.bildungsloginMetaDataTitle)

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
                        school_class=None):

        licenses = self._licenses
        if restrict_to_this_product_id:
            licenses = filter(lambda _license: _license.bildungsloginProductId == restrict_to_this_product_id, licenses)

        if school:
            licenses = filter(lambda _license: _license.bildungsloginLicenseSchool == school, licenses)

        if product_id and product_id != '*':
            licenses = filter(lambda _license: _license.bildungsloginProductId == product_id, licenses)

        if license_types:
            licenses = filter(lambda _license: _license.bildungsloginLicenseType in license_types, licenses)

        if is_advanced_search:
            if time_from:
                licenses = filter(lambda _license: _license.bildungsloginDeliveryDate >= time_from, licenses)

            if time_to:
                licenses = filter(lambda _license: _license.bildungsloginDeliveryDate <= time_to, licenses)

        if publisher:
            publisher = re.compile(publisher.replace('*', '.*'))
            licenses = filter(lambda _license: publisher.match(_license.publisher) if _license.publisher else False,
                              licenses)

        if only_available_licenses:
            licenses = filter(lambda _license: _license.is_available, licenses)

        if user_pattern and user_pattern != '*':
            user_pattern = re.compile(user_pattern.replace('*', '.*'))
            licenses = filter(lambda _license: _license.match_user_regex(user_pattern), licenses)

        if license_code:
            license_code = re.compile(license_code.replace('*', '.*'))
            licenses = filter(lambda _license: license_code.match(
                _license.bildungsloginLicenseCode) if _license.bildungsloginLicenseCode else False,
                              licenses)

        if pattern and pattern != '*':
            pattern = re.compile(pattern.replace('*', '.*'))
            licenses = filter(
                lambda _license: pattern.match(_license.bildungsloginLicenseCode), licenses)

        if product and product != '*':
            product = re.compile(product.replace('*', '.*'))
            licenses = filter(lambda _license: self._match_license_by_product(_license, product), licenses)

        if school_class and school_class != '*':
            school_class = self.get_class_by_name(school_class)
            licenses = filter(lambda _license: school_class in _license.classes, licenses)

        return licenses

    def get_metadata_by_product_id(self, product_id):
        for metadata in self._metadata:
            if metadata.bildungsloginProductId == product_id:
                return metadata
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

    def get_classes(self, school, user):
        classes = []
        for _class in self._classes:
            if _class.ucsschoolRole == "school_class:school:" + school.ou and user.uid in _class.memberUid:
                classes.append(_class)
        return classes

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

    def get_assigned_users_by_license(self, license):
        assignments = []
        users = []

        for assignment in self._assignments:
            if assignment.bildungsloginAssignmentStatus != 'AVAILABLE':
                if license.entry_dn in assignment.entry_dn:
                    assignments.append(assignment)

        if license.bildungsloginLicenseType in ['SINGLE', 'VOLUME']:
            for assignment in assignments:
                user = self.get_user_by_uuid(assignment.bildungsloginAssignmentAssignee)
                users.append({
                    'dateOfAssignment': assignment.bildungsloginAssignmentTimeOfAssignment,
                    'username': user.userId,
                    'status': assignment.bildungsloginAssignmentStatus,
                    'statusLabel': Status.label(assignment.bildungsloginAssignmentStatus),
                    'roles': user.get_roles(),
                    'roleLabels': Role.label(user.get_roles()),
                })
        elif license.bildungsloginLicenseType == 'WORKGROUP':
            for assignment in assignments:
                workgroup = self.get_workgroup_by_uuid(assignment.bildungsloginAssignmentAssignee)
                for member_uid in workgroup.memberUid:
                    user = self.get_user(member_uid)
                    users.append({
                        'dateOfAssignment': assignment.bildungsloginAssignmentTimeOfAssignment,
                        'username': user.userId,
                        'status': assignment.bildungsloginAssignmentStatus,
                        'statusLabel': Status.label(assignment.bildungsloginAssignmentStatus),
                        'roles': user.get_roles(),
                        'roleLabels': Role.label(user.get_roles()),
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
                    })
        else:
            raise RuntimeError("Unknown license type: {}".format(license.license_type))

        return users

    def set_license_ignored(self, license_code, ignored):
        license = self.get_license_by_code(license_code)
        license.bildungsloginIgnoredForDisplay = ignored

    def get_assignments_by_license(self, license):
        assignments = []
        for assignment in self._assignments:
            if license.entry_dn in assignment.entry_dn:
                assignments.append(assignment)

        return assignments

    def get_usercount_by_group(self, group):
        count = 0
        for user in self._users:
            if user.userId in group.memberUid:
                count += 1

        return count

    def add_assignments(self, license_codes, object_type, object_names):
        licenses = self.get_licenses_by_codes(license_codes)
        licenses_assignments = []
        for license in licenses:
            assignments = self.get_assignments_by_license(license)
            assignments = filter(lambda _assignment: _assignment.bildungsloginAssignmentStatus == Status.AVAILABLE,
                                 assignments)
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
                        assignment.assign(user.entryUUID)
                        break
                license['license'].quantity_assigned += 1

        elif object_type == ObjectType.GROUP:
            for object_name in object_names:
                school_class = self.get_class_by_name(object_name)
                if school_class:
                    license = licenses_to_use.next()
                    for assignment in license['assignments']:
                        if assignment.bildungsloginAssignmentStatus == Status.AVAILABLE:
                            assignment.assign(school_class.entryUUID)
                            break
                    license['license'].quantity_assigned += self.get_usercount_by_group(school_class)

                else:
                    group = self.get_workgroup_by_name(object_name)
                    if group:
                        license = licenses_to_use.next()
                        for assignment in license['assignments']:
                            if assignment.bildungsloginAssignmentStatus == Status.AVAILABLE:
                                assignment.assign(group.entryUUID)
                                break
                        license['license'].quantity_assigned += self.get_usercount_by_group(group)

        elif object_type == ObjectType.SCHOOL:
            for object_name in object_names:
                license = licenses_to_use.next()
                school = self.get_school(object_name)
                for assignment in license['assignments']:
                    if assignment.bildungsloginAssignmentAssignee == school.entryUUID:
                        assignment.assign(school.entryUUID)
                        break
                license['license'].quantity_assigned += len(self._get_users_by_school(school.ou))

    def remove_assignments(self, license_code, object_type, object_names):
        license = self.get_license_by_code(license_code)
        assignments = self.get_assignments_by_license(license)

        assignments = filter(lambda _assignment: _assignment.bildungsloginAssignmentStatus == Status.ASSIGNED,
                             assignments)

        if object_type == ObjectType.USER:
            for object_name in object_names:
                user = self.get_user(object_name)
                for assignment in assignments:
                    if assignment.bildungsloginAssignmentAssignee == user.entryUUID:
                        assignment.remove()
                license.quantity_assigned -= 1
        elif object_type == ObjectType.GROUP:
            for object_name in object_names:
                group = self.get_workgroup_by_name(object_name)
                if group:
                    for assignment in assignments:
                        if assignment.bildungsloginAssignmentAssignee == group.entryUUID:
                            assignment.remove()
                    license.quantity_assigned -= self.get_usercount_by_group(group)
                else:
                    school_classes = self.get_class_by_name(object_name)
                    if school_classes:
                        for assignment in assignments:
                            if assignment.bildungsloginAssignmentAssignee == school_classes.entryUUID:
                                assignment.remove()
                    license.quantity_assigned -= self.get_usercount_by_group(school_classes)
        elif object_type == ObjectType.SCHOOL:
            for object_name in object_names:
                school = self.get_school(object_name)
                for assignment in assignments:
                    if assignment.bildungsloginAssignmentAssignee == school.entryUUID:
                        assignment.remove()
                license.quantity_assigned -= len(self._get_users_by_school(school.ou))

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


class Instance(SchoolBaseModule):

    def __init__(self, *args, **kwargs):
        super(Instance, self).__init__(*args, **kwargs)
        self.repository = LdapRepository()

    @sanitize(
        isAdvancedSearch=BooleanSanitizer(required=True),
        school=SchoolSanitizer(required=True),
        onlyAvailableLicenses=BooleanSanitizer(required=True),
        timeFrom=StringSanitizer(regex_pattern=iso8601Date.regex, allow_none=True, default=None),
        timeTo=StringSanitizer(regex_pattern=iso8601Date.regex, allow_none=True, default=None),
        publisher=LDAPSearchSanitizer(add_asterisks=False, default=""),
        licenseType=ListSanitizer(sanitizer=LDAPSearchSanitizer(add_asterisks=False)),
        userPattern=LDAPSearchSanitizer(default=""),
        productId=LDAPSearchSanitizer(default=""),
        product=LDAPSearchSanitizer(default=""),
        licenseCode=LDAPSearchSanitizer(default=""),
        pattern=LDAPSearchSanitizer(default=""),
        allocationProductId=LDAPSearchSanitizer(add_asterisks=False, default=""),
    )
    @LDAP_Connection(USER_WRITE)
    def licenses_query(self, request, ldap_user_write=None):
        """Searches for licenses
        requests.options = {
            isAdvancedSearch -- boolean
            school -- str (schoolId)
            timeFrom -- str (ISO 8601 date string)
            timeTo -- str (ISO 8601 date string)
            onlyAllocatableLicenses -- boolean
            publisher -- str
            licenseType -- list
            userPattern -- str
            productId -- str
            product -- str
            licenseCode -- str
            pattern -- str
            class -- str
        }
        """
        self.repository.update()
        sizelimit = int(ucr.get("directory/manager/web/sizelimit", 2000))
        time_from = request.options.get("timeFrom")
        time_from = iso8601Date.to_datetime(time_from) if time_from else None
        time_to = request.options.get("timeTo")
        time_to = iso8601Date.to_datetime(time_to) if time_to else None
        school_class = request.options.get("class", None)
        if not school_class:
            school_class = request.options.get("workgroup", None)
        try:
            licenses = self.repository.filter_licenses(
                is_advanced_search=request.options.get("isAdvancedSearch"),
                school=request.options.get("school"),
                time_from=time_from,
                time_to=time_to,
                only_available_licenses=request.options.get(
                    "onlyAvailableLicenses"),
                publisher=request.options.get("publisher"),
                license_types=request.options.get("licenseType"),
                user_pattern=request.options.get("userPattern"),
                product_id=request.options.get("productId"),
                product=request.options.get("product"),
                license_code=request.options.get("licenseCode"),
                pattern=request.options.get("pattern"),
                restrict_to_this_product_id=request.options.get(
                    "allocationProductId"),
                sizelimit=sizelimit,
                school_class=school_class)
        except SearchLimitReached:
            raise UMC_Error(
                _("Hint"
                  "The number of licenses to be displayed is over {} and thus exceeds the set maximum value."
                  "You can use the filter/search parameters to limit the selection."
                  "Alternatively, the maximum number for the display can be adjusted by an administrator with "
                  "the UCR variable directory/manager/web/sizelimit."
                  ).format(sizelimit)
            )
        result = []
        for _license in licenses:
            metadata = self.repository.get_metadata_by_product_id(_license.bildungsloginProductId)
            result.append({
                "licenseCode": _license.bildungsloginLicenseCode,
                "productId": _license.bildungsloginProductId,
                "productName": metadata.bildungsloginMetaDataTitle,
                "publisher": metadata.bildungsloginMetaDataPublisher,
                "licenseTypeLabel": LicenseType.label(_license.bildungsloginLicenseType),
                "for": _license.bildungsloginLicenseSpecialType,
                "importDate": iso8601Date.from_datetime(_license.bildungsloginDeliveryDate),
                "validityStart": iso8601Date.from_datetime(
                    _license.bildungsloginValidityStartDate) if _license.bildungsloginValidityStartDate else None,
                "validityEnd": iso8601Date.from_datetime(
                    _license.bildungsloginValidityEndDate) if _license.bildungsloginValidityEndDate else None,
                "countAquired": undefined_if_none(_license.quantity, zero_as_none=True),
                "countAssigned": undefined_if_none(_license.quantity_assigned),
                "countAvailable": undefined_if_none(_license.quantity_available),
                "countExpired": undefined_if_none(_license.quantity_expired),
            })

        self.finished(request.id, result)

    @sanitize(
        #  school=StringSanitizer(required=True),
        licenseCode=StringSanitizer(required=True),
    )
    @LDAP_Connection(USER_WRITE)
    def licenses_get(self, request, ldap_user_write=None):
        """Get single license + meta data + assigned users
        requests.options = {
            #  school -- schoolId
            licenseCode -- str
        }
        """
        MODULE.info("licenses.get: options: %s" % str(request.options))
        # TODO should the school be incorperated in getting the license?
        # school = request.options.get("school")
        license_code = request.options.get("licenseCode")
        license = self.repository.get_license_by_code(license_code)
        assigned_users = self.repository.get_assigned_users_by_license(license)
        for assigned_user in assigned_users:
            assigned_user["dateOfAssignment"] = iso8601Date.from_datetime(
                assigned_user["dateOfAssignment"]
            )
        meta_data = self.repository.get_metadata_by_product_id(license.bildungsloginProductId)
        result = {
            "countAquired": undefined_if_none(license.quantity, zero_as_none=True),
            "countAssigned": license.quantity_assigned,
            "countAvailable": undefined_if_none(license.quantity_available),
            "countExpired": undefined_if_none(license.quantity_expired),
            "ignore": license.bildungsloginIgnoredForDisplay,
            "importDate": iso8601Date.from_datetime(license.bildungsloginDeliveryDate),
            "licenseCode": license.bildungsloginLicenseCode,
            "licenseTypeLabel": LicenseType.label(license.bildungsloginLicenseType),
            "productId": meta_data.bildungsloginProductId,
            "reference": license.bildungsloginPurchasingReference,
            "specialLicense": license.bildungsloginLicenseSpecialType,
            "usage": license.bildungsloginUtilizationSystems,
            "validityStart": optional_date2str(license.bildungsloginValidityStartDate),
            "validityEnd": optional_date2str(license.bildungsloginValidityEndDate),
            "validitySpan": license.bildungsloginPurchasingReference,
            "author": meta_data.bildungsloginMetaDataAuthor,
            "cover": meta_data.bildungsloginMetaDataCover or meta_data.bildungsloginMetaDataCoverSmall,
            "productName": meta_data.bildungsloginMetaDataTitle,
            "publisher": meta_data.bildungsloginMetaDataPublisher,
            "users": assigned_users,
        }
        MODULE.info("licenses.get: result: %s" % str(result))
        self.finished(request.id, result)

    @LDAP_Connection(USER_WRITE)
    def publishers(self, request, ldap_user_write=None):
        MODULE.info("licenses.publishers: options: %s" % str(request.options))
        result = [{"id": publisher, "label": publisher} for publisher in self.repository.get_publishers()]
        MODULE.info("licenses.publishers: result: %s" % str(result))
        self.finished(request.id, result)

    @LDAP_Connection(USER_WRITE)
    def license_types(self, request, ldap_user_write=None):
        MODULE.info("licenses.license_types: options: %s" % str(request.options))
        result = LicenseHandler.get_license_types()
        MODULE.info("licenses.license_types: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        licenseCode=StringSanitizer(required=True),
        ignore=BooleanSanitizer(required=True),
    )
    @LDAP_Connection(USER_WRITE)
    def set_ignore(self, request, ldap_user_write=None):
        """Set 'ignored' attribute of a license
        requests.options = {
            licenseCode -- str
            ignore -- boolean
        }
        """
        MODULE.info("licenses.set_ignore: options: %s" % str(request.options))
        license_code = request.options.get("licenseCode")
        ignore = request.options.get("ignore")
        lh = LicenseHandler(ldap_user_write)
        success = lh.set_license_ignore(license_code, ignore)
        if success:
            self.repository.set_license_ignored(license_code, ignore)
        result = {
            "errorMessage": ""
            if success
            else _(
                "The 'Ignore' state cannot be changed because users are already assigned to the license."
            )
        }
        MODULE.info("licenses.set_ignore: result: %s" % str(result))
        self.finished(request.id, result)

    def _remove_from_objects(self, ldap_user_write, license_code, object_type, object_names):
        """ Generic function for "remove_from_*" endpoints """
        ah = AssignmentHandler(ldap_user_write)
        failed_assignments = ah.remove_assignment_from_objects(license_code,
                                                               object_type,
                                                               object_names)

        object_names = filter(lambda object_name: object_name not in failed_assignments, object_names)
        self.repository.remove_assignments(license_code, object_type, object_names)
        return {
            "failedAssignments": [
                {"username": fa[0], "error": fa[1]}
                for fa in failed_assignments
            ]
        }

    @sanitize(licenseCode=StringSanitizer(required=True),
              usernames=ListSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def remove_from_users(self, request, ldap_user_write=None):
        """
        Remove ASSIGNED users from the license
        requests.options = {
            licenseCode -- str
            usernames -- List[str]
        }
        """
        MODULE.info("licenses.remove_from_users: options: %s" % str(request.options))
        result = self._remove_from_objects(ldap_user_write,
                                           request.options.get("licenseCode"),
                                           ObjectType.USER,
                                           request.options.get("usernames"))
        MODULE.info("licenses.remove_from_users: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCode=StringSanitizer(required=True),
              group=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def remove_from_group(self, request, ldap_user_write=None):
        """
        Remove ASSIGNED group from the license
        requests.options = {
            licenseCode -- str
            group -- str
        }
        """
        MODULE.info("licenses.remove_from_group: options: %s" % str(request.options))
        result = self._remove_from_objects(ldap_user_write,
                                           request.options.get("licenseCode"),
                                           ObjectType.GROUP,
                                           [request.options.get("group")])
        MODULE.info("licenses.remove_from_group: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCode=StringSanitizer(required=True),
              school=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def remove_from_school(self, request, ldap_user_write=None):
        """
        Remove ASSIGNED school from the license
        requests.options = {
            licenseCode -- str
            school -- str
        }
        """
        MODULE.info("licenses.remove_from_school: options: %s" % str(request.options))
        result = self._remove_from_objects(ldap_user_write,
                                           request.options.get("licenseCode"),
                                           ObjectType.SCHOOL,
                                           [request.options.get("school")])
        MODULE.info("licenses.remove_from_school: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              usernames=ListSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_users(self, request, ldap_user_write=None):
        """Assign licenses to users
        requests.options = {
            licenseCodes -- List[str]
            usernames -- List[str]
        }
        """
        MODULE.info("licenses.assign_to_users: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        object_names = request.options.get("usernames")

        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.USER,
                                               object_names)

        object_names = filter(lambda object_name: object_name not in result['failedAssignmentsObjects'], object_names)

        if len(object_names) > 0 and not result['notEnoughLicenses']:
            self.repository.add_assignments(request.options.get("licenseCodes"),
                                            ObjectType.USER,
                                            request.options.get("usernames"))
        MODULE.info("licenses.assign_to_users: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              school=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_school(self, request, ldap_user_write=None):
        """Assign licenses to a school
        requests.options = {
            licenseCodes -- List[str]
            school -- str
        }
        """
        MODULE.info("licenses.assign_to_school: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.SCHOOL,
                                               [request.options.get("school")])
        if not result['notEnoughLicenses']:
            self.repository.add_assignments(request.options.get("licenseCodes"),
                                            ObjectType.SCHOOL,
                                            request.options.get("school"))
        MODULE.info("licenses.assign_to_school: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              schoolClass=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_class(self, request, ldap_user_write=None):
        """Assign licenses to a class
        requests.options = {
            licenseCodes -- List[str]
            schoolClass -- str
        }
        """
        MODULE.info("licenses.assign_to_class: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.GROUP,
                                               [request.options.get("schoolClass")])
        if not result['notEnoughLicenses']:
            self.repository.add_assignments(request.options.get("licenseCodes"),
                                            ObjectType.GROUP,
                                            request.options.get("schoolClass"))
        MODULE.info("licenses.assign_to_class: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              workgroup=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_workgroup(self, request, ldap_user_write=None):
        """Assign licenses to a workgroup
        requests.options = {
            licenseCodes -- List[str]
            workgroup -- str
        }
        """
        MODULE.info("licenses.assign_to_workgroup: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.GROUP,
                                               [request.options.get("workgroup")])
        MODULE.info("licenses.assign_to_workgroup: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        **{
            "school": SchoolSanitizer(required=True),
            "class": StringSanitizer(required=True),
            "workgroup": StringSanitizer(required=True),
            "pattern": LDAPSearchSanitizer(
                required=True,
            ),
        }
    )
    @LDAP_Connection(USER_WRITE)
    def users_query(self, request, ldap_user_write=None):
        """Searches for users
        requests.options = {
            school
            class
            workgroup
            pattern
        }
        """
        self.repository.update()
        MODULE.info("licenses.query: options: %s" % str(request.options))
        school = request.options.get("school")
        pattern = request.options.get("pattern")
        workgroup = request.options.get("workgroup")
        school_class = request.options.get("class")

        users = self.repository.filter_users(pattern, school, workgroup, school_class)
        school_obj = self.repository.get_school(school)

        workgroups = {wg.entry_dn: wg.cn for wg in self.repository.get_all_workgroups()}
        prefix = school + "-"
        result = []
        for user in users:
            result.append({
                "firstname": user.givenName,
                "lastname": user.sn,
                "username": user.userId,
                "role": Role.label(user.ucsschoolRole),
                "class": ", ".join(
                    [
                        _cls.cn[len(prefix):] if _cls.cn.startswith(prefix) else _cls.cn
                        for _cls in self.repository.get_classes(school_obj, user)
                    ]
                ),
                "workgroup": ", ".join(
                    wg.cn[len(prefix):] if wg.cn.startswith(prefix) else wg.cn
                    for wg in self.repository.get_workgroups(school_obj, user)
                ),
            })

        MODULE.info("licenses.query: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        school=SchoolSanitizer(required=True),
        pattern=LDAPSearchSanitizer(),
        licenseType=ListSanitizer(sanitizer=LDAPSearchSanitizer(add_asterisks=False))
    )
    @LDAP_Connection(USER_WRITE)
    def products_query(self, request, ldap_user_write=None):
        """Searches for products
        requests.options = {
            school:  str
            pattern: str
            licenseType: List
            showOnlyAvailable: bool [optional]
        }
        """
        self.repository.update()
        MODULE.info("licenses.products.query: options: %s" % str(request.options))
        result = []

        school = request.options.get("school")
        pattern = request.options.get("pattern")
        license_types = request.options.get("licenseType", None)

        user_count = None

        if license_types is not None and "WORKGROUP" in license_types:
            workgroup_name = request.options.get("groupName", None)

            if workgroup_name is not None:
                group = self.repository.get_workgroup_by_name(workgroup_name)

                if group:
                    user_count = len(group.memberUid)
        meta_data_objs = self.repository.filter_metadata(pattern)
        for meta_datum_obj in meta_data_objs:
            licenses = self.repository.filter_licenses(meta_datum_obj.bildungsloginProductId, school, license_types)

            if licenses:
                non_ignored_licenses = [license for license in licenses if not license.bildungsloginIgnoredForDisplay]

                sum_quantity = 0
                for license in non_ignored_licenses:
                    sum_quantity += license.quantity

                sum_num_assigned = 0
                for license in non_ignored_licenses:
                    sum_num_assigned += license.quantity_assigned

                sum_num_expired = 0
                sum_num_available = 0
                for license in non_ignored_licenses:
                    if license.is_expired:
                        sum_num_expired += license.quantity_expired
                    else:
                        sum_num_available += license.quantity_available

                # count info about licenses
                number_of_licenses = len(non_ignored_licenses)
                number_of_assigned_licenses = \
                    sum(1 for l in non_ignored_licenses if l.quantity_assigned > 0)
                number_of_expired_licenses = sum(1 for license in non_ignored_licenses if license.is_expired)
                # Counting of assignments depends on the license type: _get_total_number_of_assignments() encapsulates the logic.
                number_of_available_licenses = \
                    sum(1 for license in non_ignored_licenses if
                        (license.quantity_available > 0) and not license.is_expired)
                # Caller (grid query) can now request products with 'all' or 'only available' licenses
                if 'showOnlyAvailable' in request.options and request.options['showOnlyAvailable']:
                    if number_of_available_licenses < 1:
                        continue

                latest_delivery_date = max(lic_udm.bildungsloginDeliveryDate for lic_udm in licenses)
                result.append(
                    {
                        "productId": meta_datum_obj.bildungsloginProductId,
                        "title": meta_datum_obj.bildungsloginMetaDataTitle,
                        "publisher": meta_datum_obj.bildungsloginMetaDataPublisher,
                        "cover": meta_datum_obj.bildungsloginMetaDataCoverSmall or meta_datum_obj.bildungsloginMetaDataCover,
                        "countAquired": undefined_if_none(sum_quantity),
                        "countAssigned": sum_num_assigned,
                        "countExpired": undefined_if_none(sum_num_expired),
                        "countAvailable": undefined_if_none(sum_num_available),
                        "latestDeliveryDate": iso8601Date.from_datetime(latest_delivery_date),
                        "countLicenses": number_of_licenses,
                        "countLicensesAssigned": number_of_assigned_licenses,
                        "countLicensesExpired": number_of_expired_licenses,
                        "countLicensesAvailable": number_of_available_licenses,
                        "user_count": user_count
                    }
                )
        MODULE.info("licenses.products.query: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        school=SchoolSanitizer(required=True),
        productId=StringSanitizer(required=True),
    )
    @LDAP_Connection(USER_WRITE)
    def products_get(self, request, ldap_user_write=None):
        """Get a product
        requests.options = {
            school
            productId
        }
        """
        MODULE.info("licenses.products.get: options: %s" % str(request.options))
        school = request.options.get("school")
        product_id = request.options.get("productId")
        licenses = self.repository.get_licenses_by_product_id(product_id, school)
        meta_data = self.repository.get_metadata_by_product_id(product_id)
        license_js_objs = [
            {
                "licenseCode": license.bildungsloginLicenseCode,
                "productId": meta_data.bildungsloginProductId,
                "productName": meta_data.bildungsloginMetaDataTitle,
                "publisher": meta_data.bildungsloginMetaDataAuthor,
                "licenseTypeLabel": LicenseType.label(license.bildungsloginLicenseType),
                "validityStart": optional_date2str(license.bildungsloginValidityStartDate),
                "validityEnd": optional_date2str(license.bildungsloginValidityEndDate),
                "validitySpan": str(
                    license.bildungsloginValidityDuration) if license.bildungsloginValidityDuration else "",
                "ignore": _("Yes") if license.bildungsloginIgnoredForDisplay else _("No"),
                "countAquired":
                    str(undefined_if_none(None if license.quantity == 0 else license.quantity)),
                "countAssigned": str(license.quantity_assigned),
                "countAvailable":
                    str(undefined_if_none(license.quantity_available)),
                "countExpired":
                    str(undefined_if_none(license.quantity_expired)),
                "importDate": iso8601Date.from_datetime(license.bildungsloginDeliveryDate),
            }
            for license in licenses
        ]  # type: List[Dict[str, str]]
        # meta_data_udm = mh.get_meta_data_by_product_id(product_id)
        # meta_data = mh.from_udm_obj(meta_data_udm)
        result = {
            "title": meta_data.bildungsloginMetaDataTitle,
            "productId": meta_data.bildungsloginProductId,
            "publisher": meta_data.bildungsloginMetaDataPublisher,
            "author": meta_data.bildungsloginMetaDataAuthor,
            "description": meta_data.bildungsloginMetaDataDescription,
            "cover": meta_data.bildungsloginMetaDataCover or meta_data.bildungsloginMetaDataCoverSmall,
            "licenses": license_js_objs,
        }
        MODULE.info("licenses.products.get: result: %s" % str(result))
        self.finished(request.id, result)

    pickup_regex = r"^\s*[A-Z]{3}-[\S]{3,251}\s*$"

    @staticmethod
    def _import_licenses(license_handler, license_file, school):
        # type: (LicenseHandler, str, str) -> None
        """
        Read retrieved licenses package and tries to import all of them into LDAP.
        Raises a BiloCreateError if at least one of the licenses wasn't imported.
        """
        errors = []
        for license in load_license_file(license_file, school):
            try:
                import_license(license_handler, license)
            except BiloCreateError as error:
                errors.append(error.message)
        if errors:
            error_message = "The following licenses were not imported: \n"
            error_message += "\n".join("  - {}".format(error) for error in errors)
            raise BiloCreateError(error_message)

    @sanitize(pickUpNumber=StringSanitizer(regex_pattern=pickup_regex))
    @LDAP_Connection(USER_WRITE)
    def get_license(self, request, ldap_user_write=None):
        """Import a license
        requests.options = {
            school
            pickup_number
        }
        """
        MODULE.info("licenses.import.get: options: %s" % str(request.options))
        pickup_number = "".join(request.options.get("pickUpNumber").rstrip().lstrip())
        school = request.options.get("school")
        license_handler = LicenseHandler(ldap_user_write)

        # Retrieve the requested license package
        license_file, licenses = license_handler.retrieve_license_data(pickup_number)

        # Import the retrieved license package and its metadata into LDAP
        self._import_licenses(license_handler, license_file, school)

        result = {
            "pickup": pickup_number,
            "school": school,
            "licenses": licenses
        }
        MODULE.info("licenses.import.get: result: %s" % str(result))
        self.finished(request.id, result)
