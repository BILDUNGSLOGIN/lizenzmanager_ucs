# # WIP, not tests (!)
#
#
# from time import time
#
# from ldap.filter import filter_format
# from typing import List
#
# try:
#     # todo
#     from ucsschool.lib.models.base import LoType, UdmObject
# except ImportError:
#     pass
#
# from univention.udm import UDM, CreateError, NoObject as UdmNoObject
#
# from .utils import Status, Assignment, get_logger
#
# # todo
# logger = get_logger()
#
#
# class AssignmentHandler:
#     def __init__(self, lo):  # type: (LoType) -> None
#         self.lo = lo
#         udm = UDM(lo).version(1)
#         self._licenses_mod = udm.get("vbm/license")
#         self._assignments_mod = udm.get("vbm/assignment")
#         self._users_mod = udm.get("users/user")
#
#     def get_licence_of_assignment(self, dn):  # type: (str) -> UdmObject
#         """Return the udm object of the license which is placed
#         above the assignment. This is like 'get_parent'. """
#         try:
#             return self._licenses_mod.get(dn)
#         except UdmNoObject:
#             # todo
#             print("There is no license for the assignment {}".format(dn))
#
#     def from_udm_obj(self, udm_obj):  # type: (UdmObject) -> Assignment
#         """
#         Creates an Assignment object of an udm_obj. We do not save the license
#         code directly on the assignments, so we have to ask the parent first.
#
#         :param udm_obj: of assignment
#         :return: assignment object
#         """
#         udm_license = self.get_licence_of_assignment(udm_obj.position)
#         return Assignment(
#             username=udm_obj.props.assignee,
#             license=udm_license.props.vbmLicenseCode,
#             time_of_assignment=udm_obj.props.time_of_assignment,
#             status=udm_obj.props.status,
#         )
#
#     def from_dn(self, dn):  # type: (str) -> Assignment
#         udm_license = self._assignments_mod.get(dn)
#         return self.from_udm_obj(udm_license)
#
#     def get_all(self, filter_s=None):  # type: (str) -> List[Assignment]
#         udm_assignments = self._assignments_mod.search(filter_s=filter_s)
#         return [self.from_udm_obj(a) for a in udm_assignments]
#
#     def get_all_assignments_for_user(self, username):  # type: (str) -> List[Assignment]
#         filter_s = filter_format("(assignee=%s)", [username])
#         udm_assignments = self._assignments_mod.search(filter_s)
#         return [self.from_udm_obj(a) for a in udm_assignments]
#
#     def get_assignments_for_product_id_for_user(
#         self, username, product_id
#     ):  # type: (str, str) -> List[Assignment]
#         # do we need this?
#         filter_s = filter_format("(vbmProductId=%s)", [product_id])
#         udm_licenses = self._licenses_mod.search(filter_s)
#         assignments = []
#         for udm_license in udm_licenses:
#             filter_s = filter_format("(assignee=%s)", [username])
#             udm_assignments = [a for a in self._assignments_mod.search(
#                 base=udm_license.dn, filter_s=filter_s
#             )]
#             assignments.extend(udm_assignments)
#
#         return [self.from_udm_obj(a) for a in assignments]
#
#     def check_license_can_be_assigned_to_school_user(self, license_school, ucsschool_school):
#         # type: (str, List[str]) -> None
#         """todo check is school multi-value in udm?"""
#         if license_school not in ucsschool_school:
#             raise ValueError(
#                 "License can't be assigned to user in school {}".format(
#                     ucsschool_school
#                 )
#             )
#
#     def get_user_by_username(self, username):  # type: (str) -> UdmObject
#         filter_s = filter_format("(uid=%s)", [username])
#         users = [u for u in self._users_mod.search(filter_s)]
#         if not users:
#             raise ValueError("Not user with username {}".format(username))
#         return users[0]
#
#     def get_license_by_license_code(self, license_code):  # type: (str) -> UdmObject
#         filter_s = filter_format("(vbmLicenseCode)", [license_code])
#         try:
#             license = [o for o in self._licenses_mod.search(filter_s)][0]
#             return license
#         except KeyError:
#             # todo
#             print("No license with code {} was found!".format(license))
#
#     def create_assignments_for_licence(self, license_code):  # type: (str) -> bool
#         """refactor me"""
#         udm_license = self.get_license_by_license_code(license_code)
#         try:
#             assignment = self._assignments_mod.new()
#             assignment.position = udm_license.dn
#             assignment.props.status = Status.AVAILABLE
#             assignment.save()
#         except CreateError as e:
#             # todo
#             print(
#                 "Error creating assignment for {} {}".format(
#                     license_code, e
#                 )
#             )
#
#     def assign_to_license(self, license_code, username):  # type: (str, str) -> bool
#         udm_license = self.get_license_by_license_code(license_code)
#         user = self.get_user_by_username(username)
#         self.check_license_can_be_assigned_to_school_user(udm_license.props.vbmLicenseSchool, user.props.school)
#         try:
#             assignment = self._assignments_mod.new()
#             assignment.position = udm_license.dn
#             assignment.props.assignee = username
#             assignment.props.time_of_assignment = time()  # todo correct format
#             assignment.props.status = Status.ASSIGNED
#             assignment.save()
#         except CreateError as e:
#             # todo
#             print(
#                 "Error while assigning {} to {}: {}".format(
#                     license_code, username, e
#                 )
#             )
#             return False
#         return True
#
#     def check_number_licenses_higher_then_assignees(self, licenses, usernames):
#         # type: (List[str], List[str]) -> None
#         if len(licenses) >= len(usernames):
#             raise ValueError(
#                 "The number of licenses must be >= the users the license codes!"
#             )
#
#     def assign_users_to_licenses(
#         self, licenses_code, usernames
#     ):  # type: (List[str], List[str]) -> None
#         """A license can be assigned,
#         if the amount of licenses is sufficient to assign it to all users.
#         We do not check if the license is valid at this point. The valid licenses,
#         are passed from the frontend, right?
#         """
#         self.check_number_licenses_higher_then_assignees(licenses_code, usernames)
#         for username, license in zip(usernames, licenses_code):
#             self.assign_to_license(license, username)
#
#     def check_valid_status(self, status):  # type: (St) -> None
#         if status not in [s.value for s in Status]:
#             raise ValueError("Invalid status {}:".format(status))
#
#     def get_assignments_for_user_under_license(self, license_dn, username):  # type: (str, str)  -> List[UdmObject]
#         """Search for license with license id and user with username and change the status
#         If a user has more than one license with license code under license_dn,
#         we take the first license we can find."""
#         filter_s = filter_format("(assignee)", [username])
#         return [
#             a
#             for a in self._assignments_mod.search(
#                 base=license_dn, filter_s=filter_s
#             )
#         ]
#
#     def change_license_status(
#         self, license_code, username, status
#     ):  # type: (str, str, str) -> None
#         """AVAILABLE -> ASSIGNED
#         ASSIGNED -> AVAILABLE
#         AVAILABLE -> EXPIRED (username not needed)
#         ASSIGNED -> PROVISIONED
#         handled at the license object AVAILABLE -> IGNORED
#         username has to be present except if license expired (or valid-date)
#         """
#         # assignment sollte alles mit unterstrich sein
#         # i think this is only needed, if the methods are called directly, i.e. if
#         # we do not have umc backend code.
#         self.check_valid_status(status)
#         udm_license = self.get_license_by_license_code(license_code)
#         udm_assignments = self.get_assignments_for_user_under_license(license_dn=udm_license.dn, username=username)
#         # ...todo das muessen wir bitte doch noch klaeren, besonders bezueglich volumenlizenzen.
#         udm_assignment = udm_assignments[0]
#         udm_assignment.props.status = status
#         # todo this screams for error handling
#         udm_assignment.save()
#
#
# # if __name__ == '__main__':
# #
# #     ah = AssignmentHandler(lo)
# #     ah.change_license_status("license", "username", "status")
# #
# #     licenses = ["123af", "schr-blubb"]
# #     usernames = ["tobias", "joerg"]
# #     ah.assign_users_to_licenses(licenses, usernames)
# #
# #     ah.assign_to_license("sadf", "ole")
# #
# #     a1 = ah.get_assignments_for_product_id_for_user(username="tobias", product_id="my-product-id")
# #
# #     a2 = ah.get_all_assignments_for_user("tobias")
# #
# #     a3 = ah.get_all()
# #
# #     # todo nachfragen: wer bastelt das jetzt zusammen, bzw. was muss ich zurueckgeben?
# #     # ich brauechte noch eine meta-function, die alles zusammenbastelt.
# #     #