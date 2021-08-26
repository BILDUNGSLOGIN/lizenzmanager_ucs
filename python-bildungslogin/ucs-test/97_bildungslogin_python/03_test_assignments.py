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
## desc: Test the assignment handler, i.e. changing the status of the licenses
## exposure: dangerous
## tags: [bildungslogin]
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## packages: [python-bildungslogin, udm-bildungslogin-encoders]

import datetime
import random
from typing import List

import pytest
from ldap.filter import filter_format

import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.roles import get_role_info
from univention.bildungslogin.handlers import AssignmentHandler, BiloAssignmentError, LicenseHandler
from univention.bildungslogin.models import Assignment, License
from univention.bildungslogin.utils import Status


def license_was_assigned_correct_to_user(assignments, username):
    for a in assignments:
        assert type(a) is Assignment
        if a.assignee == username:
            assignment = a
            assert username == assignment.assignee
            assert Status.ASSIGNED == assignment.status
            assert assignment.time_of_assignment == datetime.date.today()
            break


def get_assignments_from_dn(assignment_handler, dn):  # type: (AssignmentHandler, str) -> Assignment
    udm_license = assignment_handler._assignments_mod.get(dn)
    return assignment_handler.from_udm_obj(udm_license)


def get_assignments_for_license(assignment_handler, license_handler, license):
    # type: (AssignmentHandler, LicenseHandler, License) -> List[Assignment]
    """helper function to search in udm layer"""
    udm_obj = license_handler.get_udm_license_by_code(license.license_code)
    assignment_dns = udm_obj.props.assignments
    return [get_assignments_from_dn(assignment_handler, dn) for dn in assignment_dns]


def get_assignments_for_product_id_for_user(assignment_handler, username, product_id):
    # type: (AssignmentHandler, str, str) -> List[Assignment]
    """get all assignments for a product, which are assigned to a user."""
    user_entry_uuid = assignment_handler._get_entry_uuid_by_username(username)
    filter_s = filter_format("(product_id=%s)", [product_id])
    udm_licenses = assignment_handler._licenses_mod.search(filter_s)
    assignments = []
    for udm_license in udm_licenses:
        assignments.extend(
            assignment_handler.get_all_assignments_for_user(
                assignee=user_entry_uuid, base=udm_license.dn
            )
        )
    return assignments


@pytest.mark.parametrize("user_type", ["student", "teacher"])
def test_assign_user_to_license(assignment_handler, license_handler, license_obj, user_type):
    """Test that a license can be assigned to a user"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license_handler.create(license)
        if user_type == "student":
            username = schoolenv.create_student(ou)[0]
        elif user_type == "teacher":
            username = schoolenv.create_teacher(ou)[0]
        success = assignment_handler.assign_to_license(
            username=username, license_code=license.license_code
        )
        assert success is True
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        license_was_assigned_correct_to_user(assignments, username)
        # (username, license_code) is unique
        success2 = assignment_handler.assign_to_license(
            username=username, license_code=license.license_code
        )
        assert success2 is True


@pytest.mark.parametrize("ignored", [True, False])
def test_check_is_ignored(ignored):
    """Test that a license can not be used if the ignore flag is set"""
    if ignored is not False:
        with pytest.raises(BiloAssignmentError) as excinfo:
            AssignmentHandler.check_is_ignored(ignored)
        assert "License is 'ignored for display' and thus can't be assigned!" in str(excinfo.value)
    else:
        AssignmentHandler.check_is_ignored(ignored)


def test_assign_user_to_expired_license_fails(assignment_handler, license_handler, license_obj):
    """Test that a license can not be assigned if the license is expired"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license.validity_end_date = datetime.date.today() - datetime.timedelta(days=1)
        license_handler.create(license)
        username = schoolenv.create_student(ou)[0]
        with pytest.raises(BiloAssignmentError, match="License is expired") as excinfo:
            assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assert "License is expired" in str(excinfo.value)


def test_assign_user_to_ignored_license_fails(assignment_handler, license_handler, license_obj):
    """Test that a license can not be assigned if the ignore flag is set"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license.ignored_for_display = True
        license_handler.create(license)
        username = schoolenv.create_student(ou)[0]
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assert "License is 'ignored for display' and thus can't be assigned!" in str(excinfo.value)


@pytest.mark.parametrize(
    "license_school,ucsschool_school",
    [("demoschool", "demoschool"), ("demOSchool", "DEMOSCHOOL"), ("demoschool", "demoschool2")],
)
def test_check_license_can_be_assigned_to_school_user(license_school, ucsschool_school):
    """Test that a license associated to a school can not be assigned to a user of a different school"""
    if license_school.lower() == ucsschool_school.lower():
        AssignmentHandler.check_license_can_be_assigned_to_school_user(
            license_school=license_school, ucsschool_schools=[ucsschool_school]
        )
    else:
        with pytest.raises(BiloAssignmentError) as excinfo:
            AssignmentHandler.check_license_can_be_assigned_to_school_user(
                license_school=license_school, ucsschool_schools=[ucsschool_school]
            )
        assert "License can't be assigned to user in school" in str(excinfo.value)


def test_remove_assignment_from_users(assignment_handler, license_handler, license_obj):
    """Test that license assignment can be removed from an user"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        n = random.randint(0, 10)
        usernames = [schoolenv.create_student(ou)[0] for _ in range(n)]
        usernames.append(schoolenv.create_teacher(ou)[0])
        license = license_obj(ou)
        license.license_special_type = ""
        license.license_quantity = len(usernames) + 1
        license_handler.create(license)
        assignment_handler.assign_users_to_licenses(
            usernames=usernames, license_codes=[license.license_code]
        )
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        for username in usernames:
            license_was_assigned_correct_to_user(assignments, username)
        failed_assignments = assignment_handler.remove_assignment_from_users(
            usernames=usernames, license_code=license.license_code
        )
        assert len(failed_assignments) == 0
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        assignees = [a.assignee for a in assignments]
        for username in usernames:
            assert username not in assignees


