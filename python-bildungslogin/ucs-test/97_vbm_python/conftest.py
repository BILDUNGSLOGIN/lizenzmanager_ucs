import uuid

import pytest
import ldap
import random
import json
from univention.bildungslogin.models import License, MetaData
from univention.bildungslogin.utils import parse_raw_license_date
from univention.bildungslogin.handler import (
    LicenseHandler,
    MetaDataHandler,
    AssignmentHandler,
)
from univention.admin.uldap import getAdminConnection

import datetime

from univention.testing.ucr import UCSTestConfigRegistry
import univention.testing.strings as uts


def iso_format_date(my_date):
    return my_date.isoformat().split("T")[0]


def get_random_license():
    today = datetime.datetime.now()
    start = today + datetime.timedelta(days=random.randint(0, 365))
    duration = random.randint(1, 365)
    end = start + datetime.timedelta(duration)
    return License(
        license_code="VHT-{}".format(str(uuid.uuid4())),
        product_id="urn:bilo:medium:A0023#48-85-TZ",
        license_quantity=random.randint(10, 50),
        license_provider="VHT",
        purchasing_reference="2014-04-11T03:28:16 -02:00 4572022",
        utilization_systems="Antolin",
        validity_start_date=iso_format_date(start),
        validity_end_date=iso_format_date(end),
        validity_duration="{}".format(duration),
        license_special_type=random.choice(["Lehrer", ""]),
        ignored_for_display="0",
        delivery_date=today.isoformat().split("T")[0],
        license_school="test_schule",  # todo
    )


def get_expired_license():
    """"the end_date + duration < today
    """
    # todo refactor me
    today = datetime.datetime.now()
    duration = random.randint(1, 365)
    start = today - datetime.timedelta(duration)
    end = today - datetime.timedelta(1)
    return License(
        license_code="VHT-{}".format(str(uuid.uuid4())),
        product_id="urn:bilo:medium:A0023#48-85-TZ",
        license_quantity=random.randint(10, 50),
        license_provider="VHT",
        purchasing_reference="2014-04-11T03:28:16 -02:00 4572022",
        utilization_systems="Antolin",
        validity_start_date=iso_format_date(start),
        validity_end_date=iso_format_date(end),
        validity_duration="{}".format(duration),
        license_special_type=random.choice(["Lehrer", ""]),
        ignored_for_display="0",
        delivery_date=today.isoformat().split("T")[0], # huhu hier todo
        license_school="test_schule",  # todo
    )


@pytest.fixture(scope="function")
def expired_license():
    return get_expired_license()


@pytest.fixture(scope="function")
def random_n_expired_licenses():
    n = random.randint(1, 10)
    return [expired_license() for _ in range(n)]



@pytest.fixture(scope="function")
def random_license():
    return get_random_license()


@pytest.fixture(scope="function")
def random_n_random_licenses():
    n = random.randint(1, 10)
    return [get_random_license() for _ in range(n)]


@pytest.fixture(scope="function")
def random_meta_data():
    return MetaData(
            product_id=uts.random_name(),
            title=uts.random_name(),
            description="some description",
            author=uts.random_name(),
            publisher=uts.random_name(),
            cover=uts.random_name(),
            cover_small=uts.random_name(),
            modified=datetime.datetime.now().strftime('%Y-%m-%d'),
    )


@pytest.fixture()
def lo():
    def add_temp(_dn, *args, **kwargs):
        lo.add_orig(_dn, *args, **kwargs)
        created_objs.append(_dn)

    created_objs = []
    lo, po = getAdminConnection()
    lo.add_orig = lo.add
    lo.add = add_temp
    yield lo
    # we need to sort the dns to first delete the child-nodes
    created_objs.sort(key=lambda _dn: len(ldap.explode_dn(_dn)), reverse=True)
    for dn in created_objs:
        lo.delete(dn)


@pytest.fixture()
def licence_handler(lo):
    return LicenseHandler(lo)


@pytest.fixture()
def assignment_handler(lo):
    return AssignmentHandler(lo)


@pytest.fixture()
def meta_data_handler(lo):
    return MetaDataHandler(lo)


@pytest.fixture(scope='module')
def license_file(tmpdir_factory):
    test_licenses_raw = [{
        "lizenzcode": "UNI-{}".format(uuid.uuid4()),
        "product_id": "urn:bilo:medium:Test1",
        "lizenzanzahl": 25,
        "lizenzgeber": "UNI",
        "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
        "nutzungssysteme": "Antolin",
        "gueltigkeitsbeginn": "15-08-2021",
        "gueltigkeitsende": "14-08-2022",
        "gueltigkeitsdauer": "365",
        "sonderlizenz": "Lehrer",
    }, {
        "lizenzcode": "UNI-{}".format(uuid.uuid4()),
        "product_id": "urn:bilo:medium:Test2",
        "lizenzanzahl": 1,
        "lizenzgeber": "UNI",
        "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
        "nutzungssysteme": "Antolin",
        "gueltigkeitsbeginn": "15-08-2021",
        "gueltigkeitsende": "14-08-2022",
        "gueltigkeitsdauer": "365",
        "sonderlizenz": "",
    }]
    fn = tmpdir_factory.mktemp("data").join('license.json')
    with open(str(fn), 'w') as license_fd:
        json.dump(test_licenses_raw, license_fd)
    return fn


@pytest.fixture
def ucr():
    with UCSTestConfigRegistry() as ucr_test:
        return ucr_test


@pytest.fixture
def ldap_base(ucr):
    return ucr["ldap/base"]
