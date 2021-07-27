# WIP, not tests (!)

import hashlib

from ldap.filter import filter_format
from typing import List, Optional
from univention.udm import UDM
from univention.udm.exceptions import CreateError

from utils import Assignment, Status
from meta_data import MetaData
from ucsschool.lib.models.base import UdmObject


class License:
    def __init__(
        self,
        license_code,
        product_id,
        license_quantity,
        license_provider,
        purchasing_reference,
        utilization_systems,
        validity_start_date,
        validity_end_date,
        validity_duration,
        license_special_type,
        ignored_for_display,
        delivery_date,
        license_school,
    ):  # type: (str, str, str, str, str, str, str, str, str, str, bool, str, str) -> None
        self.license_code = license_code
        self.meta_data = MetaData(product_id)
        self.license_quantity = license_quantity
        self.license_provider = license_provider
        self.purchasing_reference = purchasing_reference
        self.utilization_systems = utilization_systems
        self.validity_start_date = validity_start_date
        self.validity_end_date = validity_end_date
        self.validity_duration = validity_duration
        self.license_special_type = license_special_type
        self.ignored_for_display = ignored_for_display
        self.delivery_date = delivery_date
        self.license_school = license_school


class LicenseHandler:
    def __init__(self, lo):
        self.lo = lo
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/licenses")
        self._assignments_mod = udm.get("vbm/assignments")

    def get_all(self, filter_s=None):  # type: (Optional[str]) -> List[License]
        licenses = self._licenses_mod.search(filter_s=filter_s)
        return [LicenseHandler.from_udm_obj(a) for a in licenses]

    @staticmethod
    def from_udm_obj(udm_obj):  # type: (UdmObject) -> License
        return License(
            license_code=udm_obj.props.vbmLicenseCode,
            product_id=udm_obj.props.vbmProductId,
            license_quantity=udm_obj.props.vbmLicenseQuantity,
            license_provider=udm_obj.props.vbmLicenseProvider,
            utilization_systems=udm_obj.props.vbmUtilizationSystems,
            validity_start_date=udm_obj.props.vbmValidityStartDate,
            validity_end_date=udm_obj.props.vbmValidityEndDate,
            validity_duration=udm_obj.props.vbmValidityDuration,
            delivery_date=udm_obj.props.vbmDeliveryDate,
            license_school=udm_obj.props.vbmLicenseSchool,
            ignored_for_display=udm_obj.props.vbmIgnoredForDisplay,
            license_special_type=udm_obj.props.vbmLicenseSpecialType,
            purchasing_reference=udm_obj.props.vbmPurchasingReference,
        )

    def from_dn(self, dn):  # type: (str) -> License
        udm_license = self._licenses_mod.get(dn)
        return self.from_udm_obj(udm_license)

    def _get_udm_object(self, license_code):
        filter_s = filter_format("(vbmlicenseCode=%s)", [license_code])
        return [o for o in self._licenses_mod.search(filter_s)][0]

    def _get_assignments(
        self, filter_s, license
    ):  # type: (Optional[str], License) -> List[Assignment]
        """helper function to search in udm layer"""
        udm_obj = self._get_udm_object(license.license_code)
        return [
            Assignment.from_udm_obj(obj)
            for obj in self._assignments_mod.search(base=udm_obj.dn, filter_s=filter_s)
        ]

    def all_assignments(self, license):  # type: (License) -> List[UdmObject]
        """search for assignments in leaves of license"""
        return self._get_assignments(filter_s=None, license=license)

    def number_of_available_licenses(self, license):  # type: (License) -> int
        """count the number of assignments with status available"""
        filter_s = filter_format("(vbmAssignmentStatus=%s)", [Status.AVAILABLE])
        return len(self._get_assignments(filter_s=filter_s, license=license))

    def number_of_provisioned_and_assigned_licenses(
        self, license
    ):  # type: (License) -> int
        """count the number of assignments with status provisioned or assigned"""
        filter_s = filter_format(
            "(|(vbmAssignmentStatus=%s)(vbmAssignmentStatus=%s))",
            [Status.ASSIGNED, Status.PROVISIONED],
        )
        return len(self._get_assignments(filter_s=filter_s, license=license))

    def number_of_expired_licenses(self, license):  # type: (License) -> int
        """count the number of assignments with status expired"""
        filter_s = filter_format("(vbmAssignmentStatus=%s)", [Status.EXPIRED])
        return len(self._get_assignments(filter_s=filter_s, license=license))

    def number_of_licenses(self, license):  # type: (License) -> int
        """count the number of assignments"""
        return len(self.all_assignments(license=license))

    @property
    def meta_data(self):  # type: () -> MetaData
        """we expect at least the title to be present,
        otherwise we call the meta-data api"""
        if not self.meta_data.title:
            self.meta_data.fetch_meta_data()
        return self.meta_data

    @meta_data.setter
    def meta_data(self, value):
        self.meta_data = value

    def create(self, license):  # type: (License) -> None
        try:
            udm_obj = self._licenses_mod.new()
            udm_obj.props.cn = hashlib.sha256(license.license_code).hexdigest()
            udm_obj.props.vbmLicenseCode = license.license_code
            udm_obj.props.vbmProductId = license.meta_data.product_id
            udm_obj.props.vbmLicenseQuantity = license.license_quantity
            udm_obj.props.vbmLicenseProvider = license.license_provider
            udm_obj.props.vbmUtilizationSystems = license.utilization_systems
            udm_obj.props.vbmValidityStartDate = license.validity_start_date
            udm_obj.props.vbmValidityEndDate = license.validity_end_date
            udm_obj.props.vbmValidityDuration = license.validity_duration
            udm_obj.props.vbmDeliveryDate = license.delivery_date
            udm_obj.props.vbmLicenseSchool = license.license_school
            udm_obj.props.vbmIgnoredForDisplay = license.ignored_for_display
            udm_obj.props.vbmLicenseSpecialType = license.license_special_type
            udm_obj.props.vbmPurchasingReference = license.purchasing_reference
            udm_obj.save()
        except CreateError as e:
            print("Error creating license {}: {}".format(license.license_code, e))
