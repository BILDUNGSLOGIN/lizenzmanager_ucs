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
import itertools
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

from ldap.filter import filter_format

from ucsschool.lib.roles import get_role_info
from univention.admin.syntax import iso8601Date
from univention.lib.i18n import Translation
from univention.udm import UDM, CreateError, ModifyError, NoObject as UdmNoObject

from .exceptions import (
    BiloAssignmentError,
    BiloCreateError,
    BiloLicenseNotFoundError,
    BiloProductNotFoundError,
)
from .models import Assignment, License, MetaData
from .utils import LicenseType, Status, get_entry_uuid, ldap_escape

if TYPE_CHECKING:
    from ucsschool.lib.models.base import LoType, UdmObject

_ = Translation("bildungslogin").translate


class LicenseHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("bildungslogin/license")
        self._assignments_mod = udm.get("bildungslogin/assignment")
        self._meta_data_mod = udm.get("bildungslogin/metadata")
        self._users_mod = udm.get("users/user")
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
            udm_obj.save()
            self.logger.debug("Created License object %r: %r", udm_obj.dn, udm_obj.props)
        except CreateError as exc:
            raise BiloCreateError(
                _("Error creating license {license_code!r}!\n{exc}").format(
                    license_code=license.license_code, exc=exc
                )
            )
        for i in range(license.license_quantity):
            self.ah.create_assignment_for_license(license_code=license.license_code)

    def get_assigned_users(self, license):  # type: (License) -> List[Dict[str, Any]]
        users = [
            {
                "username": a.assignee,
                "status": a.status,
                "statusLabel": Status.label(a.status),
                "dateOfAssignment": a.time_of_assignment,
            }
            for a in self.get_assignments_for_license_with_filter(license, "(assignee=*)")
        ]
        for user in users:
            udm_user = self._users_mod.search(filter_format("(entryUUID=%s)", [user["username"]])).next()
            user["username"] = udm_user.props.username
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
            purchasing_reference=udm_obj.props.purchasing_reference,
        )

    def from_dn(self, dn):  # type: (str) -> License
        udm_license = self._licenses_mod.get(dn)
        return self.from_udm_obj(udm_license)

    def _get_all(self, filter_s=None):  # type: (Optional[str]) -> List[UdmObject]
        return [o for o in self._licenses_mod.search(filter_s=filter_s)]

    def get_all(self, filter_s=None):  # type: (Optional[str]) -> List[License]
        """get all licenses"""
        return [self.from_udm_obj(udm_obj) for udm_obj in self._get_all(filter_s=filter_s)]

    def get_udm_license_by_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(code=%s)", [license_code])
        try:
            return self._get_all(filter_s)[0]
        except IndexError:
            raise BiloLicenseNotFoundError(
                _("License with code {license_code!r} does not exist.").format(license_code=license_code)
            )

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

    def get_assignments_for_license(self, license):
        # type: (Union[License,UdmObject]) -> List[Assignment]
        """helper function to search in udm layer"""
        if type(license) is License:
            udm_obj = self.get_udm_license_by_code(license.license_code)
        elif type(license) is str:
            raise ValueError("Wrong type for get_assignments_for_license!")
        else:
            udm_obj = license
        assignment_dns = udm_obj.props.assignments
        return [self.ah.from_dn(dn) for dn in assignment_dns]

    def get_assignments_for_license_with_filter(self, license, filter_s):
        # type: (License, str) -> List[Assignment]
        """search in assignments for license with license_code for filter_s e.g. for status"""
        udm_obj = self.get_udm_license_by_code(license.license_code)
        return [
            self.ah.from_udm_obj(obj)
            for obj in self._assignments_mod.search(base=udm_obj.dn, filter_s=filter_s)
        ]

    def get_all_assignments(self, license):  # type: (License) -> List[UdmObject]
        """search for assignments in leaves of license"""
        return self.get_assignments_for_license(license=license)

    def get_number_of_available_assignments(self, license):  # type: (License) -> int
        """count the number of assignments with status available"""
        udm_license = self.get_udm_license_by_code(license.license_code)
        return udm_license.props.num_available

    def get_number_of_provisioned_and_assigned_assignments(self, license):  # type: (License) -> int
        """count the number of assignments with status provisioned or assigned
        provisioned is also assigned"""
        udm_license = self.get_udm_license_by_code(license.license_code)
        return udm_license.props.num_assigned

    def get_number_of_expired_assignments(self, license):  # type: (License) -> int
        """count the number of assignments with status expired"""
        udm_license = self.get_udm_license_by_code(license.license_code)
        return udm_license.props.num_expired

    def get_total_number_of_assignments(self, license):  # type: (License) -> int
        """count the number of assignments for this license"""
        udm_license = self.get_udm_license_by_code(license.license_code)
        return udm_license.props.quantity

    def get_time_of_last_assignment(self, license):  # type: (License) -> datetime.date
        """Get all assignments of this license and return the date of assignment,
        which was assigned last."""
        filter_s = filter_format("(|(status=%s)(status=%s))", [Status.ASSIGNED, Status.PROVISIONED])
        assignments = self.get_assignments_for_license_with_filter(filter_s=filter_s, license=license)
        return max(a.time_of_assignment for a in assignments)

    def get_licenses_for_user(self, filter_s):  # type: (str) -> Set[UdmObject]
        users = self._users_mod.search(filter_s)
        licenses = set()
        for user in users:
            entry_uuid = get_entry_uuid(self._users_mod.connection, user.dn)
            assignments = self.ah.get_all_assignments_for_user(entry_uuid)
            for assignment in assignments:
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
        ]

    def search_for_licenses(
        self,
        school,  # type: str
        is_advanced_search,  # type: bool
        time_from=None,  # type: Optional[datetime.date]
        time_to=None,  # type: Optional[datetime.date]
        only_available_licenses=False,  # type: Optional[bool]
        publisher="",  # type: Optional[str]
        license_type="",  # type: Optional[str]
        user_pattern="",  # type: Optional[str]
        product_id="",  # type: Optional[str]
        product="",  # type: Optional[str]
        license_code="",  # type: Optional[str]
        pattern="",  # type: Optional[str]
        restrict_to_this_product_id="",  # type: Optional[str]
    ):
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
                filter_parts.append("({attr}={pattern})".format(attr=attr, pattern=ldap_escape(pattern)))
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
            if license_type == LicenseType.SINGLE:
                filter_parts.append("(bildungsloginLicenseQuantity=1)")
            elif license_type == LicenseType.VOLUME:
                filter_parts.append("(!(bildungsloginLicenseQuantity=1))")
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
            if user_pattern and user_pattern != "*":
                possible_licenses = self.get_licenses_for_user(
                    "(|(firstname={user_pattern})(sn={user_pattern})(uid={user_pattern}))".format(
                        user_pattern=ldap_escape(user_pattern)
                    )
                )
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
        for license in self.get_all(filter_s=filter_s):
            meta_data = self.get_meta_data_for_license(license)
            if not only_available_licenses or (
                not license.ignored_for_display and self.get_number_of_available_assignments(license) > 0
            ):
                rows.append(
                    {
                        "productId": license.product_id,
                        "productName": meta_data.title,
                        "publisher": meta_data.publisher,
                        "licenseCode": license.license_code,
                        "licenseTypeLabel": LicenseType.label(license.license_type),
                        "countAquired": self.get_total_number_of_assignments(license),
                        "countAssigned": self.get_number_of_provisioned_and_assigned_assignments(
                            license
                        ),
                        "countExpired": self.get_number_of_expired_assignments(license),
                        "countAvailable": self.get_number_of_available_assignments(license),
                        "importDate": license.delivery_date,
                    }
                )
        return rows


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

    def from_dn(self, dn):  # type: (str) -> MetaData
        udm_license = self._meta_data_mod.get(dn)
        return self.from_udm_obj(udm_license)

    def get_all(self, filter_s=None):  # type: (str) -> List[MetaData]
        meta_data_objs = self._meta_data_mod.search(filter_s=filter_s)
        return [MetaDataHandler.from_udm_obj(obj) for obj in meta_data_objs]

    def get_udm_licenses_by_product_id(self, product_id):  # type: (str) -> List[UdmObject]
        filter_s = filter_format("(product_id=%s)", [product_id])
        return [o for o in self._licenses_mod.search(filter_s)]

    def get_assignments_for_meta_data(self, meta_data):  # type: (MetaData) -> List[Assignment]
        """assignments of license with productID"""
        # get licenses objects from udm with the given product id.
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        assignments = []
        for udm_license in licenses_of_product:
            # get the assignments placed below the licenses.
            assignments.extend(self.lh.get_assignments_for_license(udm_license))

        return assignments

    def get_non_ignored_licenses_for_product_id(self, product_id):  # type: (str) -> List[UdmObject]
        licenses_of_product = self.get_udm_licenses_by_product_id(product_id)
        return [udm_license for udm_license in licenses_of_product if not udm_license.props.ignored]

    def get_number_of_available_assignments(
        self, meta_data, school=None
    ):  # type: (MetaData, Optional[str]) -> int
        """count the number of assignments with status available"""
        licenses_of_product = self.get_non_ignored_licenses_for_product_id(meta_data.product_id)
        if school:
            licenses_of_product = [
                license for license in licenses_of_product if license.props.school == school
            ]
        return sum(udm_license.props.num_available for udm_license in licenses_of_product)

    def get_number_of_provisioned_and_assigned_assignments(
        self, meta_data, school=None
    ):  # type: (MetaData, Optional[str]) -> int
        """count the number of assignments with status provisioned or assigned"""
        licenses_of_product = self.get_non_ignored_licenses_for_product_id(meta_data.product_id)
        if school:
            licenses_of_product = [
                license for license in licenses_of_product if license.props.school == school
            ]
        return sum(udm_license.props.num_assigned for udm_license in licenses_of_product)

    def get_number_of_expired_assignments(
        self, meta_data, school=None
    ):  # type: (MetaData, Optional[str]) -> int
        """count the number of assignments with status expired"""
        licenses_of_product = self.get_non_ignored_licenses_for_product_id(meta_data.product_id)
        if school:
            licenses_of_product = [
                license for license in licenses_of_product if license.props.school == school
            ]
        return sum(udm_license.props.num_expired for udm_license in licenses_of_product)

    def get_total_number_of_assignments(
        self, meta_data, school=None
    ):  # type: (MetaData, Optional[str]) -> int
        """count the total number of assignments"""
        licenses_of_product = self.get_non_ignored_licenses_for_product_id(meta_data.product_id)
        if school:
            licenses_of_product = [
                license for license in licenses_of_product if license.props.school == school
            ]
        return sum(udm_license.props.quantity for udm_license in licenses_of_product)

    def get_meta_data_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(product_id=%s)", [product_id])
        try:
            return [o for o in self._meta_data_mod.search(filter_s)][0]
        except IndexError:
            raise BiloProductNotFoundError(
                _("Meta data object with product id {p_id!r} does not exist!").format(p_id=product_id)
            )

    def get_all_product_ids(self):  # type: () -> List[str]
        # todo udm kann nicht einzelne attr abfragen -> Performance problem
        return [o.product_id for o in self.get_all()]

    def get_all_publishers(self):  # type: () -> Set[str]
        return set(o.publisher for o in self.get_all())


class AssignmentHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("bildungslogin/license")
        self._assignments_mod = udm.get("bildungslogin/assignment")
        self._users_mod = udm.get("users/user")
        self._lo = lo
        self.logger = logging.getLogger(__name__)

    def get_license_of_assignment(self, dn):  # type: (str) -> UdmObject
        """Return the udm object of the license which is placed
        above the assignment. This is like 'get_parent'."""
        try:
            return self._licenses_mod.get(dn)
        except UdmNoObject:
            raise BiloLicenseNotFoundError(
                _("There is no license for the assignment {dn!r}!").format(dn=dn)
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

    def from_dn(self, dn):  # type: (str) -> Assignment
        udm_license = self._assignments_mod.get(dn)
        return self.from_udm_obj(udm_license)

    def _get_all(self, base=None, filter_s=None):  # type: (str, str) -> List[UdmObject]
        return [o for o in self._assignments_mod.search(base=base, filter_s=filter_s)]

    def get_all(self, base=None, filter_s=None):  # type: (str, str) -> List[Assignment]
        udm_assignments = self._get_all(base=base, filter_s=filter_s)
        return [self.from_udm_obj(a) for a in udm_assignments]

    def get_all_assignments_for_user(self, assignee, base=None):
        # type: (str, Optional[str]) -> List[Assignment]
        """
        if the base is equal to the dn of a license, this can be used to
        find all assignments for this license

        :param assignee: entry-uuid of user
        :param base: dn of license object
        :return:
        """
        filter_s = filter_format("(assignee=%s)", [assignee])
        return self.get_all(base=base, filter_s=filter_s)

    def _get_entry_uuid_by_username(self, username):  # type: (str) -> str
        udm_user = self.get_user_by_username(username)
        return get_entry_uuid(self._lo, dn=udm_user.dn)

    def get_assignments_for_product_id_for_user(self, username, product_id):
        # type: (str, str) -> List[Assignment]
        """get all assignments for a product, which are assigned to a user."""
        user_entry_uuid = self._get_entry_uuid_by_username(username)
        filter_s = filter_format("(product_id=%s)", [product_id])
        udm_licenses = self._licenses_mod.search(filter_s)
        assignments = []
        for udm_license in udm_licenses:
            assignments.extend(
                self.get_all_assignments_for_user(assignee=user_entry_uuid, base=udm_license.dn)
            )
        return assignments

    @staticmethod
    def check_license_can_be_assigned_to_school_user(license_school, ucsschool_schools):
        # type: (str, List[str]) -> None
        ucsschool_schools = [s.lower() for s in ucsschool_schools]
        if license_school.lower() not in ucsschool_schools:
            raise BiloAssignmentError(
                _("License can't be assigned to user in schools {ous}!").format(ous=ucsschool_schools)
            )

    def get_user_by_username(self, username):  # type: (str) -> UdmObject
        filter_s = filter_format("(uid=%s)", [username])
        users = [u for u in self._users_mod.search(filter_s)]
        if not users:
            raise BiloAssignmentError(_("No user with username {un!r} exists!").format(un=username))
        return users[0]

    def get_license_by_license_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(code=%s)", [license_code])
        try:
            license = [o for o in self._licenses_mod.search(filter_s)][0]
            return license
        except IndexError:
            raise BiloLicenseNotFoundError(
                _("No license with code {license_code!r} was found!").format(license_code=license_code)
            )

    def create_assignment_for_license(self, license_code):  # type: (str) -> bool
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

    def _get_available_assignments(self, license_dn):  # type: (str) -> List[UdmObject]
        filter_s = filter_format("(status=%s)", [Status.AVAILABLE])
        return self._get_all(base=license_dn, filter_s=filter_s)

    @staticmethod
    def check_license_type_is_correct(username, user_roles, license_type):
        # type: (str, List[str], str) -> None
        # todo check if we need this in mvb, also make this more robust
        if license_type == "Lehrer":
            roles = [get_role_info(role)[0] for role in user_roles]
            if "student" in roles:
                raise BiloAssignmentError(
                    _(
                        "License with special type 'Lehrer' can't be assigned to user {username!r} with "
                        "roles {roles!r}!"
                    ).format(username=username, roles=roles)
                )

    @staticmethod
    def check_is_ignored(ignored):  # type: (bool) -> None
        if ignored:
            raise BiloAssignmentError(_("License is 'ignored for display' and thus can't be assigned!"))

    @staticmethod
    def check_is_expired(expired):  # type: (bool) -> None
        if expired:
            raise BiloAssignmentError(_("License is expired and thus can't be assigned!"))

    def assign_to_license(self, license_code, username):  # type: (str, str) -> bool
        """
        Assigne license with code `license_code` to `username`.

        :param str license_code: license code
        :param str username: user name of user to assigne license to
        :return: true if the license could be assigned to the user, else raises an error.
        :rtype: bool
        :raises BiloAssignmentError: 1. If the `ignored` property is set. This should not happen,
            because only 'non-ignored' license codes should be passed to this method. 2. If the license
            was already assigned. 3. If no unassigned `bildungslogin/assignment` objects are available for the
            license.
        """
        udm_license = self.get_license_by_license_code(license_code)
        self.check_is_ignored(udm_license.props.ignored)
        self.check_is_expired(udm_license.props.expired)
        udm_user = self.get_user_by_username(username)
        self.check_license_can_be_assigned_to_school_user(
            udm_license.props.school, udm_user.props.school
        )
        self.check_license_type_is_correct(
            username, udm_user.props.ucsschoolRole, udm_license.props.special_type
        )
        user_entry_uuid = get_entry_uuid(self._lo, dn=udm_user.dn)
        assigned_to_user = self.get_all_assignments_for_user(
            base=udm_license.dn, assignee=user_entry_uuid
        )
        if assigned_to_user:
            return True
        available_licenses = self._get_available_assignments(udm_license.dn)
        if not available_licenses:
            raise BiloAssignmentError(
                _(
                    "No assignment left of license with code {license_code!r}. Failed to assign "
                    "{username!r}!"
                ).format(license_code=license_code, username=username)
            )
        udm_assignment = available_licenses[0]
        udm_assignment.props.status = Status.ASSIGNED
        udm_assignment.props.assignee = user_entry_uuid
        udm_assignment.props.time_of_assignment = datetime.date.today()
        udm_assignment.save()
        self.logger.debug(
            "Assigned license %r (%d left) to %r.", license_code, len(available_licenses) - 1, username
        )
        return True

    def assign_users_to_licenses(self, license_codes, usernames):
        # type: (List[str], List[str]) -> Dict[str, Union[int, Dict[str, str]]]
        """
        Assign a license to each user, from a list of potential licenses.

        1. If there are less available licenses than the number of users, no licenses will be assigned.
        2. There can be more available licenses than the number of users. The licenses will be sorted by
        validity end date. Licenses that end sooner will be used first.

        The result will be a dict with the number of users that licenses were assigned to, warning and
        error messages:

        {
            "countSuccessfulAssignments": int,  # number of users that licenses were assigned to
            "notEnoughLicenses": bool,
            "failedAssignments": List[str],  # list of error messages
            "validityInFuture": List[str],  # list of license code whose validity lies in the future
        }

        :param list(str) license_codes: license codes to assign to users
        :param list(str) usernames: uids of users to assign licenses to
        :return: dict with the number of users that licenses were assigned to, warnings and errors
        :rtype: dict
        :raises BiloAssignmentError: If the assignment process failed somewhere down the code path.
            Insufficient available licenses will not raise an exception, only add an error message in
            the result dict.
        """
        result = {
            "countSuccessfulAssignments": 0,
            "notEnoughLicenses": False,
            "failedAssignments": set(),
            "validityInFuture": set(),
        }
        licenses = []

        for lc in license_codes:
            license = self.get_license_by_license_code(lc)
            try:
                self.check_is_expired(license.props.expired)
                licenses.append(license)
            except BiloAssignmentError:
                # this can only happen if the license expires after it was shown in the list
                # of assignable licenses (where expired licenses are filtered out)
                # The complexity to show this in addition to the 'notEnoughLicenses' error
                # seems not worth it.
                pass

        num_available_licenses = sum(lic.props.num_available for lic in licenses)
        if num_available_licenses < len(usernames):
            result["notEnoughLicenses"] = True
            result["failedAssignments"] = list(result["failedAssignments"])
            result["validityInFuture"] = list(result["validityInFuture"])
            return result

        # sort licenses by validity_end_date
        licenses.sort(key=lambda x: x.props.validity_end_date)
        # move licenses without validity_end_date to end of list
        licenses.sort(key=lambda x: bool(x.props.validity_end_date), reverse=True)

        # assign licenses

        # build list of licenses to use: [code1, code1, code1, code2, code2, ...] as an iterator (list
        # could be very long)!
        license_codes_to_use = itertools.chain.from_iterable(
            (
                (license.props.code, license.props.validity_start_date)
                for _ in range(license.props.num_available)
            )
            for license in licenses
        )
        for username in usernames:
            code, validity_start_date = license_codes_to_use.next()
            try:
                self.assign_to_license(code, username)
                result["countSuccessfulAssignments"] += 1
                if validity_start_date > datetime.date.today():
                    result["validityInFuture"].add(code)
            except BiloAssignmentError as exc:
                result["failedAssignments"].add("{} -- {}".format(username, str(exc)))
        self.logger.info(
            "Assigned licenses to %r/%r users.", result["countSuccessfulAssignments"], len(usernames)
        )
        result["failedAssignments"] = list(result["failedAssignments"])
        result["validityInFuture"] = list(result["validityInFuture"])
        return result

    def get_assignment_for_user_under_license(self, license_dn, assignee):
        # type: (str, str)  -> UdmObject
        """Search for license with license id and user with username and change the status
        If a user has more than one license with license code under license_dn,
        we take the first license we can find."""
        filter_s = filter_format("(assignee=%s)", [assignee])
        try:
            return [a for a in self._assignments_mod.search(base=license_dn, filter_s=filter_s)][0]
        except IndexError:
            raise BiloAssignmentError(
                _("No assignment for license with {dn!r} was found for user {username!r}.").format(
                    dn=license_dn, username=assignee
                )
            )

    def change_license_status(self, license_code, username, status):  # type: (str, str, str) -> bool
        """
        Returns True if the license could be assigned to the user,
        returns False if the status remains and else raises an error.
        Status changes:
        ASSIGNED -> AVAILABLE
        ASSIGNED -> PROVISIONED
        AVAILABLE -> EXPIRED -> is calculated
        AVAILABLE -> ASSIGNED -> use assign_to_license instead
        AVAILABLE -> IGNORED -> handled at the license object
        """
        if status == Status.ASSIGNED:
            # comment: fallback for AVAILABLE -> ASSIGNED
            return self.assign_to_license(license_code=license_code, username=username)
        if status not in [Status.PROVISIONED, Status.AVAILABLE]:
            raise BiloAssignmentError(_("Illegal status change to {status!r}!").format(status=status))

        udm_license = self.get_license_by_license_code(license_code)
        self.check_is_ignored(udm_license.props.ignored)
        user_entry_uuid = self._get_entry_uuid_by_username(username)

        udm_assignment = self.get_assignment_for_user_under_license(
            license_dn=udm_license.dn, assignee=user_entry_uuid
        )
        old_status = udm_assignment.props.status
        if status == old_status:
            self.logger.info(
                "Not changing any status for %r (%r -> %r).",
                username,
                udm_assignment.props.status,
                status,
            )
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
                username,
                old_status,
                status,
            )
        except ModifyError as exc:
            raise BiloAssignmentError(_("Invalid assignment status change!\n{exc}").format(exc=exc))
        return True

    def remove_assignment_from_users(self, license_code, usernames):
        # type: (str, List[str]) -> List[Tuple[str, str]]
        # TODO: result wie oben, mit user-dn statt lic-code
        num_removed_correct = 0
        failed_assignments = []
        for username in usernames:
            try:
                success = self.change_license_status(
                    license_code=license_code, username=username, status=Status.AVAILABLE
                )
                if success:
                    num_removed_correct += 1
            except BiloAssignmentError as err:
                # Error handling should be done in the umc - layer
                failed_assignments.append((username, str(err)))

        self.logger.info(
            "Removed %r/%r user-assignment to license code %r.",
            num_removed_correct,
            len(usernames),
            license_code,
        )
        return failed_assignments
