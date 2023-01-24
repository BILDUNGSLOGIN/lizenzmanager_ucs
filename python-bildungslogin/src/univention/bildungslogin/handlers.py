#!/usr/share/ucs-test/runner /usr/bin/py.test -s
# -*- coding: utf-8 -*-
#
# Copyright 2021 Univention GmbH
#
# https://www.univention.de/
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
# <https://www.gnu.org/licenses/>.

import datetime
import enum
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

from ldap.filter import filter_format
from ldap.filter import escape_filter_chars

from ucsschool.lib.roles import get_role_info
from univention.admin.syntax import iso8601Date
from univention.lib.i18n import Translation
from univention.udm import UDM, CreateError, ModifyError, NoObject as UdmNoObject
# from .license_retrieval import PULL_LICENSE_RESPONSE_MOCK
from .license_retrieval.cmd_license_retrieval import retrieve_licenses
from .exceptions import (
    BiloAssignmentError,
    BiloCreateError,
    BiloLicenseNotFoundError,
    BiloProductNotFoundError,
)
from .models import Assignment, License, LicenseType, MetaData, Status, Role
from .utils import get_entry_uuid, ldap_escape

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType
    from univention.udm.base import BaseObject as UdmObject

_ = Translation("python-bildungslogin").translate


class LicenseHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("bildungslogin/license")
        self._assignments_mod = udm.get("bildungslogin/assignment")
        self._meta_data_mod = udm.get("bildungslogin/metadata")
        self._users_mod = udm.get("users/user")
        self._groups_mod = udm.get("groups/group")
        self._schools_mod = udm.get("container/ou")
        self.ah = AssignmentHandler(lo)
        self.logger = logging.getLogger(__name__)

    def create(self, license):  # type: (License) -> None
        """Create a license and unassigned assignments as leaves."""
        try:
            udm_obj = self._licenses_mod.new()
            udm_obj.props.code = license.license_code
            udm_obj.props.product_id = license.product_id
            udm_obj.props.quantity = license.license_quantity
            udm_obj.props.provider = license.license_provider
            udm_obj.props.utilization_systems = license.utilization_systems
            udm_obj.props.validity_start_date = license.validity_start_date
            udm_obj.props.validity_end_date = license.validity_end_date
            udm_obj.props.validity_duration = license.validity_duration
            udm_obj.props.delivery_date = license.delivery_date
            udm_obj.props.school = license.license_school
            udm_obj.props.ignored = license.ignored_for_display
            udm_obj.props.special_type = license.license_special_type
            udm_obj.props.purchasing_reference = license.purchasing_reference
            udm_obj.props.license_type = license.license_type
            udm_obj.save()
            self.logger.debug("Created License object %r: %r", udm_obj.dn, udm_obj.props)
        except CreateError as exc:
            raise BiloCreateError(
                _("Error creating license {license_code!r}!\n{exc}").format(
                    license_code=license.license_code, exc=exc
                )
            )
        if license.license_type in [LicenseType.WORKGROUP, LicenseType.SCHOOL]:
            # Create 1 assignment for these types
            # (one license can be assigned only to one group/school)
            self.ah.create_assignment_for_license(license_code=license.license_code)
        elif license.license_type in [LicenseType.SINGLE, LicenseType.VOLUME]:
            # Create an assignment as per quantity
            for i in range(license.license_quantity):
                self.ah.create_assignment_for_license(license_code=license.license_code)
        else:
            raise RuntimeError("Unknown license type: {}".format(license.license_type))

    def get_assigned_users(self, license):
        """
        Get users assigned to the license:
        - Directly assigned users for the SINGLE/VOLUME licenses
        - Members of school/group licenses for the SCHOOL/WORKGROUP licenses
        """

        def _object_factory(input_user, input_assignment):
            # type: (UdmObject, Assignment) -> Dict[str, Any]
            """ Create an object required for the output """
            return {
                "username": input_user.props.username,
                "status": input_assignment.status,
                "statusLabel": Status.label(input_assignment.status),
                "dateOfAssignment": input_assignment.time_of_assignment,
            }

        school_ou = license.license_school
        assignments = self.get_assignments_for_license_with_filter(license, "(assignee=*)")
        users = []
        if license.license_type in [LicenseType.SINGLE, LicenseType.VOLUME]:
            for assignment in assignments:
                try:
                    [udm_user] = self._users_mod.search(
                        filter_format("(entryUUID=%s)", [assignment.assignee]))
                    role_data = {get_role_info(role) for role in udm_user.props.ucsschoolRole}
                    roles = {x[0] for x in role_data}
                    if license.license_special_type == "Lehrkraft" and "teacher" not in roles:
                        continue
                    append_value = _object_factory(udm_user, assignment)
                    school_roles = [x[0] for x in role_data if x[1] == 'school' and x[2] == school_ou]
                    append_value["roles"] = school_roles
                    role_labels = Role.label(school_roles)
                    append_value["roleLabels"] = role_labels
                    users.append(append_value)
                except:
                    pass
        elif license.license_type == LicenseType.WORKGROUP:
            for assignment in assignments:
                try:
                    [group] = self._groups_mod.search(
                        filter_format("(entryUUID=%s)", [assignment.assignee]))
                    for udm_user in group.props.users.objs:
                        role_data = {get_role_info(role) for role in udm_user.props.ucsschoolRole}
                        roles = {x[0] for x in role_data}
                        if license.license_special_type == "Lehrkraft" and "teacher" not in roles:
                            continue
                        append_value = _object_factory(udm_user, assignment)
                        school_roles = [x[0] for x in role_data if x[1] == 'school' and x[2] == school_ou]
                        append_value["roles"] = school_roles
                        role_labels = Role.label(school_roles)
                        append_value["roleLabels"] = role_labels
                        users.append(append_value)
                except:
                    pass
        elif license.license_type == LicenseType.SCHOOL:
            for assignment in assignments:
                [school] = self._schools_mod.search(
                    filter_format("(entryUUID=%s)", [assignment.assignee]))
                udm_users = self._users_mod.search(
                    filter_format("(school=%s)", [school.props.name]))
                for udm_user in udm_users:
                    # filter out users without "teacher" role for the "Lehrkraft"-type license
                    role_data = {get_role_info(role) for role in udm_user.props.ucsschoolRole}
                    roles = {x[0] for x in role_data}
                    if license.license_special_type == "Lehrkraft" and "teacher" not in roles:
                        continue
                    append_value = _object_factory(udm_user, assignment)
                    school_roles = [x[0] for x in role_data if x[1] == 'school' and x[2] == school_ou]
                    append_value["roles"] = school_roles
                    role_labels = Role.label(school_roles)
                    append_value["roleLabels"] = role_labels
                    users.append(append_value)
        else:
            raise RuntimeError("Unknown license type: {}".format(license.license_type))
        return users

    def set_license_ignore(self, license_code, ignore):  # type: (str, bool) -> bool
        udm_obj = self.get_udm_license_by_code(license_code)
        if ignore and udm_obj.props.num_assigned != 0:
            # can't set ignore if license has assigned users.
            return False
        udm_obj.props.ignored = ignore
        udm_obj.save()
        self.logger.debug("Set License status %r: %r", udm_obj.dn, udm_obj.props)
        return True

    @staticmethod
    def from_udm_obj(udm_obj):  # type: (UdmObject) -> License
        return License(
            license_code=udm_obj.props.code,
            product_id=udm_obj.props.product_id,
            license_quantity=udm_obj.props.quantity,
            license_provider=udm_obj.props.provider,
            utilization_systems=udm_obj.props.utilization_systems,
            validity_start_date=udm_obj.props.validity_start_date,
            validity_end_date=udm_obj.props.validity_end_date,
            validity_duration=udm_obj.props.validity_duration,
            delivery_date=udm_obj.props.delivery_date,
            license_school=udm_obj.props.school,
            ignored_for_display=udm_obj.props.ignored,
            license_special_type=udm_obj.props.special_type,
            license_type=udm_obj.props.license_type,
            purchasing_reference=udm_obj.props.purchasing_reference,
            num_assigned=udm_obj.props.num_assigned,
            num_available=udm_obj.props.num_available,
        )

    def _get_all(
            self, filter_s=None, sizelimit=0
    ):  # type: (Optional[str], Optional[int]) -> List[UdmObject]
        return [o for o in self._licenses_mod.search(filter_s=filter_s, sizelimit=sizelimit)]

    def get_all(
            self, filter_s=None, sizelimit=0
    ):  # type: (Optional[str], Optional[int]) -> List[License]
        """get all licenses"""
        return [
            self.from_udm_obj(udm_obj)
            for udm_obj in self._get_all(filter_s=filter_s, sizelimit=sizelimit)
        ]

    def get_udm_license_by_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(code=%s)", [license_code])
        try:
            return self._get_all(filter_s)[0]
        except IndexError:
            raise BiloLicenseNotFoundError(
                _("License with code {license_code!r} does not exist.")
                .format(license_code=license_code))

    def get_license_by_code(self, license_code):  # type: (str) -> License
        return self.from_udm_obj(self.get_udm_license_by_code(license_code))

    def get_meta_data_by_product_id(self, product_id):
        """
        search for the product by product id. If there is none yet, return an empty object

        TODO: This functions exists here, since we cannot have a MetadataHandler in the LicenseHandler due to
        TODO: circular dependency problems of the handlers with each other.
        """
        filter_s = filter_format("(product_id=%s)", [product_id])
        udm_meta_data = [o for o in self._meta_data_mod.search(filter_s)]
        if not udm_meta_data:
            return MetaData(product_id=product_id)
        else:
            return MetaDataHandler.from_udm_obj(udm_meta_data[0])

    def get_meta_data_for_license(self, license):  # type: (Union[UdmObject, License]) -> MetaData
        """search for the product of the license. If there is none yet, return an empty object."""
        if type(license) is License:
            product_id = license.product_id
        else:
            product_id = license.props.product_id

        # here we have to use the mod directly to prevent recursion
        filter_s = filter_format("(product_id=%s)", [product_id])
        udm_meta_data = [o for o in self._meta_data_mod.search(filter_s)]
        if not udm_meta_data:
            return MetaData(product_id=product_id)
        else:
            return MetaDataHandler.from_udm_obj(udm_meta_data[0])

    def get_assignments_for_license_with_filter(self, license, filter_s):
        # type: (License, str) -> List[Assignment]
        """search in assignments for license with license_code for filter_s e.g. for status"""
        udm_obj = self.get_udm_license_by_code(license.license_code)
        return [
            self.ah.from_udm_obj(obj)
            for obj in self._assignments_mod.search(base=udm_obj.dn, filter_s=filter_s)
        ]

    def get_number_of_assigned_users(self, license):  # type: (License) -> int
        """ Count the number of users that were assigned to the license """
        if license.num_assigned_users is None:
            license.num_assigned_users = len(self.get_assigned_users(license))
        return license.num_assigned_users

    def _count_leftover_users(self, license):  # type: (License) -> Optional[int]
        """
        Subtracts the assigned users from the maximum number of users for the license
        NOTES:
            - Returns None in case the number of available users is infinite
            -In case the number of assigned users is higher than the total, returns 0.
                Such case is possible for the SCHOOL / WORKGROUP types of licenses
        """
        if license.license_quantity == 0:
            return None
        num_assigned_users = self.get_number_of_assigned_users(license)
        num_leftover_users = license.license_quantity - num_assigned_users
        if num_leftover_users < 0:
            return 0
        return num_leftover_users

    def get_number_of_available_users(self, license):  # type: (License) -> Optional[int]
        """ Count the number of available user assignments """
        if license.is_expired:
            return 0
        return self._count_leftover_users(license)

    def get_number_of_expired_unassigned_users(self, license):  # type: (License) -> Optional[int]
        """ Count the number of user assignments that have expired due to the license expiration """
        if not license.is_expired:
            return 0
        return self._count_leftover_users(license)

    def get_licenses_for_user(self, filter_s, school):  # type: (str) -> Set[UdmObject]
        users = self._users_mod.search(filter_s)
        licenses = set()
        for user in users:
            entry_uuid = get_entry_uuid(self._users_mod.connection, user.dn)
            assignments = self.ah.get_all_assignments_for_uuid(entry_uuid)
            group_entry_uuids = [get_entry_uuid(self._groups_mod.connection, group_dn)
                                 for group_dn in user.props.groups]
            group_assignments = [self.ah.get_all_assignments_for_uuid(entry_uuid) for entry_uuid in group_entry_uuids]
            group_assignment_list = [x for l in group_assignments for x in l]
            school_filter = filter_format("(&(name=%s)(objectClass=ucsschoolOrganizationalUnit))", [school])
            school_obj = [x for x in self._schools_mod.search(school_filter)][0]
            school_uuid = get_entry_uuid(self._schools_mod.connection, school_obj.dn)
            school_assignment_list = self.ah.get_all_assignments_for_uuid(school_uuid)
            for assignment in assignments + group_assignment_list + school_assignment_list:
                licenses.add(self.ah.get_license_by_license_code(str(assignment.license)))
        return licenses

    @staticmethod
    def get_license_types():  # type: () -> List[Dict[str, str]]
        return [
            {
                "id": LicenseType.SINGLE,
                "label": LicenseType.label(LicenseType.SINGLE),
            },
            {
                "id": LicenseType.VOLUME,
                "label": LicenseType.label(LicenseType.VOLUME),
            },
            {
                "id": LicenseType.WORKGROUP,
                "label": LicenseType.label(LicenseType.WORKGROUP),
            },
            {
                "id": LicenseType.SCHOOL,
                "label": LicenseType.label(LicenseType.SCHOOL),
            },
        ]

    def search_for_licenses(
            self,
            school,  # type: str
            is_advanced_search,  # type: bool
            time_from=None,  # type: Optional[datetime.date]
            time_to=None,  # type: Optional[datetime.date]
            only_available_licenses=False,  # type: Optional[bool]
            publisher="",  # type: Optional[str]
            license_types=None,  # type: Optional[list]
            user_pattern="",  # type: Optional[str]
            product_id="",  # type: Optional[str]
            product="",  # type: Optional[str]
            license_code="",  # type: Optional[str]
            pattern="",  # type: Optional[str]
            restrict_to_this_product_id="",  # type: Optional[str]
            sizelimit=0,  # type: int
            klass=None,  # type: str
    ):
        if license_types is None:
            license_types = []

        def __get_possible_product_ids(search_values, search_combo="|"):
            attr_allow_list = (
                "title",
                "publisher",
            )
            filter_parts = []
            for attr, pattern in search_values:
                if attr not in attr_allow_list:
                    raise AttributeError(
                        "attr {} not in allowed search attr {}".format(attr, attr_allow_list)
                    )
                filter_parts.append("({attr}={pattern})"
                                    .format(attr=attr, pattern=ldap_escape(pattern)))
            if not filter_parts:
                filter_s = ""
            elif len(filter_parts) == 1:
                filter_s = filter_parts[0]
            else:
                filter_s = "({}{})".format(search_combo, "".join(filter_parts))
            possible_products = self._meta_data_mod.search(filter_s)
            return [product.props.product_id for product in possible_products]

        def __get_pattern_filter():  # type: () -> str
            possible_product_ids = __get_possible_product_ids(
                [
                    (
                        "title",
                        pattern,
                    ),
                    ("publisher", pattern),
                ]
            )
            filter_s = "(|(code={})(product_id={}){})".format(
                ldap_escape(pattern),
                ldap_escape(pattern),
                "".join(
                    [
                        filter_format("(product_id=%s)", (_product_id,))
                        for _product_id in possible_product_ids
                    ]
                ),
            )
            return filter_s

        def __get_advanced_filter():
            # return either None, if the search for matching bildungslogin/metadata did not yield results
            # or a ldap search filter str which is further used
            filter_parts = []
            if time_from:
                filter_parts.append(
                    filter_format(
                        "(bildungsloginDeliveryDate>=%s)", (iso8601Date.from_datetime(time_from),)
                    )
                )
            if time_to:
                filter_parts.append(
                    filter_format(
                        "(bildungsloginDeliveryDate<=%s)", (iso8601Date.from_datetime(time_to),)
                    )
                )

            license_types_filter_parts = []
            for license_typ in license_types:
                license_types_filter_parts.append("(bildungsloginLicenseType={})".format(license_typ))
            if license_types_filter_parts:
                if len(license_types_filter_parts) == 1:
                    filter_parts.append(license_types_filter_parts[0])
                else:
                    filter_parts.append("(|{})".format("".join(license_types_filter_parts)))

            if product_id and product_id != "*":
                filter_parts.append("(product_id={})".format(ldap_escape(product_id)))
            if license_code and license_code != "*":
                filter_parts.append("(code={})".format(ldap_escape(license_code)))
            product_search = []
            if product and product != "*":
                product_search.append(("title", product))
            if publisher and publisher != "*":
                product_search.append(("publisher", publisher))
            if product_search:
                possible_product_ids = __get_possible_product_ids(product_search, search_combo="&")
                if not possible_product_ids:
                    return None
                else:
                    filter_parts.append(
                        "(|{})".format(
                            "".join(
                                [
                                    filter_format("(product_id=%s)", (_product_id,))
                                    for _product_id in possible_product_ids
                                ]
                            )
                        )
                    )
            if (user_pattern and user_pattern != "*") or (klass and klass != "__all__"):
                pattern_parts = ""
                class_parts = ""
                if user_pattern and user_pattern != '*':
                    pattern_parts = "(givenName={user_pattern})(sn={user_pattern})(uid={user_pattern})".format(
                        user_pattern=ldap_escape(user_pattern))
                if klass and klass != "__all__":
                    class_parts = "(memberOf={})".format(escape_filter_chars(klass))
                user_parts = "(|{}{})".format(pattern_parts, class_parts)
                possible_licenses = self.get_licenses_for_user(user_parts, school)
                if not possible_licenses:
                    return None
                else:
                    filter_parts.append(
                        "(|{})".format(
                            "".join(
                                [
                                    filter_format("(code=%s)", (p_license.props.code,))
                                    for p_license in possible_licenses
                                ]
                            )
                        )
                    )
            if not filter_parts:
                filter_s = ""
            elif len(filter_parts) == 1:
                filter_s = filter_parts[0]
            else:
                filter_s = "(&{})".format("".join(filter_parts))
            return filter_s

        rows = []
        if is_advanced_search:
            filter_s = __get_advanced_filter()
            if filter_s is None:
                return []
        else:
            filter_s = __get_pattern_filter()
        school_filter = filter_format("(school=%s)", (school,))
        if filter_s:
            filter_s = "(&{}{})".format(school_filter, filter_s)
        else:
            filter_s = school_filter
        if restrict_to_this_product_id:
            filter_s = "(&(product_id={}){})".format(
                ldap_escape(restrict_to_this_product_id, allow_asterisks=False), filter_s
            )
        licenses = self.get_all(filter_s=filter_s, sizelimit=sizelimit)
        product_ids = set([license.product_id for license in licenses])
        products = {
            product_id: self.get_meta_data_by_product_id(product_id) for product_id in product_ids
        }
        for license in licenses:
            available_users = self.get_number_of_available_users(license)
            available = (available_users > 0) if license.license_type == 'VOLUME' else (license.num_available > 0)
            if not only_available_licenses \
                    or (not license.ignored_for_display and available):
                rows.append(
                    {
                        "productId": license.product_id,
                        "productName": products[license.product_id].title,
                        "publisher": products[license.product_id].publisher,
                        "licenseCode": license.license_code,
                        "licenseTypeLabel": LicenseType.label(license.license_type),
                        "for": license.license_special_type,
                        "countAquired": license.license_quantity,
                        "countAssigned": self.get_number_of_assigned_users(license),
                        "countExpired": self.get_number_of_expired_unassigned_users(license),
                        "countAvailable": available_users,
                        "importDate": license.delivery_date,
                        "licenseType": license.license_type,
                        "validityStart": license.validity_start_date,
                        "validityEnd": license.validity_end_date
                    }
                )
        return rows

    def retrieve_license_data(self, pickup_number):
        self.logger.info(
            "Pickup number: %r received.",
            pickup_number
        )
        return retrieve_licenses(None, pickup_number)


class MetaDataHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("bildungslogin/license")
        self._assignments_mod = udm.get("bildungslogin/assignment")
        self._meta_data_mod = udm.get("bildungslogin/metadata")
        self.ah = AssignmentHandler(lo)
        self.lh = LicenseHandler(lo)
        self.logger = logging.getLogger(__name__)

    def create(self, meta_data):  # type: (MetaData) -> None
        try:
            udm_obj = self._meta_data_mod.new()
            udm_obj.props.product_id = meta_data.product_id
            udm_obj.props.title = meta_data.title
            udm_obj.props.description = meta_data.description
            udm_obj.props.author = meta_data.author
            udm_obj.props.publisher = meta_data.publisher
            udm_obj.props.cover = meta_data.cover
            udm_obj.props.cover_small = meta_data.cover_small
            udm_obj.props.modified = meta_data.modified
            udm_obj.save()
            self.logger.info("Created MetaData object %r: %r", udm_obj.dn, udm_obj.props)
        except CreateError as exc:
            raise BiloCreateError(
                _("Error creating meta data for product id {p_id!r}!\n{exc}").format(
                    p_id=meta_data.product_id, exc=exc
                )
            )

    def save(self, meta_data):  # type: (MetaData) -> None
        udm_obj = self.get_meta_data_by_product_id(meta_data.product_id)
        props_before = udm_obj.props
        udm_obj.props.title = meta_data.title
        udm_obj.props.description = meta_data.description
        udm_obj.props.author = meta_data.author
        udm_obj.props.publisher = meta_data.publisher
        udm_obj.props.cover = meta_data.cover
        udm_obj.props.cover_small = meta_data.cover_small
        udm_obj.props.modified = meta_data.modified
        udm_obj.save()
        self.logger.info(
            "Saving product MetaData object %r: %r -> %r", udm_obj.dn, props_before, udm_obj.props
        )

    @staticmethod
    def from_udm_obj(udm_obj):  # type: (UdmObject) -> MetaData
        return MetaData(
            product_id=udm_obj.props.product_id,
            title=udm_obj.props.title,
            description=udm_obj.props.description,
            author=udm_obj.props.author,
            publisher=udm_obj.props.publisher,
            cover=udm_obj.props.cover,
            cover_small=udm_obj.props.cover_small,
            modified=udm_obj.props.modified,
        )

    def get_all(self, filter_s=None):  # type: (str) -> List[MetaData]
        meta_data_objs = self._meta_data_mod.search(filter_s=filter_s)
        return [MetaDataHandler.from_udm_obj(obj) for obj in meta_data_objs]

    def get_udm_licenses_by_product_id(self, product_id, school=None, license_types=None):
        # type: (str, Optional[str], Optional[list]) -> List[UdmObject]

        filter_s = ["(bildungsloginProductId={})".format(product_id)]
        if school:
            filter_s.append("(bildungsloginLicenseSchool={})".format(school))
        if license_types:
            license_types_filter_parts = []
            for license_typ in license_types:
                license_types_filter_parts.append("(bildungsloginLicenseType={})".format(license_typ))
            if license_types_filter_parts:
                if len(license_types_filter_parts) == 1:
                    filter_s.append(license_types_filter_parts[0])
                else:
                    filter_s.append("(|{})".format("".join(license_types_filter_parts)))

        filter_s = "(&{})".format("".join(filter_s))
        return [o for o in self._licenses_mod.search(filter_s)]

    def get_non_ignored_licenses_for_product_id(self, product_id, school=None):
        # type: (str, Optional[str]) -> List[UdmObject]
        licenses_of_product = self.get_udm_licenses_by_product_id(product_id, school)
        return [udm_license for udm_license in licenses_of_product if not udm_license.props.ignored]

    def get_meta_data_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(product_id=%s)", [product_id])
        try:
            return [o for o in self._meta_data_mod.search(filter_s)][0]
        except IndexError:
            raise BiloProductNotFoundError(
                _("Meta data object with product id {p_id!r} does not exist!")
                .format(p_id=product_id))


