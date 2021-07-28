# WIP, not tests (!)

import hashlib

from ldap.filter import filter_format
from typing import List, Optional
from univention.udm import UDM
from univention.udm.exceptions import CreateError

from utils import Assignment, Status
from meta_data import MetaData
from ucsschool.lib.models.base import UdmObject


class Licence:
    def __init__(
        self,
        licence_code,
        product_id,
        licence_quantity,
        licence_provider,
        purchasing_reference,
        utilization_systems,
        validity_start_date,
        validity_end_date,
        validity_duration,
        licence_special_type,
        ignored_for_display,
        delivery_date,
        licence_school,
    ):  # type: (str, str, str, str, str, str, str, str, str, str, bool, str, str) -> None
        self.licence_code = licence_code
        self.meta_data = MetaData(product_id)
        self.licence_quantity = licence_quantity
        self.licence_provider = licence_provider
        self.purchasing_reference = purchasing_reference
        self.utilization_systems = utilization_systems
        self.validity_start_date = validity_start_date
        self.validity_end_date = validity_end_date
        self.validity_duration = validity_duration
        self.licence_special_type = licence_special_type
        self.ignored_for_display = ignored_for_display
        self.delivery_date = delivery_date
        self.licence_school = licence_school


class LicenceHandler:
    def __init__(self, lo):
        self.lo = lo
        udm = UDM(lo).version(1)
        self._licences_mod = udm.get("vbm/licences")
        self._assignments_mod = udm.get("vbm/assignments")

    def get_all(self, filter_s=None):  # type: (Optional[str]) -> List[Licence]
        licences = self._licences_mod.search(filter_s=filter_s)
        return [LicenceHandler.from_udm_obj(a) for a in licences]

    @staticmethod
    def from_udm_obj(udm_obj):  # type: (UdmObject) -> Licence
        return Licence(
            licence_code=udm_obj.props.vbmLicenceCode,
            product_id=udm_obj.props.vbmProductId,
            licence_quantity=udm_obj.props.vbmLicenceQuantity,
            licence_provider=udm_obj.props.vbmLicenceProvider,
            utilization_systems=udm_obj.props.vbmUtilizationSystems,
            validity_start_date=udm_obj.props.vbmValidityStartDate,
            validity_end_date=udm_obj.props.vbmValidityEndDate,
            validity_duration=udm_obj.props.vbmValidityDuration,
            delivery_date=udm_obj.props.vbmDeliveryDate,
            licence_school=udm_obj.props.vbmLicenceSchool,
            ignored_for_display=udm_obj.props.vbmIgnoredForDisplay,
            licence_special_type=udm_obj.props.vbmLicenceSpecialType,
            purchasing_reference=udm_obj.props.vbmPurchasingReference,
        )

    def from_dn(self, dn):  # type: (str) -> Licence
        udm_licence = self._licences_mod.get(dn)
        return self.from_udm_obj(udm_licence)

    def _get_udm_object(self, licence_code):
        filter_s = filter_format("(vbmlicenceCode=%s)", [licence_code])
        return [o for o in self._licences_mod.search(filter_s)][0]

    def _get_assignments(
        self, filter_s, licence
    ):  # type: (Optional[str], Licence) -> List[Assignment]
        """helper function to search in udm layer"""
        udm_obj = self._get_udm_object(licence.licence_code)
        return [
            Assignment.from_udm_obj(obj)
            for obj in self._assignments_mod.search(base=udm_obj.dn, filter_s=filter_s)
        ]

    def all_assignments(self, licence):  # type: (Licence) -> List[UdmObject]
        """search for assignments in leaves of licence"""
        return self._get_assignments(filter_s=None, licence=licence)

    def number_of_available_licences(self, licence):  # type: (Licence) -> int
        """count the number of assignments with status available"""
        filter_s = filter_format("(vbmAssignmentStatus=%s)", [Status.AVAILABLE])
        return len(self._get_assignments(filter_s=filter_s, licence=licence))

    def number_of_provisioned_and_assigned_licences(
        self, licence
    ):  # type: (Licence) -> int
        """count the number of assignments with status provisioned or assigned"""
        filter_s = filter_format(
            "(|(vbmAssignmentStatus=%s)(vbmAssignmentStatus=%s))",
            [Status.ASSIGNED, Status.PROVISIONED],
        )
        return len(self._get_assignments(filter_s=filter_s, licence=licence))

    def number_of_expired_licences(self, licence):  # type: (Licence) -> int
        """count the number of assignments with status expired"""
        filter_s = filter_format("(vbmAssignmentStatus=%s)", [Status.EXPIRED])
        return len(self._get_assignments(filter_s=filter_s, licence=licence))

    def number_of_licences(self, licence):  # type: (Licence) -> int
        """count the number of assignments"""
        return len(self.all_assignments(licence=licence))

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

    def create(self, licence):  # type: (Licence) -> None
        try:
            udm_obj = self._licences_mod.new()
            udm_obj.props.cn = hashlib.sha256(licence.licence_code).hexdigest()
            udm_obj.props.vbmLicenceCode = licence.licence_code
            udm_obj.props.vbmProductId = licence.meta_data.product_id
            udm_obj.props.vbmLicenceQuantity = licence.licence_quantity
            udm_obj.props.vbmLicenceProvider = licence.licence_provider
            udm_obj.props.vbmUtilizationSystems = licence.utilization_systems
            udm_obj.props.vbmValidityStartDate = licence.validity_start_date
            udm_obj.props.vbmValidityEndDate = licence.validity_end_date
            udm_obj.props.vbmValidityDuration = licence.validity_duration
            udm_obj.props.vbmDeliveryDate = licence.delivery_date
            udm_obj.props.vbmLicenceSchool = licence.licence_school
            udm_obj.props.vbmIgnoredForDisplay = licence.ignored_for_display
            udm_obj.props.vbmLicenceSpecialType = licence.licence_special_type
            udm_obj.props.vbmPurchasingReference = licence.purchasing_reference
            udm_obj.save()
        except CreateError as e:
            print("Error creating licence {}: {}".format(licence.licence_code, e))
