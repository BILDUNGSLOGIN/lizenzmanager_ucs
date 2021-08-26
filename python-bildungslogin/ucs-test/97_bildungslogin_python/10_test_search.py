#!/usr/share/ucs-test/runner /usr/bin/py.test -slv
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
## desc: search for licenses
## exposure: dangerous
## tags: [bildungslogin]
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## packages: [python-bildungslogin, udm-bildungslogin-encoders]

from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from conftest import get_license, get_meta_data

from ucsschool.lib.models.user import Student
from univention.bildungslogin.handlers import AssignmentHandler, LicenseHandler, MetaDataHandler
from univention.bildungslogin.utils import LicenseType
from univention.udm import UDM

GOOD_SEARCH = "FOUND"
FUZZY_SEARCH = "*FUZZY*"
BAD_SEARCH = "NOT_FOUND"


@pytest.fixture(scope="module")
def test_user(lo_module, ou):
    user = Student(
        password="univention",
        name="bildungslogin_username",
        firstname="bildungslogin_firstname",
        lastname="bildungslogin_lastname",
        school=ou,
    )
    user.create(lo_module)
    return user.name


@pytest.fixture(scope="module")
def single_license(
    lo_module,
    ou,
    test_user,
):
    license_handler = LicenseHandler(lo_module)
    meta_data_handler = MetaDataHandler(lo_module)
    assignment_handler = AssignmentHandler(lo_module)
    license = get_license(ou)
    meta_data = get_meta_data()
    meta_data.title = "univention_s"
    meta_data.publisher = "univention_s"
    license.license_code = "univention_s"
    meta_data.product_id = "univention_s"
    license.license_quantity = 1
    license.product_id = meta_data.product_id
    license_handler.create(license)
    meta_data_handler.create(meta_data)
    assignment_handler.assign_to_license(license.license_code, test_user)
    return license


@pytest.fixture(scope="module")
def volume_license(
    lo_module,
    ou,
    test_user,
):
    license_handler = LicenseHandler(lo_module)
    meta_data_handler = MetaDataHandler(lo_module)
    assignment_handler = AssignmentHandler(lo_module)
    license = get_license(ou)
    meta_data = get_meta_data()
    meta_data.title = "univention_v"
    meta_data.publisher = "univention_v"
    license.license_code = "univention_v"
    meta_data.product_id = "univention_v"
    license.license_quantity = 2
    license.product_id = meta_data.product_id
    license_handler.create(license)
    meta_data_handler.create(meta_data)
    assignment_handler.assign_to_license(license.license_code, test_user)
    return license


@pytest.fixture(scope="module")
def udm_license_mod(lo_module):
    udm = UDM(lo_module).version(1)
    return udm.get("bildungslogin/license")


@pytest.mark.parametrize(
    "title",
    [
        GOOD_SEARCH,
        FUZZY_SEARCH,
        BAD_SEARCH,
    ],
)
@pytest.mark.parametrize(
    "publisher",
    [
        GOOD_SEARCH,
        FUZZY_SEARCH,
        BAD_SEARCH,
    ],
)
@pytest.mark.parametrize(
    "license_code",
    [
        GOOD_SEARCH,
        FUZZY_SEARCH,
        BAD_SEARCH,
    ],
)
@pytest.mark.parametrize(
    "product_id",
    [
        GOOD_SEARCH,
        FUZZY_SEARCH,
        BAD_SEARCH,
    ],
)
def test_search_for_license_pattern(
    ou,
    license_handler,
    license_obj,
    meta_data_handler,
    meta_data,
    title,
    publisher,
    license_code,
    product_id,
):
    """Test simple search with OR in title, publisher, license code (case sensitive)
    and product id (case sensitive)"""

    def __create_license(title=None, publisher=None, license_code=None, product_id=None):
        new_license = deepcopy(license_obj(ou))
        new_meta_data = deepcopy(meta_data)
        if title:
            new_meta_data.title = title.replace("*", "sun")
        if publisher:
            new_meta_data.publisher = publisher.replace("*", "sun")
        if license_code:
            new_license.license_code = license_code.replace("*", "sun")
        else:
            new_license.license_code = "uni:{}".format(uuid4())
        if product_id:
            new_meta_data.product_id = product_id.replace("*", "sun")
        else:
            new_meta_data.product_id = str(uuid4())
        new_license.product_id = new_meta_data.product_id
        new_license.license_school = ou
        license_handler.create(new_license)
        meta_data_handler.create(new_meta_data)
        return new_license.license_code

    test_license_codes = {
        GOOD_SEARCH: set(),
        BAD_SEARCH: set(),
        FUZZY_SEARCH: set(),
    }
    test_license_codes[title].add(__create_license(title=title))
    test_license_codes[publisher].add(__create_license(publisher=publisher))
    test_license_codes[license_code].add(__create_license(license_code=license_code))
    test_license_codes[product_id].add(__create_license(product_id=product_id))

    res = license_handler.search_for_licenses(
        is_advanced_search=False, pattern=GOOD_SEARCH, school=ou + "_different_school"
    )
    assert len(res) == 0
    res = license_handler.search_for_licenses(is_advanced_search=False, pattern=GOOD_SEARCH, school=ou)
    assert (
        len(res)
        == (
            title,
            publisher,
            license_code,
            product_id,
        ).count(GOOD_SEARCH)
    )
    assert test_license_codes[GOOD_SEARCH] == set(res_l["licenseCode"] for res_l in res)
    res = license_handler.search_for_licenses(is_advanced_search=False, pattern=FUZZY_SEARCH, school=ou)
    assert (
        len(res)
        == (
            title,
            publisher,
            license_code,
            product_id,
        ).count(FUZZY_SEARCH)
    )
    assert test_license_codes[FUZZY_SEARCH] == set(res_l["licenseCode"] for res_l in res)


