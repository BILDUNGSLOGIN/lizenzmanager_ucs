#!/usr/share/ucs-test/runner /usr/bin/py.test -slvv --cov --cov-config=.coveragerc --cov-append --cov-report=
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
## tags: [bildungslogin]
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## packages: [python-bildungslogin, udm-bildungslogin-encoders]

import datetime
from hashlib import sha256
from typing import TYPE_CHECKING

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.handlers import BiloCreateError, ObjectType
from univention.bildungslogin.models import LicenseType, Status
from univention.bildungslogin.utils import get_entry_uuid
from univention.testing.utils import verify_ldap_object
from univention.udm import UDM

if TYPE_CHECKING:
    from univention.bildungslogin.models import License


@pytest.mark.skip(reason="License type is not defined dynamically anymore")
def test_license_type(license_obj):
    """Test that a license can have the type VOLUME for many or SINGLE for quantity 1"""
    license = license_obj("foo")
    license.license_quantity = 10
    assert license.license_type == LicenseType.VOLUME
    license.license_quantity = 1
    assert license.license_type == LicenseType.SINGLE


@pytest.mark.parametrize("license_type", [LicenseType.SINGLE, LicenseType.VOLUME,
                                          LicenseType.SCHOOL, LicenseType.WORKGROUP])
def test_create(lo, license_handler, get_license, ldap_base, hostname, license_type):
    """Test that a license assignment can be used once in atatus AVAILABLE and can not assigned multiple times."""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        license = get_license(ou, license_type=license_type)
        license_handler.create(license)
        cn = sha256(license.license_code).hexdigest()
        license_dn = "cn={},cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
        expected_attr = {
            "cn": [cn],
            "bildungsloginLicenseCode": [license.license_code],
            "bildungsloginProductId": [license.product_id],
            "bildungsloginLicenseQuantity": [str(license.license_quantity)],
            "bildungsloginLicenseProvider": [license.license_provider],
            "bildungsloginPurchasingReference": [license.purchasing_reference],
            "bildungsloginUtilizationSystems": [license.utilization_systems],
            "bildungsloginValidityStartDate": [license.validity_start_date.strftime("%Y-%m-%d")],
            "bildungsloginValidityEndDate": [license.validity_end_date.strftime("%Y-%m-%d")],
            "bildungsloginValidityDuration": [license.validity_duration],
            "bildungsloginDeliveryDate": [license.delivery_date.strftime("%Y-%m-%d")],
            "bildungsloginLicenseSchool": [license.license_school],
            "bildungsloginIgnoredForDisplay": ["1" if license.ignored_for_display else "0"],
        }
        if license.license_special_type:
            expected_attr["bildungsloginLicenseSpecialType"] = [license.license_special_type]
        verify_ldap_object(
            license_dn,
            expected_attr=expected_attr,
            strict=False,
            primary=True,
        )
        # check assignments were created
        assignments = list(lo.searchDn(base=license_dn, scope="one"))
        if license_type in [LicenseType.SINGLE, LicenseType.VOLUME]:
            assert len(assignments) == license.license_quantity
        elif license_type in [LicenseType.SCHOOL, LicenseType.WORKGROUP]:
            assert len(assignments) == 1

        for dn in assignments:
            expected_attr = {"bildungsloginAssignmentStatus": [Status.AVAILABLE]}
            verify_ldap_object(dn, expected_attr=expected_attr, strict=False, primary=True)
        # licenses are unique, duplicates produce errors
        with pytest.raises(BiloCreateError):
            license_handler.create(license)


def test_get_assignments_for_license_with_filter(
    license_handler, assignment_handler, license_obj, hostname, lo
):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        user_name, user_dn = schoolenv.create_student(ou)
        user_entryuuid = get_entry_uuid(lo, user_dn)
        license = license_obj(ou)
        license.license_quantity = 2
        license_handler.create(license)
        assignment_handler.assign_objects_to_licenses(
            license_codes=[license.license_code],
            object_type=ObjectType.USER,
            object_names=[user_name])
        result = license_handler.get_assignments_for_license_with_filter(
            license, "(bildungsloginAssignmentStatus=ASSIGNED)"
        )
        assert len(result) == 1
        assert result[0].license == license.license_code
        assert result[0].assignee == user_entryuuid


@pytest.mark.parametrize("license_type", ["SCHOOL", "WORKGROUP", "VOLUME"])
def test_get_assigned_users(license_type, license_handler, assignment_handler,
                            get_license, lo, hostname):
    with utu.UCSTestSchool() as schoolenv:
        # create school, users, and group
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        student_name, student_dn = schoolenv.create_student(ou)
        teacher_name, teacher_dn = schoolenv.create_teacher(ou)
        wg_name, _ = schoolenv.create_workgroup(ou, users=[student_dn, teacher_dn])
        # create license
        license = get_license(ou, license_type=license_type)
        license.license_quantity = 2
        license_handler.create(license)
        # define object type
        if license_type == LicenseType.SCHOOL:
            object_type = ObjectType.SCHOOL
            object_names = [ou]
        elif license_type == LicenseType.WORKGROUP:
            object_type = ObjectType.GROUP
            object_names = [wg_name]
        elif license_type == LicenseType.VOLUME:
            object_type = ObjectType.USER
            object_names = [teacher_name, student_name]
        else:
            raise RuntimeError
        # assign license
        assignment_handler.assign_objects_to_licenses(
            license_codes=[license.license_code],
            object_type=object_type,
            object_names=object_names)

        assigned_users = license_handler.get_assigned_users(license)
        expected_assigned_users = [
            {
                "username": teacher_name,
                "status": "ASSIGNED",
                "statusLabel": "Assigned",
                "dateOfAssignment": datetime.date.today(),
            },
            {
                "username": student_name,
                "status": "ASSIGNED",
                "statusLabel": "Assigned",
                "dateOfAssignment": datetime.date.today(),
            },
        ]
        assert sorted(assigned_users, key=lambda x: x["username"]) \
               == sorted(expected_assigned_users, key=lambda x: x["username"])


