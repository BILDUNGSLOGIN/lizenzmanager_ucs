from typing import List
from utils import Assignment
from meta_data import MetaData


class Licence:
    def __init__(
        self,
        licence_code,
        product_id,
        licence_quatity,
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
        # todo
        self.meta_data = MetaData(product_id)
        self.licence_quatity = licence_quatity
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

    @property
    def assignments(self):  # type: () -> List[Assignment]
        """search for assignments in leaves of licence"""
        return []

    def fetch_meta_data_for_licence(self):
        """call meta-data api"""
        pass

    @property
    def meta_data(self):  # type: () -> MetaData
        if not self.meta_data:
            self.fetch_meta_data_for_licence()
        return self.meta_data

    @meta_data.setter
    def meta_data(self, value):
        self.meta_data = value

    @property
    def number_of_available_licences(self):   # type: () -> int
        """count the number of assignments with status available"""
        return 0

    @property
    def number_of_provisioned_and_assigned_licenses(self):  # type: () -> int
        """count the number of assignments with status provisioned or assigned"""
        return 0

    @property
    def number_of_expired_licences(self):  # type: () -> int
        """count the number of assignments with status expired"""
        return 0

    @property
    def number_of_licenses(self):  # type: () -> int
        """count the number of assignments"""
        return 0

    def save(self):
        """save to ldap
        this can be used in the importer"""
