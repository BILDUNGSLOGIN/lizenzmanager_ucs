#!/usr/share/ucs-test/runner /usr/bin/py.test -slvv --cov-config=.coveragerc --cov-append --cov-report=
# -*- coding: utf-8 -*-
## desc: Run tests for the udm module bildungslogin/license
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## exposure: dangerous
## tags: [bildungslogin]
## packages: [udm-bildungslogin-encoders]
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
import random
import uuid
from hashlib import sha256

import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.config_registry import ConfigRegistry
from univention.udm import CreateError

ucr = ConfigRegistry()
ucr.load()


def test_create_license(create_license):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "demoSCHOOL")
    assert license_obj.props.cn == sha256("LICENSE_CODE").hexdigest()


def test_license_code_insensitive(create_license, scramble_case):
    """Test that for a license the product id has to be unique in a case insensitive way."""
    code = uts.random_name()
    code_other_case = scramble_case(code)
    create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    with pytest.raises(CreateError) as exinfo:
        create_license(code_other_case, "PRODUCT_ID", 22, "DEMOSCHOOL")
    assert "A license with that code already exists" in exinfo.value.message


def test_required_attributes(udm):
    """
    Test that for license the attributes cn, code, product_id, quantity, provider, school or
    delivery_date are mandatory.
    """
    with pytest.raises(CreateError) as exinfo:
        obj = udm.get("bildungslogin/license").new()
        obj.save()
    for attr_name in (
        "cn",
        "code",
        "product_id",
        "quantity",
        "provider",
        "school",
        "delivery_date",
    ):
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
    """Test that a license object can be created in LDAP"""
    with pytest.raises(CreateError) as exinfo:
        obj = udm.get("bildungslogin/license").new()
        obj.save()
    assert "\n{}".format(attr_name) not in exinfo.value.message


def test_unique_codes(create_license):
    """Test that for a license object the CODE has to be unique"""
    code = "CODE"
    create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    with pytest.raises(CreateError) as exinfo:
        create_license(code, "PRODUCT_ID2", 22, "DEMOSCHOOL")
    assert "A license with that code already exists" in exinfo.value.message


def test_existing_school(create_license):
    """Test that for a license object the school must exist in LDAP"""
    code = "CODE"
    non_existing_school = "DEMOSCHOOL" + str(uuid.uuid4())
    with pytest.raises(CreateError) as exinfo:
        create_license(code, "PRODUCT_ID", 10, non_existing_school)
    assert 'The school "{}" does not exist.'.format(non_existing_school) in exinfo.value.message


def test_assignments(create_license, udm):
    """Test that the value of licenses and assignments matches in LDAP"""
    num_licenses = random.randint(2, 10)
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license_obj = create_license(uts.random_name(), uts.random_name(), num_licenses, ou)
        for _ in range(num_licenses):
            assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
            assignment.props.status = "AVAILABLE"
            assignment.save()
        license_obj = udm.get("bildungslogin/license").get(license_obj.dn)
        assert len(license_obj.props.assignments) == num_licenses
        assignments = schoolenv.lo.searchDn(
            "(objectClass=bildungsloginAssignment)", base=str(license_obj.dn)
        )
        assert set(assignments) == set(license_obj.props.assignments)


@pytest.mark.parametrize(
    "expired,validity_end_date",
    (
        (False, datetime.date.today()),
        (True, datetime.date.today() - datetime.timedelta(days=1)),
        (False, datetime.date.today() + datetime.timedelta(days=1)),
        (False, ""),
        (False, None),
    ),
    ids=lambda x: "{1} -> {0}".format(*x),
)
def test_expired(create_license, udm, expired, validity_end_date):
    """Test that a license can be set to expired in LDAP"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license_obj = create_license(
            uts.random_name(), uts.random_name(), 2, ou, validity_end_date=validity_end_date
        )
        license_obj_fresh = udm.get("bildungslogin/license").get(license_obj.dn)
        assert license_obj_fresh.props.expired == expired


@pytest.mark.parametrize(
    "validity_end_date,expected_expired",
    (
        (datetime.date.today() - datetime.timedelta(days=1), 9),
        (datetime.date.today() + datetime.timedelta(days=1), 0),
        ("", 0),
        (None, 0),
    ),
)
def test_num_expired(create_license, udm, validity_end_date, expected_expired):
    """Test that a license shows the right amount of expired licenses depending on expired status"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license_obj = create_license(
            uts.random_name(), uts.random_name(), 10, ou, validity_end_date=validity_end_date
        )
        # Assign one of the 10 licenses
        assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
        assignment.props.status = "AVAILABLE"
        assignment.save()
        assignment.props.status = "ASSIGNED"
        assignment.props.assignee = "SOME_STRING_UUID"
        assignment.props.time_of_assignment = datetime.date.today()
        assignment.save()
        license_obj_fresh = udm.get("bildungslogin/license").get(license_obj.dn)
        assert license_obj_fresh.props.num_expired == expected_expired


def test_num_available(create_license, udm):
    """Test that number of licenses is expected including the expired licenses in LDAP"""
    num_licenses = 10
    num_assigned = random.randint(2, num_licenses - 1)
    num_expired = num_licenses - num_assigned
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        # create an expired license
        license_obj = create_license(uts.random_name(), uts.random_name(), num_licenses, ou)
        for _ in range(num_licenses):
            assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
            assignment.props.status = "AVAILABLE"
            assignment.save()
        # all licenses are expired, as none are assigned
        license_obj_expired = udm.get("bildungslogin/license").get(license_obj.dn)
        assert len(license_obj_expired.props.assignments) == num_licenses
        assert license_obj_expired.props.num_expired == num_licenses
        # assign a few licenses
        assignment_mod = udm.get("bildungslogin/assignment")
        for assignment_dn in license_obj_expired.props.assignments[:num_assigned]:
            assignment_obj = assignment_mod.get(assignment_dn)
            assignment_obj.props.assignee = "foo"
            assignment_obj.props.time_of_assignment = datetime.date.today()
            assignment_obj.props.status = "ASSIGNED"
            assignment_obj.save()
        license_obj_fresh = udm.get("bildungslogin/license").get(license_obj_expired.dn)
        assert len(license_obj_expired.props.assignments) == num_licenses
        assert license_obj_fresh.props.num_expired == num_expired
