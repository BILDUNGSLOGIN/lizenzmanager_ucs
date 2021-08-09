#!/usr/share/ucs-test/runner /usr/bin/py.test -s
# -*- coding: utf-8 -*-
## desc: Run tests for the udm module vbm/license
## exposure: dangerous
## tags: [vbm]
## packages: [udm-bildungslogin]
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
import uuid
from hashlib import sha256

import pytest

import univention.testing.udm as udm_test
from univention.admin.uexceptions import noObject
from univention.admin.uldap import access, getMachineConnection
from univention.config_registry import ConfigRegistry
from univention.udm import CreateError

ucr = ConfigRegistry()
ucr.load()


def test_create_license(create_license):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "demoSCHOOL")
    assert license_obj.props.cn == sha256("LICENSE_CODE").hexdigest()


@pytest.mark.parametrize(
    "attr_name",
    (
        "cn",
        "code",
        "product_id",
        "quantity",
        "provider",
        "school",
        "delivery_date",
    ),
)
def test_required_attributes(attr_name, udm):
    with pytest.raises(CreateError) as exinfo:
        obj = udm.get("vbm/license").new()
        obj.save()
    assert "\n{}".format(attr_name) in exinfo.value.message


@pytest.mark.parametrize(
    "attr_name",
    (
        "purchasing_reference",
        "utilization_systems",
        "validity_start_date",
        "validity_end_date",
        "validity_duration",
        "special_type",
    ),
)
def test_unrequired_attributes(attr_name, udm):
    with pytest.raises(CreateError) as exinfo:
        obj = udm.get("vbm/license").new()
        obj.save()
    assert "\n{}".format(attr_name) not in exinfo.value.message


def test_unique_codes(create_license):
    code = "CODE"
    create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    with pytest.raises(CreateError) as exinfo:
        create_license(code, "PRODUCT_ID2", 22, "DEMOSCHOOL")
    assert "A license with that code already exists" in exinfo.value.message


def test_existing_school(create_license):
    code = "CODE"
    non_existing_school = "DEMOSCHOOL" + str(uuid.uuid4())
    with pytest.raises(CreateError) as exinfo:
        create_license(code, "PRODUCT_ID", 10, non_existing_school)
    assert 'The school "{}" does not exist.'.format(non_existing_school) in exinfo.value.message


def test_acl_machine(create_license):
    code = "CODE"
    license = create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    lo, _ = getMachineConnection()
    if ucr.get("server/role") in ["domaincontroller_master", "domaincontroller_backup"]:
        assert lo.searchDn(base=license.dn)
    else:
        with pytest.raises(noObject):
            lo.searchDn(base=license.dn)


def test_acl_user(create_license):
    code = "CODE"
    license = create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    user_pw = "univention"
    with udm_test.UCSTestUDM() as udm:
        userdn, username = udm.create_user(password=user_pw)
        lo = access(binddn=userdn, bindpw=user_pw, base=ucr.get("ldap/base"))
        with pytest.raises(noObject):
            lo.searchDn(base=license.dn)
