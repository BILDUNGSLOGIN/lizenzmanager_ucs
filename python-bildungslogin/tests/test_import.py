import json
import time
import pytest

from univention.bildungslogin.license_import import load_license
from univention.bildungslogin.license import License


test_license_raw = {
    "lizenzcode": "VHT-7bd46a45-345c-4237-a451-4444736eb011",
    "product_id": "urn:bilo:medium:A0023#48-85-TZ",
    "lizenzanzahl": 25,
    "lizenzgeber": "VHT",
    "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
    "nutzungssysteme": "Antolin",
    "gueltigkeitsbeginn": "15-08-2021",
    "gueltigkeitsende": "14-08-2022",
    "gueltigkeitsdauer": "365",
    "sonderlizenz": "Lehrer",
}


test_license = License(
    license_code="VHT-7bd46a45-345c-4237-a451-4444736eb011",
    product_id="urn:bilo:medium:A0023#48-85-TZ",
    license_quantity=25,
    license_provider="VHT",
    purchasing_date="2014-04-11T03:28:16 -02:00 4572022",
    utilization_systems="Antolin",
    validity_start_date="15-08-2021",
    validity_end_date="14-08-2022",
    validity_duration="365",
    license_special_type="Lehrer",
    ignored_for_display=False,
    delivery_date=int(time.time()),
    license_school='test_schule',
)


@pytest.fixture(scope='module')
def license_file(tmpdir_factory):
    fn = tmpdir_factory.mktemp("data").join('license.json')
    with open(str(fn), 'w') as license_fd:
        json.dump([test_license_raw], license_fd)
    return fn


def test_load_license():
    license = load_license(test_license_raw, 'test_schule')
    assert license.delivery_date >= test_license.delivery_date and license.delivery_date <= int(time.time())
    license_dict = license.__dict__
    test_license_dict = test_license.__dict__
    del license_dict["delivery_date"]
    del test_license_dict["delivery_date"]
    assert license_dict == test_license_dict
