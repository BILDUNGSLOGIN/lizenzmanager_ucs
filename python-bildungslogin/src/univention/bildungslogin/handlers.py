<<<<<<< HEAD:python-bildungslogin/src/univention/bildungslogin/handler.py
# -*- coding: utf-8 -*-
# WIP, not all tested (!)
=======
#!/usr/share/ucs-test/runner /usr/bin/py.test -s
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

>>>>>>> issue #7: python-layer:python-bildungslogin/src/univention/bildungslogin/handlers.py
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ucsschool.lib.models.base import LoType, UdmObject

from typing import List, Optional, Set, Union

from ldap.filter import filter_format
from models import Assignment

from univention.admin.syntax import date
from univention.udm import UDM, CreateError, ModifyError, NoObject as UdmNoObject

from .execptions import (
    BiloAssignmentError,
    BiloCreateError,
    BiloLicenseNotFoundError,
    BiloProductNotFoundError,
)
from .models import License, MetaData
from .utils import Status, my_string_to_int

# DONE license position is not set correct @juern -> DONE (typo)

#
# DONE Mehrfachzuweisung einer Lizenz soll nicht moeglich sein
# (user, license) should be unique
#
# DONE create factory method for from_udm_obj lassen wir das mal
#
#
# DONE refactoring handlers @tobi
# DONE assignments in models ziehen
#
# DONE MetaDataHandler save + test @tobi
# DONE get_publishers +test @tobias
# todo get_license_types -> klaeren
# DONE get_all_product_ids -> @juern -> Test

# todo test special type ?
# -> in change status assign license


class LicenseHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._meta_data_mod = udm.get("vbm/metadata")
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
            self.logger.info("Created License object {}: {}".format(udm_obj.dn, udm_obj.props))
        except CreateError as e:
            raise BiloCreateError('Error creating license "{}"!\n{}'.format(license.license_code, e))
        for i in range(license.license_quantity):
            self.ah.create_assignment_for_licence(license_code=license.license_code)

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
        return self._get_all(filter_s=filter_s)

    def get_udm_license_by_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(code=%s)", [license_code])
        try:
            return self._get_all(filter_s)[0]
        except IndexError:
            raise BiloLicenseNotFoundError("License with code {} does not exist".format(license_code))

    def get_meta_data_for_license(self, license):  # type: (License) -> MetaData
        """search for the product of the license. If this there is none
        yet, return an empty object.
        """
        # here we have to use the mod directly to prevent recursion
        filter_s = filter_format("(product_id=%s)", [license.product_id])
        udm_meta_data = [o for o in self._meta_data_mod.search(filter_s)][0]
        if not udm_meta_data:
            return MetaData(product_id=license.product_id)
        else:
            return MetaDataHandler.from_udm_obj(udm_meta_data)

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

    def get_assignments_for_license_with_filter(
        self, license, filter_s
    ):  # type: (License, str) -> List[Assignment]
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
        return my_string_to_int(udm_license.props.num_available)

    def get_number_of_provisioned_and_assigned_assignments(self, license):  # type: (License) -> int
        """count the number of assignments with status provisioned or assigned
        provisioned is also assigned"""
        udm_license = self.get_udm_license_by_code(license.license_code)
        num_assigned = my_string_to_int(udm_license.props.num_assigned)
        return num_assigned

    def get_number_of_expired_assignments(self, license):  # type: (License) -> int
        """count the number of assignments with status expired
        todo comment: has to be fixed in udm"""
        udm_license = self.get_udm_license_by_code(license.license_code)
        return my_string_to_int(udm_license.props.num_expired)

    def get_total_number_of_assignments(self, license):  # type: (License) -> int
        """count the number of assignments for this license"""
        udm_license = self.get_udm_license_by_code(license.license_code)
        return my_string_to_int(udm_license.props.quantity)

    def get_time_of_last_assignment(self, license):  # type: (License) -> str
        """Get all assignments of this license and return the date of assignment,
        which was assigned last."""
        filter_s = filter_format("(|(status=%s)(status=%s))", [Status.ASSIGNED, Status.PROVISIONED])
        assignments = self.get_assignments_for_license_with_filter(filter_s=filter_s, license=license)
        max_datetime = max([date.to_datetime(a.time_of_assignment) for a in assignments])
        return date.from_datetime(max_datetime)


class MetaDataHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._meta_data_mod = udm.get("vbm/metadata")
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
            self.logger.info("Created MetaData object {}: {}".format(udm_obj.dn, udm_obj.props))
        except CreateError as e:
            BiloCreateError(
                'Error creating meta data for product id "{}"!\n{}'.format(meta_data.product_id, e)
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
            "Saving product MetaData object {}: {} -> {}".format(udm_obj.dn, props_before, udm_obj.props)
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
        assignments = self._meta_data_mod.search(filter_s=filter_s)
        return [MetaDataHandler.from_udm_obj(a) for a in assignments]

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

    def get_number_of_available_assignments(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status available"""
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        return sum(
            [my_string_to_int(udm_license.props.num_available) for udm_license in licenses_of_product]
        )

    def get_number_of_provisioned_and_assigned_assignments(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status provisioned or assigned"""
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        return sum(
            [my_string_to_int(udm_license.props.num_assigned) for udm_license in licenses_of_product]
        )

    def get_number_of_expired_assignments(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status expired
        todo comment: has to be fixed in udm"""
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        return sum(
            [my_string_to_int(udm_license.props.num_expired) for udm_license in licenses_of_product]
        )

    def get_total_number_of_assignments(self, meta_data):  # type: (MetaData) -> int
        """count the total number of assignments"""
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        return sum([my_string_to_int(udm_license.props.quantity) for udm_license in licenses_of_product])

    def get_meta_data_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(product_id=%s)", [product_id])
        try:
            return [o for o in self._meta_data_mod.search(filter_s)][0]
        except KeyError:
            raise BiloProductNotFoundError(
                "Meta data object with product id {} does not exist!".format(product_id)
            )

    def get_all_product_ids(self):  # type: () -> List[str]
        # todo udm kann nicht einzelne attr abfragen -> Performance problem
        return [o.product_id for o in self.get_all()]

    def get_all_publishers(self):  # type: () -> Set[str]
        return set(o.publisher for o in self.get_all())


class AssignmentHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._users_mod = udm.get("users/user")
        self.logger = logging.getLogger(__name__)

    def get_licence_of_assignment(self, dn):  # type: (str) -> UdmObject
        """Return the udm object of the license which is placed
        above the assignment. This is like 'get_parent'."""
        try:
            return self._licenses_mod.get(dn)
        except UdmNoObject:
            raise BiloLicenseNotFoundError("There is no license for the assignment {}!".format(dn))

    def from_udm_obj(self, udm_obj):  # type: (UdmObject) -> Assignment
        """
        Creates an Assignment object of an udm_obj. We do not save the license
        code directly on the assignments, so we have to ask the parent first.

        :param udm_obj: of assignment
        :return: assignment object
        """
        udm_license = self.get_licence_of_assignment(udm_obj.position)
        return Assignment(
            username=udm_obj.props.assignee,
            license=udm_license.props.code,
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

    def get_all_assignments_for_user(
        self, username, base=None
    ):  # type: (str, Optional[str]) -> List[Assignment]
        """if the base is equal to the dn of a license, this can be used to
        find all assignments for this license"""
        filter_s = filter_format("(assignee=%s)", [username])
        return self.get_all(base=base, filter_s=filter_s)

    def get_assignments_for_product_id_for_user(self, username, product_id):
        # type: (str, str) -> List[Assignment]
        """get all assignments for a product, which are assigned to a user."""
        filter_s = filter_format("(product_id=%s)", [product_id])
        udm_licenses = self._licenses_mod.search(filter_s)
        assignments = []
        for udm_license in udm_licenses:
            assignments.extend(self.get_all_assignments_for_user(username=username, base=udm_license.dn))
        return assignments

    @staticmethod
    def check_license_can_be_assigned_to_school_user(license_school, ucsschool_schools):
        # type: (str, List[str]) -> None
        if license_school not in ucsschool_schools:
            raise BiloAssignmentError(
                "License can't be assigned to user in school {}!".format(ucsschool_schools)
            )

    def get_user_by_username(self, username):  # type: (str) -> UdmObject
        filter_s = filter_format("(uid=%s)", [username])
        users = [u for u in self._users_mod.search(filter_s)]
        if not users:
            raise BiloAssignmentError("No user with username {} exists!".format(username))
        return users[0]

    def get_license_by_license_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(code=%s)", [license_code])
        try:
            license = [o for o in self._licenses_mod.search(filter_s)][0]
            return license
        except IndexError:
            raise BiloLicenseNotFoundError("No license with code {} was found!".format(license_code))

    def create_assignment_for_licence(self, license_code):  # type: (str) -> bool
        udm_license = self.get_license_by_license_code(license_code)
        try:
            assignment = self._assignments_mod.new(superordinate=udm_license.dn)
            assignment.props.status = Status.AVAILABLE
            assignment.save()
            self.logger.debug("Created Assignment object {}: {}".format(assignment.dn, assignment.props))
        except CreateError as e:
            raise BiloCreateError('Error creating assignment for "{}"!\n{}'.format(license_code, e))

    def _get_available_assignments(self, dn):  # type: (str) -> List[UdmObject]
        filter_s = filter_format("(status=%s)", [Status.AVAILABLE])
        return self._get_all(base=dn, filter_s=filter_s)

    def assign_to_license(self, license_code, username):  # type: (str, str) -> None
        udm_license = self.get_license_by_license_code(license_code)
        user = self.get_user_by_username(username)
        self.check_license_can_be_assigned_to_school_user(udm_license.props.school, user.props.school)
        assigned_to_user = self.get_all_assignments_for_user(base=udm_license.dn, username=username)
        if assigned_to_user:
            raise BiloAssignmentError(
                "License with code {} has already been assigned to {}".format(license_code, username)
            )

        available_licenses = self._get_available_assignments(udm_license.dn)
        if not available_licenses:
            raise BiloAssignmentError(
                "No assignment left of license with code {}. Failed to assign {}!".format(
                    license_code, username
                )
            )
        date_of_today = datetime.now().strftime("%Y-%m-%d")
        udm_assignment = available_licenses[0]
        udm_assignment.props.status = Status.ASSIGNED
        udm_assignment.props.assignee = username
        udm_assignment.props.time_of_assignment = date_of_today
        udm_assignment.save()
        logging.debug("Assigned license with license code {} to {}".format(license_code, username))

    def assign_users_to_license(self, licenses_code, usernames):  # type: (str, List[str]) -> None
        for username in usernames:
            self.assign_to_license(licenses_code, username)

    def get_assignment_for_user_under_license(self, license_dn, username):
        # type: (str, str)  -> UdmObject
        """Search for license with license id and user with username and change the status
        If a user has more than one license with license code under license_dn,
        we take the first license we can find."""
        filter_s = filter_format("(assignee=%s)", [username])
        try:
            return [a for a in self._assignments_mod.search(base=license_dn, filter_s=filter_s)][0]
        except IndexError:
            raise BiloAssignmentError(
                "No assignment for license with {} was found for user {}".format(license_dn, username)
            )

    def change_license_status(self, license_code, username, status):  # type: (str, str, str) -> None
        """
        AVAILABLE -> ASSIGNED
        ASSIGNED -> AVAILABLE
        AVAILABLE -> EXPIRED -> is calculated
        ASSIGNED -> PROVISIONED
        handled at the license object AVAILABLE -> IGNORED
        """
        udm_license = self.get_license_by_license_code(license_code)
        udm_assignment = self.get_assignment_for_user_under_license(
            license_dn=udm_license.dn, username=username
        )
        old_status = udm_assignment.props.status
        if status == old_status:
            self.logger.info(
                "Not changing any status for {} ({} -> {})".format(
                    username, udm_assignment.props.status, status
                )
            )
            return
        if status == Status.AVAILABLE:
            # assignments which are available do not have an assignee
            udm_assignment.props.assignee = None
        udm_assignment.props.status = status

        try:
            udm_assignment.save()
            logging.debug(
                "Changed status of assignment {},{} from {} to {}".format(
                    license_code, username, old_status, status
                )
            )
        except ModifyError as exc:
            raise BiloAssignmentError("Assignment status change is not valid!\n{}".format(exc))