def test_number_of_provisioned_and_assigned_licenses(
    license_handler, assignment_handler, license_obj, hostname
):
    """Test that the number of license assignments is the same as the number of selected teachers and students"""
    # the number of provisioned licenses is included in the number of assigned licenses
    num_students = 3
    num_teachers = 3
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        student_usernames = [schoolenv.create_student(ou)[0] for _ in range(num_students)]
        teacher_usernames = [schoolenv.create_teacher(ou)[0] for _ in range(num_teachers)]
        users = student_usernames + teacher_usernames
        license = license_obj(ou)  # type: License
        license.license_quantity = len(users) + 1
        license_handler.create(license)
        assignment_handler.assign_objects_to_licenses(
            license_codes=[license.license_code],
            object_type=ObjectType.USER,
            object_names=users)
        license = license_handler.get_license_by_code(license.license_code)  # refresh object from LDAP
        assert license.num_assigned == num_students + num_teachers
        for user_name in users[:2]:
            assignment_handler.change_license_status(license_code=license.license_code,
                                                     object_type=ObjectType.USER, object_name=user_name,
                                                     status=Status.PROVISIONED)
        # after provisioning the code to some users, the number should still be the same.
        license = license_handler.get_license_by_code(license.license_code)  # refresh object from LDAP
        assert license.num_assigned == num_students + num_teachers
        # the number of available license-assignments for this license should be the total number - the
        # number of users which just a license-assignment for this license
        total_num = license.license_quantity
        assert license.num_available == total_num - len(users)


def test_get_number_of_expired_unassigned_users(lo, license_handler, expired_license_obj, hostname):
    """Test that the number of expired license assignments is as expected"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        username, user_dn = schoolenv.create_student(ou)
        expired_license = expired_license_obj(ou)
        license_handler.create(expired_license)
        license_obj = license_handler.get_udm_license_by_code(expired_license.license_code)
        udm = UDM(lo).version(1)
        user_entry_uuid = get_entry_uuid(lo, user_dn)
        assignment_mod = udm.get("bildungslogin/assignment")
        for assignment_dn in license_obj.props.assignments[:2]:
            assignment_obj = assignment_mod.get(assignment_dn)
            assignment_obj.props.assignee = user_entry_uuid
            assignment_obj.props.time_of_assignment = datetime.date.today()
            assignment_obj.props.status = Status.ASSIGNED
            assignment_obj.save()
        expected_num = expired_license.license_quantity - 2  # assigned 2 licenses in for loop above
        assert license_handler.get_number_of_expired_unassigned_users(expired_license) == expected_num


@pytest.mark.parametrize("use_udm", [True, False])
def test_get_meta_data_for_license(
    license_handler, meta_data_handler, license_obj, meta_data, hostname, use_udm
):
    """Test that for a license the meta data is available"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        license = license_obj(ou)
        license.product_id = meta_data.product_id
        license_handler.create(license)
        meta_data_handler.create(meta_data)
        if use_udm:
            argument = license_handler.get_udm_license_by_code(license.license_code)
        else:
            argument = license
        meta_data = license_handler.get_meta_data_for_license(argument)
        assert meta_data.product_id == meta_data.product_id
        assert meta_data.title == meta_data.title
        assert meta_data.description == meta_data.description
        assert meta_data.author == meta_data.author
        assert meta_data.publisher == meta_data.publisher
        assert meta_data.cover == meta_data.cover
        assert meta_data.cover_small == meta_data.cover_small
        assert meta_data.modified == meta_data.modified


def test_set_license_ignore(license_handler, assignment_handler, license_obj, ldap_base):
    """Test that a license can be set to ignored and can not assigned afterwards"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        username = schoolenv.create_student(ou)[0]
        license.ignored_for_display = False
        license_handler.create(license)
        cn = sha256(license.license_code).hexdigest()
        license_dn = "cn={},cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
        verify_ldap_object(
            license_dn,
            expected_attr={
                "bildungsloginIgnoredForDisplay": ["0"],
            },
            strict=False,
            primary=True,
        )
        license_handler.set_license_ignore(license_code=license.license_code, ignore=True)
        verify_ldap_object(
            license_dn,
            expected_attr={
                "bildungsloginIgnoredForDisplay": ["1"],
            },
            strict=False,
            primary=True,
        )
        license_handler.set_license_ignore(license_code=license.license_code, ignore=False)
        udm_license = license_handler.get_udm_license_by_code(license.license_code)
        assignment_handler.assign_license(license=udm_license,
                                          object_type=ObjectType.USER,
                                          object_name=username)
        assert (
            license_handler.set_license_ignore(license_code=license.license_code, ignore=True) is False
        )


def test_get_license_types(license_handler):
    """Test that a license type is implemented for "Volume license" and "Single license" """
    expected_license_types = {"VOLUME", "SINGLE", "WORKGROUP", "SCHOOL"}
    actual_license_types = {t["id"] for t in license_handler.get_license_types()}
    assert actual_license_types == expected_license_types


@pytest.mark.xfail(reason="Not implemented yet.")
def test_get_all():
    raise NotImplementedError("Missing test for LicenseHandler.get_all()")