class ObjectType(enum.Enum):
    """ Type of the assigned object """
    GROUP = "GROUP"
    SCHOOL = "SCHOOL"
    USER = "USER"


# Define which objects can use which license types
_ALLOWED_LICENSE_TYPES = {
    ObjectType.GROUP: [LicenseType.WORKGROUP],
    ObjectType.SCHOOL: [LicenseType.SCHOOL],
    ObjectType.USER: [LicenseType.SINGLE, LicenseType.VOLUME]
}


class AssignmentHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("bildungslogin/license")
        self._assignments_mod = udm.get("bildungslogin/assignment")
        self._users_mod = udm.get("users/user")
        self._groups_mod = udm.get("groups/group")
        self._schools_mod = udm.get("container/ou")
        self._lo = lo
        self.logger = logging.getLogger(__name__)

    def get_license_of_assignment(self, assignment_dn):  # type: (str) -> UdmObject
        """Return the udm object of the license which is placed
        above the assignment. This is like 'get_parent'."""
        try:
            return self._licenses_mod.get(assignment_dn)
        except UdmNoObject:
            raise BiloLicenseNotFoundError(
                _("There is no license for the assignment {dn!r}!").format(dn=assignment_dn)
            )

    def from_udm_obj(self, udm_obj):  # type: (UdmObject) -> Assignment
        """
        Creates an Assignment object of an udm_obj. We do not save the license
        code directly on the assignments, so we have to ask the parent first.

        :param udm_obj: of assignment
        :return: assignment object
        """
        udm_assignment = self.get_license_of_assignment(udm_obj.position)
        return Assignment(
            assignee=udm_obj.props.assignee,
            license=udm_assignment.props.code,
            time_of_assignment=udm_obj.props.time_of_assignment,
            status=udm_obj.props.status,
        )

    def _get_all(self, base=None, filter_s=None):  # type: (str, str) -> List[UdmObject]
        return [o for o in self._assignments_mod.search(base=base, filter_s=filter_s)]

    def get_all(self, base=None, filter_s=None):  # type: (str, str) -> List[Assignment]
        udm_assignments = self._get_all(base=base, filter_s=filter_s)
        return [self.from_udm_obj(a) for a in udm_assignments]

    def get_all_assignments_for_uuid(self, assignee_uuid, base=None):
        # type: (str, Optional[str]) -> List[Assignment]
        """
        if the base is equal to the dn of a license, this can be used to
        find all assignments for this license

        :param assignee_uuid: entry-uuid of the object (user / group / school)
        :param base: dn of license object
        :return:
        """
        filter_s = filter_format("(assignee=%s)", [assignee_uuid])
        return self.get_all(base=base, filter_s=filter_s)

    def _get_object_uuid_by_name(self, object_type, name):  # type: (ObjectType, str) -> str
        obj = self._get_object_by_name(object_type, name)
        return get_entry_uuid(self._lo, dn=obj.dn)

    def _get_object_by_name(self, object_type, name):  # type: (ObjectType, str) -> UdmObject
        """ Get group/user/school based on its name """
        if object_type is ObjectType.GROUP:
            mod = self._groups_mod
            filter_s = filter_format("(name=%s)", [name])
        elif object_type is ObjectType.USER:
            mod = self._users_mod
            filter_s = filter_format("(username=%s)", [name])
        elif object_type is ObjectType.SCHOOL:
            mod = self._schools_mod
            filter_s = filter_format(
                "(&(name=%s)(objectClass=ucsschoolOrganizationalUnit))", [name])
        else:
            raise RuntimeError("Cannot handle object type: {}".format(object_type))

        objects = [o for o in mod.search(filter_s)]
        if not objects:
            raise BiloAssignmentError(_("No {obj!r} with name {name!r} exists!")
                                      .format(obj=object_type.value, name=name))
        [obj] = objects  # ensure that only one object was found
        return obj

    def _get_school_teachers(self, school):  # type: (UdmObject) -> List[UdmObject]
        """ Get a list of the teachers which belong to the school """
        return list(self._users_mod.search(
            filter_format("(&(school=%s)(ucsschoolRole=teacher:school:%s))", [school.props.name, school.props.name])))

    def _get_school_users(self, school):  # type: (UdmObject) -> List[UdmObject]
        """ Get a list of the users which belong to the school """
        return list(self._users_mod.search(filter_format("(school=%s)", [school.props.name])))

    def get_user_by_username(self, username):  # type: (str) -> UdmObject
        return self._get_object_by_name(ObjectType.USER, username)

    def get_group_by_name(self, group_name):  # type: (str) -> UdmObject
        return self._get_object_by_name(ObjectType.GROUP, group_name)

    def get_school_by_name(self, school_name):  # type: (str) -> UdmObject
        return self._get_object_by_name(ObjectType.SCHOOL, school_name)

    def get_license_by_license_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(code=%s)", [license_code])
        try:
            license = [o for o in self._licenses_mod.search(filter_s)][0]
            return license
        except IndexError:
            raise BiloLicenseNotFoundError(
                _("No license with code {license_code!r} was found!")
                .format(license_code=license_code))

    def create_assignment_for_license(self, license_code):  # type: (str) -> None
        udm_license = self.get_license_by_license_code(license_code)
        try:
            assignment = self._assignments_mod.new(superordinate=udm_license.dn)
            assignment.props.status = Status.AVAILABLE
            assignment.save()
            self.logger.debug("Created Assignment object %r: %r.", assignment.dn, assignment.props)
        except CreateError as exc:
            raise BiloCreateError(
                _("Error creating assignment for {license_code!r}!\n{exc!s}").format(
                    license_code=license_code, exc=exc
                )
            )

    def _get_available_assignments(self, license):  # type: (UdmObject) -> List[UdmObject]
        filter_s = filter_format("(status=%s)", [Status.AVAILABLE])
        return self._get_all(base=license.dn, filter_s=filter_s)

    @staticmethod
    def _check_license_is_ignored(license):  # type: (UdmObject) -> None
        if license.props.ignored:
            raise BiloAssignmentError(
                _("License is 'ignored for display' and thus can't be assigned!"))

    @staticmethod
    def _check_license_is_expired(license):  # type: (UdmObject) -> None
        if license.props.expired:
            raise BiloAssignmentError(_("License is expired and thus can't be assigned!"))

    @classmethod
    def check_assigned_license(cls, license):  # type: (UdmObject) -> None
        """ Conduct different checks for the license to verify that it can be assigned """
        cls._check_license_is_ignored(license)
        cls._check_license_is_expired(license)

    @staticmethod
    def _check_license_school_against_user(license, user):
        # type: (UdmObject, UdmObject) -> None
        user_schools = {s.lower() for s in user.props.school}
        if license.props.school.lower() not in user_schools:
            raise BiloAssignmentError(
                _("License can't be assigned to user in schools {ous}!")
                .format(ous=user_schools))

    @staticmethod
    def _check_license_special_type_against_user(license, user):
        # type: (UdmObject, UdmObject) -> None
        # todo check if we need this in mvp, also make this more robust
        if license.props.special_type == "Lehrkraft":
            roles = [get_role_info(role)[0] for role in user.props.ucsschoolRole]
            if "teacher" not in roles:
                raise BiloAssignmentError(
                    _("License with special type 'Lehrkraft' can't be assigned to user {username!r} "
                      "with roles {roles!r}!").format(username=user.props.username, roles=roles))

    @classmethod
    def _check_license_special_type_against_group(cls, license, group):
        # type: (UdmObject, UdmObject) -> None
        users = group.props.users.objs
        for user in users:
            try:
                cls._check_license_special_type_against_user(license, user)
            except BiloAssignmentError:
                raise BiloAssignmentError(_("This license is allowed for assignments to groups including only teachers."
                                            " Please modify your group selection accordingly."))

    @staticmethod
    def _check_license_school_against_group(license, group):
        # type: (UdmObject, UdmObject) -> None
        if "ou={},dc=".format(license.props.school) not in group.dn:
            raise BiloAssignmentError(
                _("license can't be assigned to group as it doesn't belong to the same school"))

    @staticmethod
    def _check_license_quantity_against_group(license, group):
        # type: (UdmObject, UdmObject) -> None
        group_size = len(group.props.users)
        license_quantity = license.props.quantity
        if license_quantity != 0 and group_size > license_quantity:
            raise BiloAssignmentError(
                _("This license is allowed for assignments to groups including a maximum of <{ous}> members. "
                  "Please modify your group selection accordingly").format(ous=license_quantity))

    @staticmethod
    def _check_license_school_against_school(license, school):
        # type: (UdmObject, UdmObject) -> None
        if license.props.school != school.props.name:
            raise BiloAssignmentError(_("License can't be assigned to a different school"))

    def _check_license_quantity_against_school(self, license, school):
        # type: (UdmObject, UdmObject) -> None
        if license.props.special_type == "Lehrkraft":
            users_count = len(self._get_school_teachers(school))
        else:
            users_count = len(self._get_school_users(school))

        license_quantity = license.props.quantity
        if license_quantity != 0 and users_count > license_quantity:
            raise BiloAssignmentError(
                _("This license is allowed for assignments to schools including a maximum "
                  "of <{ous}> members. The selected school exceeds this number of users")
                .format(ous=license_quantity))

    @staticmethod
    def _check_license_type_against_object_type(license, object_type):
        # type: (UdmObject, ObjectType) -> None
        """
        Check whether license with the given type
        can be assigned to the given type of object
        """
        license_type = license.props.license_type
        if license_type not in _ALLOWED_LICENSE_TYPES[object_type]:
            raise BiloAssignmentError(
                _("License with license type {license_type!r} "
                  "can't be assigned to the object type {object_type!r}")
                .format(license_type=license_type, object_type=object_type.value))

    def check_assigned_object(self, object_type, obj, license):
        # type: (ObjectType, UdmObject, UdmObject) -> None
        """
        Conduct different checks for the object to verify
        that it can be assigned to the selected license
        """
        self._check_license_type_against_object_type(license, object_type)
        if object_type is ObjectType.USER:
            self._check_license_school_against_user(license, obj)
            self._check_license_special_type_against_user(license, obj)
        elif object_type is ObjectType.GROUP:
            self._check_license_school_against_group(license, obj)
            self._check_license_special_type_against_group(license, obj)
            self._check_license_quantity_against_group(license, obj)
        elif object_type is ObjectType.SCHOOL:
            self._check_license_school_against_school(license, obj)
            self._check_license_quantity_against_school(license, obj)
        else:
            raise RuntimeError("Cannot handle object type: {}".format(object_type))

    def assign_license(self, license, object_type, object_name):
        # type: (UdmObject, ObjectType, str) -> bool
        """
        Assign license with code `license_code` to the object with `object_name`.

        :param UdmObject license: license object
        :param ObjectType object_type: type of the assigned object
        :param str object_name: name of the object to assign license to
        :return: true if the license could be assigned to the user, else raises an error.
        :rtype: bool
        :raises BiloAssignmentError: 1. If the `ignored` property is set. This should not happen,
            because only 'non-ignored' license codes should be passed to this method. 2. If the license
            was already assigned. 3. If no unassigned `bildungslogin/assignment` objects are available for the
            license.
        """
        self.check_assigned_license(license)
        assigned_object = self._get_object_by_name(object_type, object_name)
        self.check_assigned_object(object_type, assigned_object, license)
        object_uuid = get_entry_uuid(self._lo, dn=assigned_object.dn)
        # Check if the object was already assigned to the license
        if self.get_all_assignments_for_uuid(base=license.dn, assignee_uuid=object_uuid):
            return True

        available_assignments = self._get_available_assignments(license)
        if not available_assignments:
            raise BiloAssignmentError(
                _("There are no more assignments available "
                  "for the license with code {license_code!r}. "
                  "No license has been assigned to the object {object_name!r}!")
                .format(license_code=license.props.code, object_name=object_name))
        udm_assignment = available_assignments[0]
        udm_assignment.props.status = Status.ASSIGNED
        udm_assignment.props.assignee = object_uuid
        udm_assignment.props.time_of_assignment = datetime.date.today()
        udm_assignment.save()
        self.logger.debug(
            "Assigned license %r (%d left) to %r.",
            license.props.code,
            len(available_assignments) - 1,
            object_name)
        return True

    def assign_objects_to_licenses(self, license_codes, object_type, object_names):
        # type: (List[str], ObjectType, List[str]) -> Dict[str, Union[int, bool, List[str]]]
        """
        Assign a license to each object, from a list of potential licenses.

        1. If there are less available licenses than the number of objects,
            no licenses will be assigned.
        2. There can be more available licenses than the number of objects.
            The licenses will be sorted by validity end date.
            Licenses that end sooner will be used first.

        The result will be a dict with the number of users that licenses were assigned to, warning and
        error messages:

        {
            "countSuccessfulAssignments": int,  # number of objects that licenses were assigned to
            "notEnoughLicenses": bool,
            "failedAssignments": List[str],  # list of error messages
            "validityInFuture": List[str],  # list of license code whose validity lies in the future
        }

        :param list(str) license_codes: license codes to assign to users
        :param ObjectType object_type: type of objects being assigned
        :param list(str) object_names: names of objects to assign licenses to
        :return: dict with the number of objects that licenses were assigned to, warnings and errors
        :raises BiloAssignmentError: If the assignment process failed somewhere down the code path.
            Insufficient available licenses will not raise an exception, only add an error message in
            the result dict.
        """
        result = {
            "countSuccessfulAssignments": 0,
            "notEnoughLicenses": False,
            "failedAssignments": set(),
            "failedAssignmentsObjects": set(),
            "validityInFuture": set(),
        }
        licenses = []

        for lc in license_codes:
            license = self.get_license_by_license_code(lc)
            if license.props.expired:
                # this can only happen if the license expires after it was shown in the list
                # of assignable licenses (where expired licenses are filtered out)
                # The complexity to show this in addition to the 'notEnoughLicenses' error
                # seems not worth it.
                continue
            licenses.append(license)

        num_available_licenses = sum(lic.props.num_available for lic in licenses)
        if num_available_licenses < len(object_names):
            result["notEnoughLicenses"] = True
            result["failedAssignments"] = list(result["failedAssignments"])
            result["validityInFuture"] = list(result["validityInFuture"])
            return result

        # sort licenses by validity_end_date
        licenses.sort(key=lambda x: x.props.validity_end_date)
        # move licenses without validity_end_date to end of list
        licenses.sort(key=lambda x: bool(x.props.validity_end_date), reverse=True)

        # assign licenses

        # build an iterator of licenses to use: [license1, license1, license2, license2, ...]
        licenses_to_use = (
            license
            for license in licenses
            for _ in range(license.props.num_available)
        )
        for object_name in object_names:
            license = licenses_to_use.next()
            try:
                self.assign_license(license, object_type, object_name)
                result["countSuccessfulAssignments"] += 1
                if license.props.validity_start_date \
                        and license.props.validity_start_date > datetime.date.today():
                    result["validityInFuture"].add(license.props.code)
            except BiloAssignmentError as exc:
                result["failedAssignments"].add("{} -- {}".format(object_name, str(exc)))
                result["failedAssignmentsObjects"].add(object_name)
        self.logger.info(
            "Assigned licenses to %r/%r users.",
            result["countSuccessfulAssignments"],
            len(object_names)
        )
        result["failedAssignments"] = list(result["failedAssignments"])
        result["failedAssignmentsObjects"] = list(result["failedAssignmentsObjects"])
        result["validityInFuture"] = list(result["validityInFuture"])
        return result

    def get_assignment_for_object_under_license(self, license_dn, assignee):
        # type: (str, str)  -> UdmObject
        """
        Search for an assignment with license id and object with entryUUID.
        If multiple assignments found: return the first one.
        """
        filter_s = filter_format("(assignee=%s)", [assignee])
        try:
            return [a for a in self._assignments_mod.search(base=license_dn, filter_s=filter_s)][0]
        except IndexError:
            raise BiloAssignmentError(
                _("No assignment for license with {dn!r} was found for object {object_uuid!r}.")
                .format(dn=license_dn, object_uuid=assignee))

    def change_license_status(self, license_code, object_type, object_name, status):
        # type: (str, ObjectType, str, str) -> bool
        """
        Returns True if the license could be assigned to the user,
        returns False if the status remains and else raises an error.
        Status changes:
        ASSIGNED -> AVAILABLE
        ASSIGNED -> PROVISIONED
        AVAILABLE -> EXPIRED -> is calculated
        AVAILABLE -> ASSIGNED -> use assign_license instead
        AVAILABLE -> IGNORED -> handled at the license object
        """
        license = self.get_license_by_license_code(license_code)

        if status == Status.ASSIGNED:
            # comment: fallback for AVAILABLE -> ASSIGNED
            return self.assign_license(license=license, object_type=object_type,
                                       object_name=object_name)
        if status not in [Status.PROVISIONED, Status.AVAILABLE]:
            raise BiloAssignmentError(_("Illegal status change to {status!r}!")
                                      .format(status=status))

        self._check_license_is_ignored(license)
        object_uuid = self._get_object_uuid_by_name(object_type, object_name)
        udm_assignment = self.get_assignment_for_object_under_license(
            license_dn=license.dn, assignee=object_uuid)
        old_status = udm_assignment.props.status
        if status == old_status:
            self.logger.info(
                "Not changing any status for %r (%r -> %r).",
                object_name,
                udm_assignment.props.status,
                status)
            return False
        if status == Status.AVAILABLE:
            # assignments which are available do not have an assignee
            udm_assignment.props.assignee = None
            udm_assignment.props.time_of_assignment = None
        udm_assignment.props.status = status
        try:
            udm_assignment.save()
            self.logger.debug(
                "Changed status of assignment %r (-> %r) from %r to %r.",
                license_code,
                object_name,
                old_status,
                status)
        except ModifyError as exc:
            raise BiloAssignmentError(_("Invalid assignment status change!\n{exc}").format(exc=exc))
        return True

    def remove_assignment_from_objects(self, license_code, object_type, object_names):
        # type: (str, ObjectType, List[str]) -> List[Tuple[str, str]]
        num_removed_correct = 0
        failed_assignments = []
        for object_name in object_names:
            try:
                success = self.change_license_status(license_code=license_code,
                                                     object_type=object_type,
                                                     object_name=object_name,
                                                     status=Status.AVAILABLE)
                if success:
                    num_removed_correct += 1
            except BiloAssignmentError as err:
                # Error handling should be done in the umc - layer
                failed_assignments.append((object_name, str(err)))

        self.logger.info(
            "Removed %r/%r user-assignment to license code %r.",
            num_removed_correct,
            len(object_names),
            license_code,
        )
        return failed_assignments