#  Warning: all combinations take a lot of time
@pytest.mark.parametrize(
    "time_from",
    [
        (None, True),
        (datetime.now() - timedelta(days=2), True),
        (datetime.now() + timedelta(days=2), False),
    ],
)
@pytest.mark.parametrize(
    "time_to",
    [
        (None, True),
        (datetime.now() - timedelta(days=2), False),
        (datetime.now() + timedelta(days=2), True),
    ],
)
@pytest.mark.parametrize(
    "only_available_licenses",
    [
        (False, True),
        (True, False),
    ],
)
@pytest.mark.parametrize(
    "publisher",
    [
        ("", True),
        # ("*vention{}", True),
        # ("univention{}", True),
        # ("foobar", False),
    ],
)
@pytest.mark.parametrize(
    "license_type",
    [
        ("", True),
        (LicenseType.SINGLE, True),
        (LicenseType.VOLUME, True),
    ],
)
@pytest.mark.parametrize(
    "user_pattern",
    [
        ("*", True),
        ("bildungslogin*username", True),
        ("bildungslogin*firstname", True),
        ("bildungslogin*lastname", True),
        ("foobar", False),
    ],
)
@pytest.mark.parametrize(
    "product_id",
    [
        ("*", True),
        # ("*vention{}", True),
        # ("univention{}", True),
        # ("foobar", False),
    ],
)
@pytest.mark.parametrize(
    "product",
    [
        ("*", True),
        ("*vention{}", True),
        ("univention{}", True),
        ("foobar", False),
    ],
)
@pytest.mark.parametrize(
    "license_code",
    [
        # ("*", True),
        ("*vention{}", True),
        # ("univention{}", True),
        # ("foobar", False),
    ],
)
def test_search_for_license_advance(
    ou,
    udm_license_mod,
    license_handler,
    single_license,
    volume_license,
    time_from,
    time_to,
    only_available_licenses,
    publisher,
    license_type,
    user_pattern,
    product_id,
    product,
    license_code,
):
    """Test advanced search with AND in start period/end period, only available licenses,
    user identification, product id (case sensitive), title and  license code (case sensitive)"""
    if license_type[0] == LicenseType.SINGLE:
        license_appendix = "_s"
    else:
        license_appendix = "_v"
    res = license_handler.search_for_licenses(
        is_advanced_search=True,
        time_to=time_to[0],
        time_from=time_from[0],
        only_available_licenses=only_available_licenses[0],
        publisher=publisher[0].format(license_appendix),
        license_type=license_type[0],
        user_pattern=user_pattern[0],
        product_id=product_id[0].format(license_appendix),
        product=product[0].format(license_appendix),
        license_code=license_code[0].format(license_appendix),
        school=ou + "_different_school",
    )
    assert len(res) == 0
    res = license_handler.search_for_licenses(
        is_advanced_search=True,
        time_to=time_to[0],
        time_from=time_from[0],
        only_available_licenses=only_available_licenses[0],
        publisher=publisher[0].format(license_appendix),
        license_type=license_type[0],
        user_pattern=user_pattern[0],
        product_id=product_id[0].format(license_appendix),
        product=product[0].format(license_appendix),
        license_code=license_code[0].format(license_appendix),
        school=ou,
    )
    should_be_found = all(
        (
            time_to[1],
            time_from[1],
            only_available_licenses[1] or license_type[0] in (LicenseType.VOLUME, ""),
            publisher[1],
            license_type[1],
            user_pattern[1],
            user_pattern[1],
            product_id[1],
            product[1],
            license_code[1],
        )
    )
    if license_type[0] == LicenseType.SINGLE:
        assert (
            single_license.license_code in set(res_l["licenseCode"] for res_l in res)
        ) == should_be_found
    else:
        assert (
            volume_license.license_code in set(res_l["licenseCode"] for res_l in res)
        ) == should_be_found
