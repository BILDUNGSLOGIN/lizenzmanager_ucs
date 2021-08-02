# WIP, not all tested (!)
from datetime import datetime

import univention
import univention.admin.uexceptions
from typing import Optional
from ucsschool.lib.models import SchoolClass, WorkGroup, User
from univention.admin.syntax import date

from models import License

try:
    # todo
    from ucsschool.lib.models.base import LoType, UdmObject
except ImportError:
    pass

from models import MetaData

from ldap.filter import filter_format
from typing import List, Union


from univention.udm import UDM, CreateError, NoObject as UdmNoObject

from .utils import Status, Assignment, get_logger

# todo
logger = get_logger()


class BiloCreateError(CreateError):
    pass


class BiloAssignmentError(Exception):
    pass


class BiloProductNotFoundError(Exception):
    pass


class BiloLicenseNotFoundError(Exception):
    pass


# we thought it would be nice to have at least some of this in a basehandler, maybe revisit for refactoring
# -> recursion
# alternatively in function

# class BaseHandler:
#     def __init__(self, lo):  # type: (LoType) -> None
#         udm = UDM(lo).version(1)
#         self._licenses_mod = udm.get("vbm/license")
#         self._assignments_mod = udm.get("vbm/assignment")
#         self._meta_data_mod = udm.get("vbm/metadatum")
#         if type(self) is not LicenseHandler:
#             self.lh = LicenseHandler(lo)
#         if type(self) is not AssignmentHandler:
#             self.ah = AssignmentHandler(lo)
#         if type(self) is not MetaDataHandler:
#             self.mh = MetaDataHandler(lo)


def my_string_to_int(num):  # type: (str) -> int
    return int(num) if num else 0


class LicenseHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._meta_data_mod = udm.get("vbm/metadatum")
        self.ah = AssignmentHandler(lo)

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
            # logger.debug("")
        except CreateError as e:
            raise BiloCreateError(
                "Error creating license \"{}\"!\n{}".format(license.license_code, e)
            )
        for i in range(license.license_quantity):
            self.ah.create_assignments_for_licence(license_code=license.license_code)

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

    def get_all(self, filter_s=None):  # type: (Optional[str]) -> List[License]
        """get all licenses"""
        udm_licenses = self._licenses_mod.search(filter_s=filter_s)
        return [LicenseHandler.from_udm_obj(a) for a in udm_licenses]

    def get_udm_license(self, license_code):  # type: (str) -> UdmObject
        """todo move me into a factory"""
        filter_s = filter_format("(code=%s)", [license_code])
        return [o for o in self._licenses_mod.search(filter_s)][0]

    def get_meta_data_for_license(self, license):  # type: (License) -> MetaData
        """search for the product of the license. If this there is none
        yet, return an empty object.
        """
        filter_s = filter_format("(product_id=%s)", [license.product_id])
        udm_meta_data = [o for o in self._meta_data_mod.search(filter_s)][0]
        if not udm_meta_data:
            return MetaData(product_id=license.product_id)
        else:
            return MetaDataHandler.from_udm_obj(udm_meta_data)

    def get_assignments_for_license(
        self, license
    ):  # type: (Union[License,UdmObject]) -> List[Assignment]
        """helper function to search in udm layer"""
        if type(license) is License:
            udm_obj = self.get_udm_license(license.license_code)
        elif type(license) is str:
            raise ValueError("Wrong type for get_assignments_for_license!")
        else:
            udm_obj = license
        assignment_dns = udm_obj.props.assignments
        return [self.ah.from_dn(dn) for dn in assignment_dns]

    def assignments_search(
        self, filter_s, license
    ):  # type: (Optional[str], License) -> List[Assignment]
        """search in assignments for filter_s
        todo meditate on usefulness"""
        udm_obj = self.get_udm_license(license.license_code)
        return [
            self.ah.from_udm_obj(obj)
            for obj in self._assignments_mod.search(base=udm_obj.dn, filter_s=filter_s)
        ]

    def get_all_assignments(self, license):  # type: (License) -> List[UdmObject]
        """search for assignments in leaves of license"""
        return self.get_assignments_for_license(license=license)

    def get_number_of_available_assignments(self, license):  # type: (License) -> int
        """count the number of assignments with status available"""
        udm_license = self.get_udm_license(license.license_code)
        return my_string_to_int(udm_license.props.num_available)

    def get_number_of_provisioned_and_assigned_assignments(
        self, license
    ):  # type: (License) -> int
        """count the number of assignments with status provisioned or assigned
        provisioned is also assigned"""
        udm_license = self.get_udm_license(license.license_code)
        num_assigned = my_string_to_int(udm_license.num_assigned)
        return num_assigned

    def get_number_of_expired_assignments(self, license):  # type: (License) -> int
        """count the number of assignments with status expired
        todo comment: has to be fixed in udm"""
        udm_license = self.get_udm_license(license.license_code)
        return my_string_to_int(udm_license.props.num_expired)

    def get_number_of_assignments(self, license):  # type: (License) -> int
        """count the number of assignments for this license"""
        udm_license = self.get_udm_license(license.license_code)
        return my_string_to_int(udm_license.props.quantity)

    def get_time_of_last_assignment(self, license):  # type: (License) -> str
        """Get all assignments of this license and return the date of assignment,
        which was assigned last."""
        # todo assignment -> sublicense
        filter_s = filter_format(
            "(|(status=%s)(status=%s))", [Status.ASSIGNED, Status.PROVISIONED]
        )
        assignments = self.assignments_search(filter_s=filter_s, license=license)
        max_datetime = max(
            [date.to_datetime(a.time_of_assignment) for a in assignments]
        )
        return date.from_datetime(max_datetime)

    # """this seems like another layer & out of scope"""
    #
    # def search_for_license_code(self, udm, filter_s):  # type: (UDM, Optional[str]) -> List[Dict[str, str]]
    #     """the filter_s can be used to filter license attributes, e.g. license codes
    #     todo check
    #     eigentlich nicht teil dieser userstory - wollen wir eine freitext-suche tatsaechlich im mvp?"""
    #     rows = []
    #     for license in self.get_all(filter_s=filter_s):
    #         meta_data = self.get_meta_data_for_license(license)
    #
    #         rows.append({
    #             "product_id": license.product_id,
    #             "product": meta_data.title,
    #             "publisher": meta_data.publisher,
    #             "license_code": license.license_code,
    #             "type": str(license.license_type),
    #             "time_of_assignment": self.get_time_of_last_assignment(license),
    #             "assigned": self.get_number_of_provisioned_and_assigned_licenses(license),
    #             "acquired": self.get_number_of_licenses(license),
    #             "expired": self.get_number_of_expired_licenses(license),
    #             "available": self.get_number_of_available_licenses(license)
    #         })
    #     return rows


class MetaDataHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._meta_data_mod = udm.get("vbm/metadatum")
        self.ah = AssignmentHandler(lo)
        self.lh = LicenseHandler(lo)

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
            print(udm_obj.dn)
        except CreateError as e:
            # todo
            BiloCreateError(
                "Error creating meta datum for product id \"{}\"!\n{}".format(
                    meta_data.product_id, e
                )
            )

    def save(self, meta_data):  # type: (MetaData) -> None
        # udm_meta_data = self.get_meta_data_by_product_id(meta_data.product_id)
        # todo update udm_meta_data
        # udm_meta_data.save()
        raise NotImplementedError

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

    def fetch_meta_data(self, meta_data):  # type: (MetaData) -> None
        """call meta-data api"""
        raise NotImplementedError

    def get_udm_licenses_by_product_id(
        self, product_id
    ):  # type: (str) -> List[UdmObject]
        filter_s = filter_format("(product_id=%s)", [product_id])
        return [o for o in self._licenses_mod.search(filter_s)]

    def get_assignments_for_meta_data(
        self, meta_data
    ):  # type: (MetaData) -> List[Assignment]
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
            [
                my_string_to_int(udm_license.props.num_available)
                for udm_license in licenses_of_product
            ]
        )

    def get_number_of_provisioned_and_assigned_assignments(
        self, meta_data
    ):  # type: (MetaData) -> int
        """count the number of assignments with status provisioned or assigned"""
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        return sum(
            [
                my_string_to_int(udm_license.props.num_assigned)
                for udm_license in licenses_of_product
            ]
        )

    def get_number_of_expired_assignments(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status expired
        todo comment: has to be fixed in udm"""
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        return sum(
            [
                my_string_to_int(udm_license.props.num_expired)
                for udm_license in licenses_of_product
            ]
        )

    def get_number_of_assignments(self, meta_data):  # type: (MetaData) -> int
        """count the total number of assignments"""
        licenses_of_product = self.get_udm_licenses_by_product_id(meta_data.product_id)
        return sum(
            [
                my_string_to_int(udm_license.props.quantity)
                for udm_license in licenses_of_product
            ]
        )

    def get_meta_data_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(product_id=%s)", [product_id])
        try:
            return [o for o in self._meta_data_mod.search(filter_s)][0]
        except KeyError:
            raise BiloProductNotFoundError(
                "Meta data object with product id {} does not exist!".format(product_id)
            )


class AssignmentHandler:
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._users_mod = udm.get("users/user")

    def get_licence_of_assignment(self, dn):  # type: (str) -> UdmObject
        """Return the udm object of the license which is placed
        above the assignment. This is like 'get_parent'."""
        try:
            return self._licenses_mod.get(dn)
        except UdmNoObject:
            # todo
            raise BiloLicenseNotFoundError(
                "There is no license for the assignment {}!".format(dn)
            )

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

    def get_all(self, filter_s=None):  # type: (str) -> List[Assignment]
        udm_assignments = self._assignments_mod.search(filter_s=filter_s)
        return [self.from_udm_obj(a) for a in udm_assignments]

    def get_all_assignments_for_user(self, username):  # type: (str) -> List[Assignment]
        filter_s = filter_format("(assignee=%s)", [username])
        udm_assignments = self._assignments_mod.search(filter_s)
        return [self.from_udm_obj(a) for a in udm_assignments]

    def get_assignments_for_product_id_for_user(
        self, username, product_id
    ):  # type: (str, str) -> List[Assignment]
        """get all assignments for a product, which are assigned to a user."""
        # do we need this?
        filter_s = filter_format("(product_id=%s)", [product_id])
        udm_licenses = self._licenses_mod.search(filter_s)
        assignments = []
        for udm_license in udm_licenses:
            filter_s = filter_format("(assignee=%s)", [username])
            udm_assignments = [
                a
                for a in self._assignments_mod.search(
                    base=udm_license.dn, filter_s=filter_s
                )
            ]
            assignments.extend(udm_assignments)

        return [self.from_udm_obj(a) for a in assignments]

    @staticmethod
    def check_license_can_be_assigned_to_school_user(license_school, ucsschool_school):
        # type: (str, List[str]) -> None
        """todo check is school multi-value in udm?"""
        if license_school not in ucsschool_school:
            raise BiloAssignmentError(
                "License can't be assigned to user in school {}!".format(
                    ucsschool_school
                )
            )

    def get_user_by_username(self, username):  # type: (str) -> UdmObject
        filter_s = filter_format("(uid=%s)", [username])
        users = [u for u in self._users_mod.search(filter_s)]
        if not users:
            # todo
            raise BiloAssignmentError("No user with username {} exists!".format(username))
        return users[0]

    def get_license_by_license_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(code=%s)", [license_code])
        try:
            license = [o for o in self._licenses_mod.search(filter_s)][0]
            return license
        except IndexError:
            # todo
            raise BiloLicenseNotFoundError(
                "No license with code {} was found!".format(license_code)
            )

    def create_assignments_for_licence(self, license_code):  # type: (str) -> bool
        """refactor me"""
        udm_license = self.get_license_by_license_code(license_code)
        try:
            assignment = self._assignments_mod.new(superordinate=udm_license.dn)
            assignment.props.status = Status.AVAILABLE
            assignment.save()
        except CreateError as e:
            # todo
            raise BiloCreateError(
                "Error creating assignment for \"{}\"!\n{}".format(license_code, e)
            )

    def _get_available_assignments(self, dn):  # type: (str) -> List[UdmObject]
        filter_s = filter_format(
            "(status=%s)", [Status.AVAILABLE]
        )
        return [
            obj
            for obj in self._assignments_mod.search(
                base=dn, filter_s=filter_s
            )
        ]

    def assign_to_license(self, license_code, username):  # type: (str, str) -> None
        udm_license = self.get_license_by_license_code(license_code)
        user = self.get_user_by_username(username)
        self.check_license_can_be_assigned_to_school_user(
            udm_license.props.school, user.props.school
        )
        available_licenses = self._get_available_assignments(udm_license.dn)
        if not available_licenses:
            raise BiloAssignmentError(
                "No assignment left of license with code {}. Failed to assign {}!".format(
                    license_code, username
                )
            )
        date_of_today = datetime.now().isoformat().split("T")[0]
        # todo error handling
        udm_assignment = available_licenses[0]
        udm_assignment.props.status = Status.ASSIGNED
        udm_assignment.props.assignee = username
        udm_assignment.props.time_of_assignment = date_of_today
        # todo logging
        print(udm_assignment.props)
        udm_assignment.save()

    def assign_users_to_license(
        self, licenses_code, usernames
    ):  # type: (str, List[str]) -> None
        """A license can be assigned,
        if the amount of licenses is sufficient to assign it to all users.
        We do not check if the license is valid at this point. The valid licenses,
        are passed from the frontend, right? todo
        """
        for username in usernames:
            self.assign_to_license(licenses_code, username)

    def get_assignment_for_user_under_license(
        self, license_dn, username
    ):  # type: (str, str)  -> UdmObject
        """Search for license with license id and user with username and change the status
        If a user has more than one license with license code under license_dn,
        we take the first license we can find."""
        filter_s = filter_format("(assignee=%s)", [username])
        return [
            a for a in self._assignments_mod.search(base=license_dn, filter_s=filter_s)
        ][0]

    def change_license_status(
        self, license_code, username, status
    ):  # type: (str, str, str) -> None
        """
        AVAILABLE -> ASSIGNED
        ASSIGNED -> AVAILABLE
        AVAILABLE -> EXPIRED -> is calculated
        ASSIGNED -> PROVISIONED
        handled at the license object AVAILABLE -> IGNORED
        username has to be present except if license expired (or valid-date)

        """
        udm_license = self.get_license_by_license_code(license_code)
        udm_assignment = self.get_assignment_for_user_under_license(
            license_dn=udm_license.dn, username=username
        )
        udm_assignment.props.status = status
        try:
            udm_assignment.save()
        except univention.admin.uexceptions.valueError as exc:
            raise BiloAssignmentError("Assigment status change is not valid!\n{}".format(exc))
