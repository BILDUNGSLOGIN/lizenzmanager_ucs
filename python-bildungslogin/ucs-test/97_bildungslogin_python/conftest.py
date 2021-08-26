#!/usr/share/ucs-test/runner /usr/bin/py.test -s
# -*- coding: utf-8 -*-
#
# Copyright 2021 Univention GmbH
#
# https://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/>.

import datetime
import json
import random
import string
import uuid
from contextlib import contextmanager

import ldap
import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.admin.uexceptions import noObject
from univention.admin.uldap import getAdminConnection
from univention.bildungslogin.handlers import AssignmentHandler, LicenseHandler, MetaDataHandler
from univention.bildungslogin.models import License, MetaData
from univention.testing.ucr import UCSTestConfigRegistry


@pytest.fixture(scope="module")
def ou():
    """if you don't need cleanup after every test. Use with caution"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        yield ou


def iso_format_date(my_date):
    return my_date.strftime("%Y-%m-%d")


def random_string(n):  # type: (int) -> str
    return "".join([random.choice(string.ascii_uppercase + string.digits) for _ in range(n)])


def product_id():
    return "urn:bilo:medium:{}#{}-{}-{}".format(
        random_string(5), random_string(2), random_string(2), random_string(2)
    )


def get_license(ou):  # type: (str) -> License
    today = datetime.date.today()
    start = today + datetime.timedelta(days=random.randint(0, 365))
    duration = "Unbeschränkt"
    end = start + datetime.timedelta(days=random.randint(0, 365))
    provider = uts.random_username()
    return License(
        license_code="{}-{}".format(provider, str(uuid.uuid4())),
        product_id=product_id(),
        license_quantity=random.randint(2, 10),
        license_provider=provider,
        purchasing_reference=today.isoformat(),  # could be just a random string
        utilization_systems=uts.random_username(),
        validity_start_date=start,
        validity_end_date=end,
        validity_duration=duration,
        license_special_type="",
        ignored_for_display=False,
        delivery_date=today,
        license_school=ou,
    )


def get_expired_license(ou):
    """the validity_end_date < today"""
    today = datetime.date.today()
    duration = "Ein Schuljahr"
    start = today - datetime.timedelta(days=random.randint(2, 365))
    license = get_license(ou)
    license.validity_start_date = start
    license.validity_end_date = today - datetime.timedelta(1)
    license.validity_duration = duration
    return license


@pytest.fixture(scope="function")
def expired_license_obj():
    def _func(ou):
        return get_expired_license(ou)

    return _func


@pytest.fixture(scope="function")
def n_expired_licenses(expired_license_obj):
    def _func(ou):
        n = random.randint(1, 10)
        return [expired_license_obj(ou) for _ in range(n)]

    return _func


@pytest.fixture(scope="function")
def license_obj():
    def _func(ou):  # type: (str) -> License
        return get_license(ou)

    return _func


@pytest.fixture(scope="function")
def n_licenses():
    def _func(ou):
        n = random.randint(1, 10)
        return [get_license(ou) for _ in range(n)]

    return _func


def get_meta_data():
    return MetaData(
        product_id=uts.random_name(),
        title=uts.random_name(),
        description="some description",
        author=uts.random_name(),
        publisher=uts.random_name(),
        cover=uts.random_name(),
        cover_small=uts.random_name(),
        modified=datetime.date.today(),
    )


@pytest.fixture(scope="function")
def meta_data():
    return get_meta_data()


@pytest.fixture(scope="function")
def n_meta_data():
    n = random.randint(1, 10)
    return [get_meta_data() for _ in range(n)]


@contextmanager
def __lo():
    """this is to simplify some of our tests with the simple udm api,
    so we do not have to use the ucs-test school env all the time."""

    def add_temp(_dn, *args, **kwargs):
        lo.add_orig(_dn, *args, **kwargs)
        created_objs.append(_dn)

    created_objs = []
    lo, po = getAdminConnection()
    lo.add_orig = lo.add
    lo.add = add_temp
    try:
        yield lo
    finally:
        # we need to sort the dns to first delete the child-nodes
        created_objs.sort(key=lambda _dn: len(ldap.explode_dn(_dn)), reverse=True)
        for dn in created_objs:
            try:
                lo.delete(dn)
            except noObject:
                pass
        lo.add = lo.add_orig
        lo.unbind()


@pytest.fixture()
def lo():
    with __lo() as lo:
        yield lo


@pytest.fixture(scope="module")
def lo_module():
    with __lo() as lo:
        yield lo


@pytest.fixture()
def license_handler(lo):
    return LicenseHandler(lo)


@pytest.fixture()
def assignment_handler(lo):
    return AssignmentHandler(lo)


@pytest.fixture()
def meta_data_handler(lo):
    return MetaDataHandler(lo)


@pytest.fixture(scope="module")
def license_file(tmpdir_factory):
    test_licenses_raw = [
        {
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
        },
        {
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
        },
    ]
    fn = tmpdir_factory.mktemp("data").join("license.json")
    with open(str(fn), "w") as license_fd:
        json.dump(test_licenses_raw, license_fd)
    return fn


@pytest.fixture
def ucr():
    with UCSTestConfigRegistry() as ucr_test:
        return ucr_test


@pytest.fixture
def ldap_base(ucr):
    return ucr["ldap/base"]
