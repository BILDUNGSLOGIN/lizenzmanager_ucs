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
## desc: Test the license handler, i.e. the license view.
## exposure: dangerous
## tags: [vbm]
## roles: [domaincontroller_master]

import datetime
from hashlib import sha256

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.handlers import BiloCreateError, BiloLicenseInvalidError
from univention.bildungslogin.utils import LicenseType, Status
from univention.testing.utils import verify_ldap_object
from univention.udm import UDM


def test_license_type(license):
    license.license_quantity = "10"
    assert license.license_type == LicenseType.VOLUME
    license.license_quantity = "1"
    assert license.license_type == LicenseType.SINGLE


def test_create(lo, license_handler, license, ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        cn = sha256(license.license_code).hexdigest()
        license_dn = "cn={},cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
        expected_attr = {
            "cn": [cn],
            "vbmLicenseCode": [license.license_code],
            "vbmProductId": [license.product_id],
            "vbmLicenseQuantity": [license.license_quantity],
            "vbmLicenseProvider": [license.license_provider],
            "vbmPurchasingReference": [license.purchasing_reference],
            "vbmUtilizationSystems": [license.utilization_systems],
            "vbmValidityStartDate": [license.validity_start_date],
            "vbmValidityEndDate": [license.validity_end_date],
            "vbmValidityDuration": [license.validity_duration],
            "vbmDeliveryDate": [license.delivery_date],
            "vbmLicenseSchool": [license.license_school],
            "vbmIgnoredForDisplay": [license.ignored_for_display],
        }
        if license.license_special_type:
            expected_attr["vbmLicenseSpecialType"] = [license.license_special_type]
        verify_ldap_object(
            license_dn,
            expected_attr=expected_attr,
            strict=False,
        )
        # check assignments were created
        for dn in lo.searchDn(base=license_dn, scope="one"):
            expected_attr = {"vbmAssignmentStatus": [Status.AVAILABLE]}
            verify_ldap_object(dn, expected_attr=expected_attr, strict=False)
        # licenses are unique, duplicates produce errors
        with pytest.raises(BiloCreateError):
            license_handler.create(license)


def test_get_assignments_for_license(license_handler, license):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        assignments = license_handler.get_assignments_for_license(license)
        for assignment in assignments:
            assert assignment.status == Status.AVAILABLE
            assert assignment.license == license.license_code


def test_get_total_number_of_licenses(license_handler, license):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        assert license_handler.get_total_number_of_assignments(license) == int(license.license_quantity)


def test_number_of_provisioned_and_assigned_licenses(license_handler, assignment_handler, license):
    # 00_vbm_test_assignments
    # the number of provisioned licenses is included in the number of assigned licenses
    num_students = 3
    num_teachers = 3
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        student_usernames = [schoolenv.create_student(ou)[0] for _ in range(num_students)]
        teacher_usernames = [schoolenv.create_teacher(ou)[0] for _ in range(num_teachers)]
        users = student_usernames + teacher_usernames
        assignment_handler.assign_users_to_licenses(
            usernames=users, license_codes=[license.license_code]
        )
        num_assigned = license_handler.get_number_of_provisioned_and_assigned_assignments(license)
        assert num_assigned == num_students + num_teachers
        for user_name in users[:2]:
            assignment_handler.change_license_status(
                username=user_name,
                license_code=license.license_code,
                status=Status.PROVISIONED,
            )
        # after provisioning the code to some users, the number should still be the same.
        num_assigned = license_handler.get_number_of_provisioned_and_assigned_assignments(license)
        assert num_assigned == num_students + num_teachers
        # the number of available license-assignments for this license should be the total number - the
        # number of users which just a license-assignment for this license
        total_num = license_handler.get_total_number_of_assignments(license)
        assert license_handler.get_number_of_available_assignments(license) == total_num - len(users)


def test_get_number_of_expired_assignments(lo, license_handler, expired_license):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        expired_license.license_school = ou
        license_handler.create(expired_license)
        license_obj = license_handler.get_udm_license_by_code(expired_license.license_code)
        udm = UDM(lo).version(1)
        assignment_mod = udm.get("vbm/assignment")
        for assignment_dn in license_obj.props.assignments[:2]:
            assignment_obj = assignment_mod.get(assignment_dn)
            assignment_obj.props.assignee = "foo"
            assignment_obj.props.time_of_assignment = datetime.datetime.now().strftime("%Y-%m-%d")
            assignment_obj.props.status = Status.ASSIGNED
            assignment_obj.save()
        expected_num = int(expired_license.license_quantity) - 2  # assigned 2 licenses in for loop above
        assert license_handler.get_number_of_expired_assignments(expired_license) == expected_num


def test_get_meta_data_for_license(license_handler, meta_data_handler, license, meta_data):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.product_id = meta_data.product_id
        license.license_school = ou
        license_handler.create(license)
        meta_data_handler.create(meta_data)
        meta_data = license_handler.get_meta_data_for_license(license)
        assert meta_data.product_id == meta_data.product_id
        assert meta_data.title == meta_data.title
        assert meta_data.description == meta_data.description
        assert meta_data.author == meta_data.author
        assert meta_data.publisher == meta_data.publisher
        assert meta_data.cover == meta_data.cover
        assert meta_data.cover_small == meta_data.cover_small
        assert meta_data.modified == meta_data.modified


def test_get_time_of_last_assignment(license_handler, assignment_handler, license):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        username, _ = schoolenv.create_student(ou)
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assert license_handler.get_time_of_last_assignment(license) == datetime.datetime.now().strftime(
            "%Y-%m-%d"
        )


def test_set_license_ignore(license_handler, assignment_handler, license, ldap_base):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        username = schoolenv.create_student(ou)[0]
        license.license_school = ou
        license.ignored_for_display = "0"
        license_handler.create(license)
        cn = sha256(license.license_code).hexdigest()
        license_dn = "cn={},cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
        verify_ldap_object(
            license_dn,
            expected_attr={
                "vbmIgnoredForDisplay": ["0"],
            },
            strict=False,
        )
        license_handler.set_license_ignore(license_code=license.license_code, ignore=True)
        verify_ldap_object(
            license_dn,
            expected_attr={
                "vbmIgnoredForDisplay": ["1"],
            },
            strict=False,
        )
        license_handler.set_license_ignore(license_code=license.license_code, ignore=False)
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        with pytest.raises(BiloLicenseInvalidError):
            license_handler.set_license_ignore(license_code=license.license_code, ignore=True)


def test_get_license_types(license_handler):
    assert {"Volumenlizenz", "Einzellizenz"} == set(license_handler.get_license_types())
