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
    licence_provider="VHT",
    purchasing_date="2014-04-11T03:28:16 -02:00 4572022",
    utilization_systems="Antolin",
    validity_start_date="15-08-2021",
    validity_end_date="14-08-2022",
    validity_duration="365",
    licence_special_type="Lehrer",
    ignored_for_display=False,
    delivery_date=int(time.time()),
    licence_school='test_schule',
)


@pytest.fixture(scope='module')
def licence_file(tmpdir_factory):
    fn = tmpdir_factory.mktemp("data").join('licence.json')
    with open(str(fn), 'w') as licence_fd:
        json.dump([test_licence_raw], licence_fd)
    return fn


def test_load_licence():
    licence = load_licence(test_licence_raw, 'test_schule')
    assert licence.delivery_date >= test_licence.delivery_date and licence.delivery_date <= int(time.time())
    licence_dict = licence.__dict__
    test_licence_dict = test_licence.__dict__
    del licence_dict["delivery_date"]
    del test_licence_dict["delivery_date"]
    assert licence_dict == test_licence_dict
