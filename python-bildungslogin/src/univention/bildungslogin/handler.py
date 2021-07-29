# WIP, not tested (!)


from typing import Optional
from univention.admin.syntax import date

from models import License

try:
    # todo
    from ucsschool.lib.models.base import LoType, UdmObject
except ImportError:
    pass

from models import MetaData

from time import time

from ldap.filter import filter_format
from typing import List


from univention.udm import UDM, CreateError, NoObject as UdmNoObject

from .utils import Status, Assignment, get_logger

# todo
logger = get_logger()


class BiloCreateError(CreateError):
    pass


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


class LicenseHandler:
    def __init__(self, lo):  # type: (UDM) -> None
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
        except CreateError as e:
            # todo
            raise BiloCreateError("Error creating license {}: {}".format(license.license_code, e))
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
        filter_s = filter_format("(code=%s)", [license_code])
        return [o for o in self._licenses_mod.search(filter_s)][0]

    def get_meta_data_for_license(self, license):  # type: (License) -> MetaData
        """search for the product of the license. If this there is none
        yet, return an empty object.
        """
        filter_s = filter_format("(&(product_id=%s))", [license.product_id])
        udm_meta_data = [o for o in self._meta_data_mod.search(filter_s)][0]
        if not udm_meta_data:
            return MetaData(product_id=license.product_id)
        else:
            return MetaDataHandler.from_udm_obj(udm_meta_data)

    def _get_assignments(
        self, filter_s, license
    ):  # type: (Optional[str], License) -> List[Assignment]
        """helper function to search in udm layer"""
        udm_obj = self.get_udm_license(license.license_code)
        return [
            self.ah.from_udm_obj(obj)
            for obj in self._assignments_mod.search(base=udm_obj.dn, filter_s=filter_s)
        ]

    def get_all_assignments(self, license):  # type: (License) -> List[UdmObject]
        """search for assignments in leaves of license"""
        return self._get_assignments(filter_s=None, license=license)

    def get_available_licenses(self, license):  # type: (License) -> List[UdmObject]
        filter_s = filter_format("(status=%s)", [str(Status.AVAILABLE)])
        return self._get_assignments(filter_s=filter_s, license=license)

    def get_number_of_available_licenses(self, license):  # type: (License) -> int
        """count the number of assignments with status available"""
        return len(self.get_available_licenses(license))

    def get_number_of_provisioned_and_assigned_licenses(
        self, license
    ):  # type: (License) -> int
        """count the number of assignments with status provisioned or assigned
        todo why both?"""
        filter_s = filter_format(
            "(|(status=%s)(status=%s))",
            [Status.ASSIGNED, Status.PROVISIONED],
        )
        return len(self._get_assignments(filter_s=filter_s, license=license))

    def get_number_of_expired_licenses(self, license):  # type: (License) -> int
        """count the number of assignments with status expired"""
        filter_s = filter_format("(status=%s)", [Status.EXPIRED])
        return len(self._get_assignments(filter_s=filter_s, license=license))

    def get_number_of_licenses(self, license):  # type: (License) -> int
        """count the number of assignments"""
        return len(self.get_all_assignments(license=license))

    def get_time_of_last_assignment(self, license):  # type: (License) -> str
        """Get all assignments of this license and return the date of assignment,
        which was assigned last."""
        assignments = self.get_available_licenses(license)
        last_assignment = max([date.to_datetime(a.time_of_assignment) for a in assignments])
        return date.from_datetime(last_assignment)

    def get_assignments_for_license(self, dn):  # type: (str) -> List[Assignment]
        """Get all assignments which are placed as leaves under the license.
        """
        assignments_from_license = self._assignments_mod.search(base=dn)
        return [
                self.ah.from_udm_obj(assignment)
                for assignment in assignments_from_license
            ]

    # """this seems like another layer & out of scope"""
    #
    # def search_for_license_code(self, udm, filter_s):  # type: (UDM, Optional[str]) -> List[Dict[str, str]]
    #     """the filter_s can be used to filter license attributes, e.g. license codes
    #     todo check
    #     eigentlich nicht teil dieser userstory - wollen wir eine freitext-suche tatsaechlich im mvp?"""
    #     lh = LicenseHandler(udm)
    #     rows = []
    #     for license in self.get_all(filter_s=filter_s):
    #         meta_data = lh.get_meta_data_for_license(license)
    #
    #         rows.append({
    #             "product_id": license.product_id,
    #             "product": meta_data.title,
    #             "publisher": meta_data.publisher,
    #             "license_code": license.license_code,
    #             "type": str(license.license_type),
    #             "time_of_assignment": self.get_time_of_last_assignment(license),
    #             "assigned": lh.get_number_of_provisioned_and_assigned_licenses(license),
    #             "acquired": lh.get_number_of_licenses(license),
    #             "expired": lh.get_number_of_expired_licenses(license),
    #             "available": lh.get_number_of_available_licenses(license)
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
        except CreateError as e:
            print(
                "Error creating meta datum for product id {}: {}".format(
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
        """call meta-data api
        todo out of scope for this """
        pass

    def get_licenses_udm_object_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(&(product_id=%s))", [product_id])
        return [o for o in self._licenses_mod.search(filter_s)]

    def get_assignments_for_meta_data(self, meta_data):  # type: (MetaData) -> List[Assignment]
        """assignments of license with productID"""
        # get licenses objects from udm with the given product id.
        licenses_of_product = self.get_licenses_udm_object_by_product_id(meta_data.product_id)
        assignments = []
        for udm_license in licenses_of_product:
            # get the assignments placed below the licenses.
            assignments.extend(self.lh.get_assignments_for_license(udm_license.dn))

        return assignments

    def get_number_of_available_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status available"""
        return len(
            [
                a
                for a in self.get_assignments_for_meta_data(meta_data)
                if a.status == Status.AVAILABLE
            ]
        )

    def get_number_of_provisioned_and_assigned_licenses(
        self, meta_data
    ):  # type: (MetaData) -> int
        """count the number of assignments with status provisioned or assigned"""
        return len(
            [
                a
                for a in self.get_assignments_for_meta_data(meta_data)
                if a.status in [Status.PROVISIONED, Status.ASSIGNED]
            ]
        )

    def get_number_of_expired_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status expired"""
        return len(
            [
                a
                for a in self.get_assignments_for_meta_data(meta_data)
                if a.status in [Status.EXPIRED]
            ]
        )

    def get_number_of_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments"""
        return len(self.get_assignments_for_meta_data(meta_data))

    def get_meta_data_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(product_id=%s)", [product_id])
        try:
            return [o for o in self._meta_data_mod.search(filter_s)][0]
        except KeyError:
            print("Meta data object with product id {} does not exist!".format(product_id))


class AssignmentHandler:
    # # todo refactor me to BaseHandler
    def __init__(self, lo):  # type: (LoType) -> None
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._users_mod = udm.get("users/user")

    def get_licence_of_assignment(self, dn):  # type: (str) -> UdmObject
        """Return the udm object of the license which is placed
        above the assignment. This is like 'get_parent'. """
        try:
            return self._licenses_mod.get(dn)
        except UdmNoObject:
            # todo
            raise BiloCreateError("There is no license for the assignment {}".format(dn))

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
        # do we need this?
        filter_s = filter_format("(vbmProductId=%s)", [product_id])
        udm_licenses = self._licenses_mod.search(filter_s)
        assignments = []
        for udm_license in udm_licenses:
            filter_s = filter_format("(assignee=%s)", [username])
            udm_assignments = [a for a in self._assignments_mod.search(
                base=udm_license.dn, filter_s=filter_s
            )]
            assignments.extend(udm_assignments)

        return [self.from_udm_obj(a) for a in assignments]

    def check_license_can_be_assigned_to_school_user(self, license_school, ucsschool_school):
        # type: (str, List[str]) -> None
        """todo check is school multi-value in udm?"""
        if license_school not in ucsschool_school:
            raise BiloCreateError(
                "License can't be assigned to user in school {}".format(
                    ucsschool_school
                )
            )

    def get_user_by_username(self, username):  # type: (str) -> UdmObject
        filter_s = filter_format("(uid=%s)", [username])
        users = [u for u in self._users_mod.search(filter_s)]
        if not users:
            # todo
            raise BiloCreateError("Not user with username {}".format(username))
        return users[0]

    def get_license_by_license_code(self, license_code):  # type: (str) -> UdmObject
        filter_s = filter_format("(vbmLicenseCode=%s)", [license_code])
        try:
            license = [o for o in self._licenses_mod.search(filter_s)][0]
            return license
        except KeyError:
            # todo
            raise BiloCreateError("No license with code {} was found!".format(license))

    def create_assignments_for_licence(self, license_code):  # type: (str) -> bool
        """refactor me"""
        udm_license = self.get_license_by_license_code(license_code)
        try:
            assignment = self._assignments_mod.new(superordinate=udm_license.dn)
            assignment.props.status = str(Status.AVAILABLE)
            assignment.save()
        except CreateError as e:
            # todo
            raise BiloCreateError(
                "Error creating assignment for {} {}".format(
                    license_code, e
                )
            )

    def assign_to_license(self, license_code, username):  # type: (str, str) -> None
        udm_license = self.get_license_by_license_code(license_code)
        user = self.get_user_by_username(username)
        self.check_license_can_be_assigned_to_school_user(udm_license.props.vbmLicenseSchool, user.props.school)
        try:
            assignment = self._assignments_mod.new()
            assignment.position = udm_license.dn
            assignment.props.assignee = username
            assignment.props.time_of_assignment = time()  # todo correct format
            assignment.props.status = Status.ASSIGNED
            assignment.save()
        except CreateError as e:
            # todo
            raise BiloCreateError(
                "Error while assigning {} to {}: {}".format(
                    license_code, username, e
                )
            )

    def check_number_licenses_higher_then_assignees(self, licenses, usernames):
        # type: (List[str], List[str]) -> None
        if len(licenses) >= len(usernames):
            raise BiloCreateError(
                "The number of licenses must be >= the users the license codes!"
            )

    def assign_users_to_licenses(
        self, licenses_code, usernames
    ):  # type: (List[str], List[str]) -> None
        """A license can be assigned,
        if the amount of licenses is sufficient to assign it to all users.
        We do not check if the license is valid at this point. The valid licenses,
        are passed from the frontend, right?
        """
        self.check_number_licenses_higher_then_assignees(licenses_code, usernames)
        for username, license in zip(usernames, licenses_code):
            self.assign_to_license(license, username)

    def check_valid_status(self, status):  # type: (St) -> None
        if status not in [s.value for s in Status]:
            raise ValueError("Invalid status {}:".format(status))

    def get_assignments_for_user_under_license(self, license_dn, username):  # type: (str, str)  -> List[UdmObject]
        """Search for license with license id and user with username and change the status
        If a user has more than one license with license code under license_dn,
        we take the first license we can find."""
        filter_s = filter_format("(assignee)", [username])
        return [
            a
            for a in self._assignments_mod.search(
                base=license_dn, filter_s=filter_s
            )
        ]

    def change_license_status(
        self, license_code, username, status
    ):  # type: (str, str, str) -> None
        """AVAILABLE -> ASSIGNED
        ASSIGNED -> AVAILABLE
        AVAILABLE -> EXPIRED (username not needed)
        ASSIGNED -> PROVISIONED
        handled at the license object AVAILABLE -> IGNORED
        username has to be present except if license expired (or valid-date)
        """
        # assignment sollte alles mit unterstrich sein
        # i think this is only needed, if the methods are called directly, i.e. if
        # we do not have umc backend code.
        self.check_valid_status(status)
        udm_license = self.get_license_by_license_code(license_code)
        udm_assignments = self.get_assignments_for_user_under_license(license_dn=udm_license.dn, username=username)
        # ...todo das muessen wir bitte doch noch klaeren, besonders bezueglich volumenlizenzen.
        udm_assignment = udm_assignments[0]
        udm_assignment.props.status = status
        # todo this screams for error handling
        udm_assignment.save()


# if __name__ == '__main__':
#
#     ah = AssignmentHandler(lo)
#     ah.change_license_status("license", "username", "status")
#
#     licenses = ["123af", "schr-blubb"]
#     usernames = ["tobias", "joerg"]
#     ah.assign_users_to_licenses(licenses, usernames)
#
#     ah.assign_to_license("sadf", "ole")
#
#     a1 = ah.get_assignments_for_product_id_for_user(username="tobias", product_id="my-product-id")
#
#     a2 = ah.get_all_assignments_for_user("tobias")
#
#     a3 = ah.get_all()
#
#     # todo nachfragen: wer bastelt das jetzt zusammen, bzw. was muss ich zurueckgeben?
#     # ich brauechte noch eine meta-function, die alles zusammenbastelt.
#     #



# def import_licenses(school, licenses):
#     """dummy function for demonstration purposes"""
#     lh = LicenseHandler(lo)
#     for license in licenses:
#         l = License(license_school=school, **license)  # this is simplefied
#         lh.create(l)
#
#
# if __name__ == '__main__':
#     # dummy code, not tested
#     school = "Demoschool"  # script parameter
#     licenses = [
#         {
#             "lizenzcode": "VHT-7bd46a45-345c-4237-a451-4444736eb011",
#             "product_id": "urn:bilo:medium:A0023#48-85-TZ",
#             "lizenzanzahl": 25,
#             "lizenzgeber": "VHT",
#             "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
#             "nutzungssysteme": "Antolin",
#             "gueltigkeitsbeginn": "15-08-2021",
#             "gueltigkeitsende": "14-08-2022",
#             "gueltigkeitsdauer": "365",
#             "sonderlizenz": "Lehrer",
#         }
#     ]  # data which we get as json
#
#     import_licenses(school, licenses)
#
#
#     license = License()
#     lh = LicenseHandler(lo)
#     lh.create(license)
#
#     lh.get_number_of_licenses(license)
#     lh.get_number_of_expired_licenses(license)
#     lh.get_number_of_provisioned_and_assigned_licenses(license)
#     lh.get_number_of_available_licenses(license)
#     lh.get_all_assignments(license)