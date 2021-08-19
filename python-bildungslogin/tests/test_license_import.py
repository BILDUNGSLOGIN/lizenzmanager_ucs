# -*- coding: utf-8 -*-
import datetime

import attr
import pytest

from univention.bildungslogin.license_import import load_license
from univention.bildungslogin.models import License

test_license_raw = {
    "lizenzcode": "VHT-7bd46a45-345c-4237-a451-4444736eb011",
    "product_id": "urn:bilo:medium:A0023#48-85-TZ",
    "lizenzanzahl": 25,
    "lizenzgeber": "VHT",
    "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
    "nutzungssysteme": "Antolin",
    "gueltigkeitsbeginn": "",
    "gueltigkeitsende": "14-08-2022",
    "gueltigkeitsdauer": "Ein Jahr",
    "sonderlizenz": "Lehrer",
}


test_license = License(
    license_code="VHT-7bd46a45-345c-4237-a451-4444736eb011",
    product_id="urn:bilo:medium:A0023#48-85-TZ",
    license_quantity=25,
    license_provider="VHT",
    purchasing_reference="2014-04-11T03:28:16 -02:00 4572022",
    utilization_systems="Antolin",
    validity_start_date=None,
    validity_end_date=datetime.date(2022, 8, 14),
    validity_duration="Ein Jahr",
    license_special_type="Lehrer",
    ignored_for_display=False,
    delivery_date=datetime.date.today(),
    license_school="test_schule",
)


def test_load_license():
    license = load_license(test_license_raw, "test_schule")
    assert license.__dict__ == attr.asdict(test_license)


@pytest.mark.parametrize(
    "code,expected", [("abc", "VHT-abc"), ("VHT-abc", "VHT-abc"), ("vHt-ABC", "vHt-ABC")]
)
def test_load_license_missing_provider_in_code(code, expected):
    license_raw = {
        "lizenzcode": code,
        "product_id": "urn:bilo:medium:A0023#48-85-TZ",
        "lizenzanzahl": 25,
        "lizenzgeber": "VHT",
        "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
        "nutzungssysteme": "Antolin",
        "gueltigkeitsbeginn": "",
        "gueltigkeitsende": "14-08-2022",
        "gueltigkeitsdauer": "Ein Jahr",
        "sonderlizenz": "Lehrer",
    }
    license = load_license(license_raw, "test_schule")
    assert license.license_code == expected
