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
## desc: Test the assignment handler, i.e. changing the status of the licenses
## exposure: dangerous
## tags: [vbm]
## roles: [domaincontroller_master]

import datetime
import random

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.roles import get_role_info
from univention.bildungslogin.handlers import AssignmentHandler, BiloAssignmentError
from univention.bildungslogin.models import Assignment
from univention.bildungslogin.utils import Status


def license_was_assigned_correct_to_user(assignments, username):
    for a in assignments:
        assert type(a) is Assignment
        if a.assignee == username:
            assignment = a
            assert username == assignment.assignee
            assert Status.ASSIGNED == assignment.status
            assert assignment.time_of_assignment == datetime.datetime.now().strftime("%Y-%m-%d")
            break


@pytest.mark.parametrize("user_type", ["student", "teacher"])
def test_assign_user_to_license(assignment_handler, license_handler, license, user_type):
    # 00_vbm_test_assignments
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        if user_type == "student":
            username = schoolenv.create_student(ou)[0]
        elif user_type == "teacher":
            username = schoolenv.create_teacher(ou)[0]
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assignments = license_handler.get_assignments_for_license(license)
        license_was_assigned_correct_to_user(assignments, username)
        # (username, license_code) is unique
        with pytest.raises(BiloAssignmentError):
            assignment_handler.assign_to_license(username=username, license_code=license.license_code)


def test_check_license_can_be_assigned_to_school_user():
    AssignmentHandler.check_license_can_be_assigned_to_school_user(
        license_school="valid", ucsschool_schools=["valid"]
    )
    with pytest.raises(BiloAssignmentError):
        AssignmentHandler.check_license_can_be_assigned_to_school_user(
            license_school="invalid", ucsschool_schools=["valid"]
        )


def test_remove_assignment_from_users(assignment_handler, license_handler, license):
    # 00_vbm_test_assignments
    with utu.UCSTestSchool() as schoolenv:
        license.license_special_type = ""
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        n = random.randint(0, 10)
        usernames = [schoolenv.create_student(ou)[0] for _ in range(n)]
        usernames.append(schoolenv.create_teacher(ou)[0])
        assignment_handler.assign_users_to_license(
            usernames=usernames, license_code=license.license_code
        )
        assignments = license_handler.get_assignments_for_license(license)
        for username in usernames:
            license_was_assigned_correct_to_user(assignments, username)
        assignment_handler.remove_assignment_from_users(
            usernames=usernames, license_code=license.license_code
        )
        assignments = license_handler.get_assignments_for_license(license)
        assignees = [a.assignee for a in assignments]
        for username in usernames:
            assert username not in assignees


def test_assign_users_to_licenses(assignment_handler, license_handler, license):
    # 00_vbm_test_assignments
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        usernames = [schoolenv.create_student(ou)[0] for _ in range(license.license_quantity)]
        assignment_handler.assign_users_to_license(
            usernames=usernames, license_code=license.license_code
        )
        assignments = license_handler.get_assignments_for_license(license)
        for username in usernames:
            license_was_assigned_correct_to_user(assignments, username)


def test_get_assignments_for_product_id_for_user(license_handler, assignment_handler, license):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        username = schoolenv.create_student(ou)[0]
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assignments = assignment_handler.get_assignments_for_product_id_for_user(
            username=username, product_id=license.product_id
        )
        for a in assignments:
            print(a.assignee)
        assert len(assignments) == 1
        license_was_assigned_correct_to_user(assignments, username)


@pytest.mark.parametrize("user_type", ["student", "teacher"])
def test_positive_change_license_status(license_handler, assignment_handler, user_type, license):
    # positive test: test all valid status changes (+ if status was set correct)
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        if user_type == "student":
            username = schoolenv.create_student(ou)[0]
        elif user_type == "teacher":
            username = schoolenv.create_teacher(ou)[0]
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assignments = assignment_handler.get_assignments_for_product_id_for_user(
            username=username, product_id=license.product_id
        )
        assignment = assignments[0]
        assert assignment.status == Status.ASSIGNED
        assignment_handler.change_license_status(
            username=username,
            license_code=license.license_code,
            status=Status.AVAILABLE,
        )
        assignments = assignment_handler.get_assignments_for_product_id_for_user(
            username=username, product_id=license.product_id
        )
        assert len(assignments) == 0
        # license has to be reassigned to also have a username at the assignment
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assignment = assignment_handler.get_assignments_for_product_id_for_user(
            username=username, product_id=license.product_id
        )[0]
        assert assignment.status == Status.ASSIGNED
        assignment_handler.change_license_status(
            username=username,
            license_code=license.license_code,
            status=Status.PROVISIONED,
        )
        assignment = assignment_handler.get_assignments_for_product_id_for_user(
            username=username, product_id=license.product_id
        )[0]
        assert assignment.status == Status.PROVISIONED


@pytest.mark.parametrize("user_type", ["student", "teacher"])
def test_negative_change_license_status(license_handler, assignment_handler, user_type, license):
    # negative test: test all invalid status changes
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.license_school = ou
        license_handler.create(license)
        if user_type == "student":
            username = schoolenv.create_student(ou)[0]
        elif user_type == "teacher":
            username = schoolenv.create_teacher(ou)[0]
        # the status can only be changed for assignments which already have an assignee
        with pytest.raises(BiloAssignmentError):
            assignment_handler.change_license_status(
                username=username,
                license_code=license.license_code,
                status=Status.PROVISIONED,
            )
        assignment_handler.assign_to_license(username=username, license_code=license.license_code)
        assignment_handler.change_license_status(
            username=username,
            license_code=license.license_code,
            status=Status.PROVISIONED,
        )
        # license-assignments which have the status provisioned can't change their status.
        with pytest.raises(BiloAssignmentError):
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
    roles = [get_role_info(role)[0] for role in user_roles]
    if license_type == "Lehrer" and "student" in roles:
        with pytest.raises(BiloAssignmentError):
            assignment_handler.check_license_type_is_correct("dummyusername", user_roles, license_type)
    else:
        assignment_handler.check_license_type_is_correct("dummyusername", user_roles, license_type)
