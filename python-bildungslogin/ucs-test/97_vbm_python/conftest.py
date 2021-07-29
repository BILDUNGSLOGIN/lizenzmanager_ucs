import uuid

import pytest
import ldap
import random
from univention.bildungslogin.models import License
from univention.bildungslogin.handler import LicenseHandler, MetaDataHandler, AssignmentHandler
from univention.admin.uldap import getAdminConnection
from univention.udm import UDM

import datetime





@pytest.fixture(scope="function")
def random_license():
    today = datetime.datetime.now()
    # start = today + random.randint(0, 365)
    # end = start + random.randint(1, 365)
    license = License(
    license_code="VHT-{}".format(str(uuid.uuid4())),
    product_id="urn:bilo:medium:A0023#48-85-TZ",
    license_quantity=random.randint(10, 50),
    license_provider="VHT",
    purchasing_reference="2014-04-11T03:28:16 -02:00 4572022",
    utilization_systems="Antolin",
    validity_start_date="15.08.21",
    validity_end_date="14.08.22",
    validity_duration="365",
    license_special_type=random.choice(["Lehrer", ""]),
    ignored_for_display="0",
    delivery_date=datetime.datetime.now().isoformat().split('T')[0],
    license_school='test_schule',
)
    return license


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
