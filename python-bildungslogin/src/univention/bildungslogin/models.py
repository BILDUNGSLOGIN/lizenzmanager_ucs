from typing import Optional

from utils import LicenseType


class License(object):
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
        num_available=None,
    ):  # type: (str, str, int, str, str, str, str, str, str, str, str, str, str, Optional[int]) -> None
        self.license_code = license_code
        self.product_id = product_id
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
        self.num_available = num_available

    @property
    def license_type(self):  # type: () -> str
        if self.license_quantity > 1:
            return LicenseType.VOLUME
        else:
            return LicenseType.SINGLE


class MetaData(object):
    def __init__(
        self,
        product_id,
        title=None,
        description=None,
        author=None,
        publisher=None,
        cover=None,
        cover_small=None,
        modified=None,
    ):  # type: (str, str, str, str, str, str, str, str) -> None
        self.product_id = product_id
        self.title = title
        self.description = description
        self.author = author
        self.publisher = publisher
        self.cover = cover
        self.cover_small = cover_small
        self.modified = modified
