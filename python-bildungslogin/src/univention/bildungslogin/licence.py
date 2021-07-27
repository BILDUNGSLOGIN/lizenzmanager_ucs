from univention.management.console.ldap import get_machine_connection

from ldap.filter import filter_format
from typing import List
from univention.udm import UDM

from utils import Assignment, Status
from meta_data import MetaData


class Licence:
    def __init__(
        self,
        licence_code,
        product_id,
        licence_quantity,
        licence_provider,
        purchasing_date,
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
        self.purchasing_date = purchasing_date
        self.utilization_systems = utilization_systems
        self.validity_start_date = validity_start_date
        self.validity_end_date = validity_end_date
        self.validity_duration = validity_duration
        self.licence_special_type = licence_special_type
        self.ignored_for_display = ignored_for_display
        self.delivery_date = delivery_date
        self.licence_school = licence_school

        # das ist eher unguenstig.
        lo, po = get_machine_connection(write=True)
        udm = UDM(lo).version(1)
        self._licences_mod = udm.get("vbm/licences")
        self._assignments_mod = udm.get("vbm/assignments")
        self.udm_obj = self._get_udm_object()

    def _get_udm_object(self):
        filter_s = filter_format("(vbmLicenceCode=%s)", [self.licence_code])
        return [o for o in self._licences_mod.search(filter_s)][0]

    def _assignments(self, filter_s):
        return [o for o in self._assignments_mod.search(base=self.udm_obj.dn, filter_s=filter_s)]

    @property
    def assignments(self):  # type: () -> List[Assignment]
        """search for assignments in leaves of licence"""
        return self._assignments(filter_s=None)

    @property
    def number_of_available_licences(self):   # type: () -> int
        """count the number of assignments with status available"""
        filter_s = filter_format("(vbmAssignmentStatus=%s)", [Status.AVAILABLE])
        return len(self._assignments(filter_s=filter_s))

    @property
    def number_of_provisioned_and_assigned_licenses(self):  # type: () -> int
        """count the number of assignments with status provisioned or assigned"""
        filter_s = filter_format("(|(vbmAssignmentStatus=%s)(vbmAssignmentStatus=%s))", [Status.ASSIGNED, Status.PROVISIONED])
        return len(self._assignments(filter_s=filter_s))

    @property
    def number_of_expired_licences(self):  # type: () -> int
        """count the number of assignments with status expired"""
        filter_s = filter_format("(vbmAssignmentStatus=%s)", [Status.EXPIRED])
        return len(self._assignments(filter_s=filter_s))

    @property
    def number_of_licenses(self):  # type: () -> int
        """count the number of assignments"""
        return len(self.assignments)

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

    def save(self):
        """save to ldap
        this can be used in the importer"""
        self.udm_obj.save()

    def create(self):
        """don't we need this, too?"""
        pass