def test_assign_users_to_licenses(assignment_handler, license_handler, license_obj):
    """Test that a license can be assigned to a user with status ASSIGNED"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license_handler.create(license)
        usernames = [schoolenv.create_student(ou)[0] for _ in range(license.license_quantity)]
        assignment_handler.assign_users_to_licenses(
            usernames=usernames, license_codes=[license.license_code]
        )
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        for username in usernames:
            license_was_assigned_correct_to_user(assignments, username)


def test_get_assignments_for_product_id_for_user(license_handler, assignment_handler, license_obj):
    """Test that a license can be assigned to a user and the user have the product"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license_handler.create(license)
        username = schoolenv.create_student(ou)[0]
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assignments = get_assignments_for_product_id_for_user(
            assignment_handler=assignment_handler, username=username, product_id=license.product_id
        )
        assert len(assignments) == 1
        license_was_assigned_correct_to_user(assignments, username)


@pytest.mark.parametrize("user_type", ["student", "teacher"])
def test_positive_change_license_status(license_handler, assignment_handler, user_type, license_obj):
    """Positive test: test all valid status changes (+ if status was set correct)"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license_handler.create(license)
        if user_type == "student":
            username = schoolenv.create_student(ou)[0]
        elif user_type == "teacher":
            username = schoolenv.create_teacher(ou)[0]
        success = assignment_handler.assign_to_license(
            username=username, license_code=license.license_code
        )
        assert success is True
        assignments = get_assignments_for_product_id_for_user(
            assignment_handler=assignment_handler, username=username, product_id=license.product_id
        )
        assignment = assignments[0]
        assert assignment.status == Status.ASSIGNED
        success = assignment_handler.change_license_status(
            username=username,
            license_code=license.license_code,
            status=Status.AVAILABLE,
        )
        assert success is True
        assignments = get_assignments_for_product_id_for_user(
            assignment_handler=assignment_handler, username=username, product_id=license.product_id
        )
        assert len(assignments) == 0
        # license has to be reassigned to also have a username at the assignment
        success = assignment_handler.assign_to_license(
            username=username, license_code=license.license_code
        )
        assert success is True
        assignment = get_assignments_for_product_id_for_user(
            assignment_handler=assignment_handler, username=username, product_id=license.product_id
        )[0]
        assert assignment.status == Status.ASSIGNED
        success = assignment_handler.change_license_status(
            username=username,
            license_code=license.license_code,
            status=Status.PROVISIONED,
        )
        assert success is True
        assignment = get_assignments_for_product_id_for_user(
            assignment_handler=assignment_handler, username=username, product_id=license.product_id
        )[0]
        assert assignment.status == Status.PROVISIONED


@pytest.mark.parametrize("user_type", ["student", "teacher"])
def test_negative_change_license_status(license_handler, assignment_handler, user_type, license_obj):
    """Negative test: test all invalid status changes"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license_handler.create(license)
        if user_type == "student":
            username = schoolenv.create_student(ou)[0]
        elif user_type == "teacher":
            username = schoolenv.create_teacher(ou)[0]
        # the status can only be changed for assignments which already have an assignee
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.change_license_status(
                username=username,
                license_code=license.license_code,
                status=Status.PROVISIONED,
            )
        assert "No assignment for license with" in str(excinfo.value)
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assignment_handler.change_license_status(
            username=username,
            license_code=license.license_code,
            status=Status.PROVISIONED,
        )
        # license-assignments which have the status provisioned can't change their status.
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.change_license_status(
                username=username,
                license_code=license.license_code,
                status=Status.AVAILABLE,
            )
            assignment_handler.change_license_status(
                username=username,
                license_code=license.license_code,
                status=Status.ASSIGNED,
            )
        assert "Invalid status transition from PROVISIONED to AVAILABLE." in str(excinfo.value)


@pytest.mark.parametrize(
    "user_roles",
    [
        ("student:school:demoschool",),
        ("teacher:school:demoschool",),
        ("teacher:school:demoschool", "staff:school:demoschool"),
    ],
)
@pytest.mark.parametrize("license_type", ["Lehrer", ""])
def test_check_license_type_is_correct(assignment_handler, user_roles, license_type):
    """Test that a license with string type "Lehrer" can not be assigned to a student"""
    roles = [get_role_info(role)[0] for role in user_roles]
    if license_type == "Lehrer" and "student" in roles:
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.check_license_type_is_correct("dummyusername", user_roles, license_type)
        assert "License with special type 'Lehrer' can't be assigned to user" in str(excinfo.value)
    else:
        assignment_handler.check_license_type_is_correct("dummyusername", user_roles, license_type)