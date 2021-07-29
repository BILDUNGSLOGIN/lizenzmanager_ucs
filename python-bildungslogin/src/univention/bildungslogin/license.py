# # WIP, not tested (!)
#
#
# from ldap.filter import filter_format
# from typing import List, Optional, Dict
# from univention.admin.syntax import date
# from univention.udm import UDM
# from univention.udm.exceptions import CreateError
#
# from utils import Assignment, Status
# from meta_datum import MetaDataHandler
#
# from assignment_handler import AssignmentHandler
# from models import License, MetaData
#
# try:
#     # todo
#     from ucsschool.lib.models.base import LoType, UdmObject
# except ImportError:
#     pass
#
#
# class LicenseHandler:
#     def __init__(self, lo):  # type: (LoType) -> None
#         self.lo = lo
#         udm = UDM(lo).version(1)
#         self._licenses_mod = udm.get("vbm/license")
#         self._assignments_mod = udm.get("vbm/assignment")
#         self._meta_data_mod = udm.get("vbm/metadatum")
#         self.ah = AssignmentHandler(self.lo)
#
#     def create(self, license):  # type: (License) -> None
#         """Create a license and unassigned assignments as leaves."""
#         try:
#             udm_obj = self._licenses_mod.new()
#             udm_obj.props.code = license.license_code
#             udm_obj.props.product_id = license.product_id
#             udm_obj.props.quantity = license.license_quantity
#             udm_obj.props.provider = license.license_provider
#             udm_obj.props.utilization_systems = license.utilization_systems
#             udm_obj.props.validity_start_date = license.validity_start_date
#             udm_obj.props.validity_end_date = license.validity_end_date
#             udm_obj.props.validity_duration = license.validity_duration
#             udm_obj.props.delivery_date = license.delivery_date
#             udm_obj.props.school = license.license_school
#             udm_obj.props.ignored = license.ignored_for_display
#             udm_obj.props.special_type = license.license_special_type
#             udm_obj.props.purchasing_reference = license.purchasing_reference
#             udm_obj.save()
#         except CreateError as e:
#             print("Error creating license {}: {}".format(license.license_code, e))
#         for i in range(license.license_quantity):
#             self.ah.create_assignments_for_licence(license_code=license.license_code)
#
#     @staticmethod
#     def from_udm_obj(udm_obj):  # type: (UdmObject) -> License
#         return License(
#             license_code=udm_obj.props.code,
#             product_id=udm_obj.props.product_id,
#             license_quantity=udm_obj.props.quantity,
#             license_provider=udm_obj.props.provider,
#             utilization_systems=udm_obj.props.utilization_systems,
#             validity_start_date=udm_obj.props.validity_start_date,
#             validity_end_date=udm_obj.props.validity_end_date,
#             validity_duration=udm_obj.props.validity_duration,
#             delivery_date=udm_obj.props.delivery_date,
#             license_school=udm_obj.props.school,
#             ignored_for_display=udm_obj.props.ignored,
#             license_special_type=udm_obj.props.special_type,
#             purchasing_reference=udm_obj.props.purchasing_reference,
#         )
#
#     def from_dn(self, dn):  # type: (str) -> License
#         udm_license = self._licenses_mod.get(dn)
#         return self.from_udm_obj(udm_license)
#
#     def get_all(self, filter_s=None):  # type: (Optional[str]) -> List[License]
#         """get all licenses"""
#         udm_licenses = self._licenses_mod.search(filter_s=filter_s)
#         return [LicenseHandler.from_udm_obj(a) for a in udm_licenses]
#
#     def get_udm_license(self, license_code):  # type: (str) -> UdmObject
#         filter_s = filter_format("(code=%s)", [license_code])
#         return [o for o in self._licenses_mod.search(filter_s)][0]
#
#     def get_meta_data_for_license(self, license):  # type: (License) -> MetaData
#         """search for the product of the license. If this there is none
#         yet, return an empty object.
#         """
#         filter_s = filter_format("(&(product_id=%s))", [license.product_id])
#         udm_meta_data = [o for o in self._meta_data_mod.search(filter_s)][0]
#         if not udm_meta_data:
#             return MetaData(product_id=license.product_id)
#         else:
#             return MetaDataHandler.from_udm_obj(udm_meta_data)
#
#     def _get_assignments(
#         self, filter_s, license
#     ):  # type: (Optional[str], License) -> List[Assignment]
#         """helper function to search in udm layer"""
#         udm_obj = self.get_udm_license(license.license_code)
#         return [
#             self.ah.from_udm_obj(obj)
#             for obj in self._assignments_mod.search(base=udm_obj.dn, filter_s=filter_s)
#         ]
#
#     def get_all_assignments(self, license):  # type: (License) -> List[UdmObject]
#         """search for assignments in leaves of license"""
#         return self._get_assignments(filter_s=None, license=license)
#
#     def get_available_licenses(self, license):  # type: (License) -> List[UdmObject]
#         filter_s = filter_format("(status=%s)", [Status.AVAILABLE])
#         return self._get_assignments(filter_s=filter_s, license=license)
#
#     def get_number_of_available_licenses(self, license):  # type: (License) -> int
#         """count the number of assignments with status available"""
#         return len(self.get_available_licenses(license))
#
#     def get_number_of_provisioned_and_assigned_licenses(
#         self, license
#     ):  # type: (License) -> int
#         """count the number of assignments with status provisioned or assigned
#         todo why both?"""
#         filter_s = filter_format(
#             "(|(status=%s)(status=%s))",
#             [Status.ASSIGNED, Status.PROVISIONED],
#         )
#         return len(self._get_assignments(filter_s=filter_s, license=license))
#
#     def get_number_of_expired_licenses(self, license):  # type: (License) -> int
#         """count the number of assignments with status expired"""
#         filter_s = filter_format("(status=%s)", [Status.EXPIRED])
#         return len(self._get_assignments(filter_s=filter_s, license=license))
#
#     def get_number_of_licenses(self, license):  # type: (License) -> int
#         """count the number of assignments"""
#         return len(self.get_all_assignments(license=license))
#
#     def get_time_of_last_assignment(self, license):  # type: (License) -> str
#         """Get all assignments of this license and return the date of assignment,
#         which was assigned last."""
#         assignments = self.get_available_licenses(license)
#         last_assignment = max([date.to_datetime(a.time_of_assignment) for a in assignments])
#         return date.from_datetime(last_assignment)
#
#     def get_assignments_for_license(self, dn):  # type: (str) -> List[Assignment]
#         """Get all assignments which are placed as leaves under the license.
#         """
#         assignments_from_license = self._assignments_mod.search(base=dn)
#         return [
#                 self.ah.from_udm_obj(assignment)
#                 for assignment in assignments_from_license
#             ]
#
#     """this seems like another layer"""
#
#     def search_for_license_code(self, lo, filter_s):  # type: (LoType, Optional[str]) -> List[Dict[str, str]]
#         """the filter_s can be used to filter license attributes, e.g. license codes
#         todo check """
#         lh = LicenseHandler(lo)
#         rows = []
#         for license in self.get_all(filter_s=filter_s):
#             meta_data = lh.get_meta_data_for_license(license)
#             rows.append({
#                 "product_id": license.product_id,
#                 "product": meta_data.title,
#                 "publisher": meta_data.publisher,
#                 "license_code": license.license_code,
#                 "type": str(license.license_type),
#                 "time_of_assignment": self.get_time_of_last_assignment(license),
#                 "assigned": lh.get_number_of_provisioned_and_assigned_licenses(license),
#                 "acquired": lh.get_number_of_licenses(license),
#                 "expired": lh.get_number_of_expired_licenses(license),
#                 "available": lh.get_number_of_available_licenses(license)
#             })
#         return rows
#
# #
# # def import_licenses(school, licenses):
# #     """dummy function for demonstration purposes"""
# #     lh = LicenseHandler(lo)
# #     for license in licenses:
# #         l = License(license_school=school, **license)  # this is simplefied
# #         lh.create(l)
# #
# #
# # if __name__ == '__main__':
# #     # dummy code, not tested
# #     school = "Demoschool"  # script parameter
# #     licenses = [
# #         {
# #             "lizenzcode": "VHT-7bd46a45-345c-4237-a451-4444736eb011",
# #             "product_id": "urn:bilo:medium:A0023#48-85-TZ",
# #             "lizenzanzahl": 25,
# #             "lizenzgeber": "VHT",
# #             "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
# #             "nutzungssysteme": "Antolin",
# #             "gueltigkeitsbeginn": "15-08-2021",
# #             "gueltigkeitsende": "14-08-2022",
# #             "gueltigkeitsdauer": "365",
# #             "sonderlizenz": "Lehrer",
# #         }
# #     ]  # data which we get as json
# #
# #     import_licenses(school, licenses)
# #
# #
# #     license = License()
# #     lh = LicenseHandler(lo)
# #     lh.create(license)
# #
# #     lh.get_number_of_licenses(license)
# #     lh.get_number_of_expired_licenses(license)
# #     lh.get_number_of_provisioned_and_assigned_licenses(license)
# #     lh.get_number_of_available_licenses(license)
# #     lh.get_all_assignments(license)