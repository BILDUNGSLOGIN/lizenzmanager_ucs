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
## desc: Test the assignment handler, i.e. changing the status of the licenses
## exposure: dangerous
## tags: [bildungslogin]
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## packages: [python-bildungslogin, udm-bildungslogin-encoders]

import datetime
import enum
from typing import List

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
from univention.udm import UDM

from univention.bildungslogin.handlers import AssignmentHandler, BiloAssignmentError, \
    LicenseHandler, ObjectType
from univention.bildungslogin.models import Assignment, License, LicenseType, Status


def license_was_assigned_correct_to_object(assignments, object_uuid):
    count = 0
    for assignment in assignments:
        assert type(assignment) is Assignment
        if assignment.assignee == object_uuid:
            assert Status.ASSIGNED == assignment.status
            assert assignment.time_of_assignment == datetime.date.today()
            count += 1
    assert count == 1


def get_assignments_from_dn(assignment_handler, dn):  # type: (AssignmentHandler, str) -> Assignment
    udm_license = assignment_handler._assignments_mod.get(dn)
    return assignment_handler.from_udm_obj(udm_license)


def get_assignments_for_license(assignment_handler, license_handler, license):
    # type: (AssignmentHandler, LicenseHandler, License) -> List[Assignment]
    """helper function to search in udm layer"""
    udm_obj = license_handler.get_udm_license_by_code(license.license_code)
    assignment_dns = udm_obj.props.assignments
    return [get_assignments_from_dn(assignment_handler, dn) for dn in assignment_dns]


class AssignmentType(enum.Enum):
    SCHOOL = 1
    CLASS = 2
    WORKGROUP = 3
    USER = 4


_ASSIGNMENT_TYPE_TO_OBJECT_TYPE = {
    AssignmentType.USER: ObjectType.USER,
    AssignmentType.CLASS: ObjectType.GROUP,
    AssignmentType.WORKGROUP: ObjectType.GROUP,
    AssignmentType.SCHOOL: ObjectType.SCHOOL
}


@pytest.fixture
def create_environment_for_assignment_type(license_handler, get_license, hostname):
    """
    Create environment required for the selected assignment type:
        - 2 objects for the required assignment type
        - 1 license for the required assignment type (unless overridden)
    """
    def _func(schoolenv, assignment_type, license_type=None, license_props=None, custom_ou=None):
        if custom_ou is None:
            ou, _ = schoolenv.create_ou(name_edudc=hostname, use_cache=False)
        else:
            ou = custom_ou

        if assignment_type == AssignmentType.USER:
            obj1, _ = schoolenv.create_student(ou)
            obj2, _ = schoolenv.create_student(ou)
            if license_type is None:
                license_type = LicenseType.VOLUME
        elif assignment_type == AssignmentType.CLASS:
            obj1, _ = schoolenv.create_school_class(ou)
            obj2, _ = schoolenv.create_school_class(ou)
            if license_type is None:
                license_type = LicenseType.WORKGROUP
        elif assignment_type == AssignmentType.WORKGROUP:
            obj1, _ = schoolenv.create_workgroup(ou)
            obj2, _ = schoolenv.create_workgroup(ou)
            if license_type is None:
                license_type = LicenseType.WORKGROUP
        elif assignment_type == AssignmentType.SCHOOL:
            obj1 = ou
            obj2, _ = schoolenv.create_ou(name_edudc=hostname, use_cache=False)
            if license_type is None:
                license_type = LicenseType.SCHOOL
        else:
            raise NotImplementedError("Unknown assignment type: {}".format(assignment_type))

        license = get_license(ou, license_type=license_type)
        if license_props is not None:
            for prop, value in license_props.items():
                setattr(license, prop, value)
        license_handler.create(license)

        return obj1, obj2, license
    return _func


def test_get_user_by_username(assignment_handler, hostname):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        # Create user with the defined username
        username = "test"
        _, dn = schoolenv.create_student(ou, username=username)
        # Create the second user with random name to ensure the correct search
        schoolenv.create_student(ou)
        user = assignment_handler.get_user_by_username(username)
        assert user.dn == dn


def test_get_workgroup_by_name(assignment_handler, hostname):
    """ Check that a workgroup can be obtained by its name using the group search """
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        # Create group with the defined name
        # NOTE: Such format of the name is required by "create_workgroup"
        workgroup_name = "{}-test".format(ou)
        _, dn = schoolenv.create_workgroup(ou, workgroup_name=workgroup_name)
        # Create the second group with random name to ensure the correct search
        schoolenv.create_workgroup(ou)
        group = assignment_handler.get_group_by_name(workgroup_name)
        assert group.dn == dn


def test_get_class_by_name(assignment_handler, hostname):
    """ Check that a class can be obtained by its name using the group search """
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        # Create class-group with the defined name
        # NOTE: Such format of the name is required by "create_school_class"
        class_name = "{}-test".format(ou)
        _, dn = schoolenv.create_school_class(ou, class_name=class_name)
        # Create the second class with random name to ensure the correct search
        schoolenv.create_school_class(ou)
        group = assignment_handler.get_group_by_name(class_name)
        assert group.dn == dn


def test_get_school_by_name(assignment_handler, hostname, lo):
    """ Check that a school can be obtained by its name using the school search """
    with utu.UCSTestSchool() as schoolenv:
        # Create a school with the defined name
        school_name = "testou100"
        ou, dn = schoolenv.create_ou(ou_name=school_name, name_edudc=hostname, use_cache=False)
        # Create the second school with random name to ensure the correct search
        schoolenv.create_ou(name_edudc=hostname)
        # Create a container with the same name (but different position)
        udm = UDM(lo).version(1)
        mod = udm.get("container/ou")
        container = mod.new()
        container.props.name = school_name
        container.position = dn
        container.save()
        # Get school
        school = assignment_handler.get_school_by_name(school_name)
        # Check
        assert school.dn == dn


def test_get_school_users(assignment_handler, hostname):
    """ Check that a school can be obtained by its name using the school search """
    with utu.UCSTestSchool() as schoolenv:
        # Create a school with the defined name
        school_name = "testou101"
        ou1, _ = schoolenv.create_ou(ou_name=school_name, name_edudc=hostname, use_cache=False)
        # Create the second school with random name
        ou2, _ = schoolenv.create_ou(name_edudc=hostname)
        # Add users to school 1
        created_users_dns = set(dn for _, dn in (schoolenv.create_student(ou1),
                                                 schoolenv.create_student(ou1),
                                                 schoolenv.create_teacher(ou1),
                                                 schoolenv.create_teacher_and_staff(ou1),
                                                 schoolenv.create_staff(ou1)))
        assert len(created_users_dns) == 5
        school = assignment_handler.get_school_by_name(ou1)

        # Get and check users
        users = assignment_handler._get_school_users(school)
        assert len(users) == 5
        acquired_users_dns = set(u.dn for u in users)
        assert created_users_dns == acquired_users_dns

        # Add users to school 2
        schoolenv.create_student(ou2)
        schoolenv.create_teacher(ou2)

        # Check users for school 1 again to ensure that results were not affected
        users = assignment_handler._get_school_users(school)
        acquired_users_dns = set(u.dn for u in users)
        assert created_users_dns == acquired_users_dns


@pytest.mark.parametrize(
    "assignment_type,assigned_license_type",
    [
        (AssignmentType.SCHOOL, LicenseType.WORKGROUP),
        (AssignmentType.SCHOOL, LicenseType.SINGLE),
        (AssignmentType.SCHOOL, LicenseType.VOLUME),
        (AssignmentType.WORKGROUP, LicenseType.SINGLE),
        (AssignmentType.WORKGROUP, LicenseType.VOLUME),
        (AssignmentType.WORKGROUP, LicenseType.SCHOOL),
        (AssignmentType.CLASS, LicenseType.SINGLE),
        (AssignmentType.CLASS, LicenseType.VOLUME),
        (AssignmentType.CLASS, LicenseType.SCHOOL),
        (AssignmentType.USER, LicenseType.WORKGROUP),
        (AssignmentType.USER, LicenseType.SCHOOL),
    ]
)
def test_assigning_wrong_license_type(assignment_type, assigned_license_type, assignment_handler,
                                      license_handler, get_license,
                                      create_environment_for_assignment_type):
    """ Test that it is not possible to assign license of incorrect type """
    with utu.UCSTestSchool() as schoolenv:
        obj1, _, license = create_environment_for_assignment_type(schoolenv, assignment_type,
                                                                  license_type=assigned_license_type)
        udm_license = license_handler.get_udm_license_by_code(license.license_code)
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
        with pytest.raises(BiloAssignmentError) as context:
            assignment_handler.assign_license(udm_license, object_type, obj1)
        assert context.value.message.startswith("License with license type ")
        assert "can't be assigned to the object type" in context.value.message


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_assign_license_none_left(assignment_type, assignment_handler, license_handler,
                                  create_environment_for_assignment_type):
    """
    Tests that an exception is thrown if a license is assigned a user with no assignments left.
    The test is using "assign_license" method
    """
    with utu.UCSTestSchool() as schoolenv:
        if assignment_type is AssignmentType.USER:
            license_quantity = 1  # SINGLE/VOLUME licenses have 1 assignment per quantity
        else:
            license_quantity = 10  # GROUP/SCHOOL licenses have 1 assignment per license

        obj1, obj2, license = create_environment_for_assignment_type(
            schoolenv, assignment_type, license_props={"license_quantity": license_quantity})
        udm_license = license_handler.get_udm_license_by_code(license.license_code)
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]

        assignment_handler.assign_license(udm_license, object_type, obj1)
        with pytest.raises(BiloAssignmentError) as excinfo:
            if assignment_type == AssignmentType.SCHOOL:
                udm_license.props.school = obj2  # change license's school to test the logic
            assignment_handler.assign_license(udm_license, object_type, obj2)
        assert excinfo.value.message.startswith("There are no more assignments available")


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_assign_objects_to_licenses_none_left(assignment_type, assignment_handler, license_handler,
                                              create_environment_for_assignment_type):
    """
    Tests that an exception is thrown if a license is assigned a user with no assignments left.
    The test is using "assign_objects_to_licenses" method
    """
    with utu.UCSTestSchool() as schoolenv:
        if assignment_type is AssignmentType.USER:
            license_quantity = 1  # SINGLE/VOLUME licenses have 1 assignment per quantity
        else:
            license_quantity = 10  # GROUP/SCHOOL licenses have 1 assignment per license

        obj1, obj2, license = create_environment_for_assignment_type(
            schoolenv, assignment_type, license_props={"license_quantity": license_quantity})
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]

        result = assignment_handler.assign_objects_to_licenses([license.license_code],
                                                               object_type, [obj1])
        assert result["countSuccessfulAssignments"] == 1
        assert result["notEnoughLicenses"] is False

        result = assignment_handler.assign_objects_to_licenses([license.license_code],
                                                               object_type, [obj2])
        assert result["countSuccessfulAssignments"] == 0
        assert result["notEnoughLicenses"] is True


@pytest.fixture
def create_object_with_users_for_assignment(assignment_handler, license_handler,
                                            hostname, get_license, user_roles=None):
    """
    Creates school/workgroup/class with users assigned to it
    + a license with the respective type
    """
    def _func(schoolenv, assignment_type, license_props=None):
        # Create users and objects
        ou, _ = schoolenv.create_ou(name_edudc=hostname, use_cache=False)
        user1_name, user1_dn = schoolenv.create_student(ou)
        user2_name, user2_dn = schoolenv.create_student(ou)

        if assignment_type == AssignmentType.CLASS:
            object_name, _ = schoolenv.create_school_class(ou, users=[user1_dn, user2_dn])
            license_type = LicenseType.WORKGROUP
        elif assignment_type == AssignmentType.WORKGROUP:
            object_name, _ = schoolenv.create_workgroup(ou, users=[user1_dn, user2_dn])
            license_type = LicenseType.WORKGROUP
        elif assignment_type == AssignmentType.SCHOOL:
            object_name = ou
            license_type = LicenseType.SCHOOL
        else:
            raise RuntimeError
        # Create license
        license = get_license(ou, license_type=license_type)
        if license_props is not None:
            for prop, value in license_props.items():
                setattr(license, prop, value)
        license_handler.create(license)
        udm_license = license_handler.get_udm_license_by_code(license.license_code)
        return object_name, udm_license
    return _func


@pytest.mark.parametrize("assignment_type", [AssignmentType.SCHOOL,
                                             AssignmentType.CLASS,
                                             AssignmentType.WORKGROUP])
def test_assign_license_quantity_failure(assignment_type, assignment_handler,
                                         create_object_with_users_for_assignment):
    """ Tests that quantity of the license must not exceed number of users in school/group """
    with utu.UCSTestSchool() as schoolenv:
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
        object_name, udm_license = \
            create_object_with_users_for_assignment(schoolenv, assignment_type,
                                                    license_props={"license_quantity": 1})
        if assignment_type == AssignmentType.CLASS:
            expected_message = "This license is allowed for assignments to groups including a " \
                               "maximum of <1> members. " \
                               "Please modify your group selection accordingly"
        elif assignment_type == AssignmentType.WORKGROUP:
            expected_message = "This license is allowed for assignments to groups including a " \
                               "maximum of <1> members. "  \
                               "Please modify your group selection accordingly"
        elif assignment_type == AssignmentType.SCHOOL:
            expected_message = "This license is allowed for assignments to schools including a " \
                               "maximum of <1> members. Please modify your school " \
                               "selection accordingly"
        else:
            raise RuntimeError

        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.assign_license(udm_license, object_type, object_name)
        assert excinfo.value.message == expected_message


@pytest.mark.parametrize("assignment_type", [AssignmentType.SCHOOL,
                                             AssignmentType.CLASS,
                                             AssignmentType.WORKGROUP])
def test_assign_license_infinite_quantity(assignment_type, assignment_handler,
                                          create_object_with_users_for_assignment):
    """ Tests that quantity of the license must not exceed number of users in school/group """
    with utu.UCSTestSchool() as schoolenv:
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
        object_name, udm_license = \
            create_object_with_users_for_assignment(schoolenv, assignment_type,
                                                    license_props={"license_quantity": 0})
        assignment_handler.assign_license(udm_license, object_type, object_name)
        # re-fetch udm_license
        udm_license = assignment_handler.get_license_by_license_code(udm_license.props.code)
        assignments = [get_assignments_from_dn(assignment_handler, dn)
                       for dn in udm_license.props.assignments]
        object_uuid = assignment_handler._get_object_uuid_by_name(object_type, object_name)
        license_was_assigned_correct_to_object(assignments, object_uuid)


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_assign_object_to_license(assignment_type, assignment_handler, license_handler,
                                  create_environment_for_assignment_type):
    """Test that a license can be assigned to a user"""
    object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
    with utu.UCSTestSchool() as schoolenv:
        object_name, _, license = create_environment_for_assignment_type(schoolenv, assignment_type)
        udm_license = license_handler.get_udm_license_by_code(license.license_code)
        success = assignment_handler.assign_license(
            object_type=object_type,
            object_name=object_name,
            license=udm_license)
        assert success is True
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        # check assignments
        object_uuid = assignment_handler._get_object_uuid_by_name(object_type, object_name)
        license_was_assigned_correct_to_object(assignments, object_uuid)
        # (object_name, license_code) is unique
        success2 = assignment_handler.assign_license(
            object_type=object_type,
            object_name=object_name,
            license=udm_license)
        assert success2 is True
        license_was_assigned_correct_to_object(assignments, object_uuid)


@pytest.mark.parametrize("ignored", [True, False])
def test_check_is_ignored(ignored, mock):
    """Test that a license can not be used if the ignore flag is set"""
    mock_license = mock.Mock(**{"props.ignored": ignored})
    if ignored:
        with pytest.raises(BiloAssignmentError) as excinfo:
            AssignmentHandler._check_license_is_ignored(mock_license)
        assert "License is 'ignored for display' and thus can't be assigned!" in str(excinfo.value)
    else:
        AssignmentHandler._check_license_is_ignored(mock_license)


@pytest.mark.parametrize("expired", [True, False])
def test_check_is_expired(expired, mock):
    """Test that a license can not be used if the ignore flag is set"""
    mock_license = mock.Mock(**{"props.expired": expired})
    if expired:
        with pytest.raises(BiloAssignmentError) as excinfo:
            AssignmentHandler._check_license_is_expired(mock_license)
        assert "License is expired and thus can't be assigned!" in str(excinfo.value)
    else:
        AssignmentHandler._check_license_is_expired(mock_license)


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_assign_object_to_expired_license_fails(assignment_type,
                                                assignment_handler, license_handler,
                                                create_environment_for_assignment_type):
    """Test that a license can not be assigned if the license is expired"""
    with utu.UCSTestSchool() as schoolenv:
        validity_end_date = datetime.date.today() - datetime.timedelta(days=1)
        object_name, _, license = create_environment_for_assignment_type(
            schoolenv, assignment_type, license_props={"validity_end_date": validity_end_date})
        udm_license = license_handler.get_udm_license_by_code(license.license_code)
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
        with pytest.raises(BiloAssignmentError, match="License is expired") as excinfo:
            assignment_handler.assign_license(object_type=object_type,
                                              object_name=object_name,
                                              license=udm_license)
        assert "License is expired" in str(excinfo.value)


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_assign_object_to_ignored_license_fails(assignment_type,
                                                assignment_handler, license_handler,
                                                create_environment_for_assignment_type):
    """Test that a license can not be assigned if the ignore flag is set"""
    with utu.UCSTestSchool() as schoolenv:
        object_name, _, license = create_environment_for_assignment_type(
            schoolenv, assignment_type, license_props={"ignored_for_display": True})
        udm_license = license_handler.get_udm_license_by_code(license.license_code)
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.assign_license(object_type=object_type,
                                              object_name=object_name,
                                              license=udm_license)
        assert "License is 'ignored for display' and thus can't be assigned!" in str(excinfo.value)


# TODO: Add similar tests for group/school
@pytest.mark.parametrize(
    "license_school,ucsschool_school",
    [("demoschool", "demoschool"), ("demOSchool", "DEMOSCHOOL"), ("demoschool", "demoschool2")],
)
def test_check_license_can_be_assigned_to_school_user(license_school, ucsschool_school, mock):
    """Test that a license associated to a school can not be assigned to a user of a different school"""
    mock_user = mock.Mock(**{"props.school": [ucsschool_school]})
    mock_license = mock.Mock(**{"props.school": license_school})
    if license_school.lower() == ucsschool_school.lower():
        AssignmentHandler._check_license_school_against_user(mock_license, mock_user)
    else:
        with pytest.raises(BiloAssignmentError) as excinfo:
            AssignmentHandler._check_license_school_against_user(mock_license, mock_user)
        assert "License can't be assigned to user in school" in str(excinfo.value)


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_assign_objects_to_licenses(assignment_type, assignment_handler, license_handler,
                                    create_environment_for_assignment_type):
    """Test that a license can be assigned to a user with status ASSIGNED"""
    object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
    with utu.UCSTestSchool() as schoolenv:
        # prepare data
        obj1, obj2, license = create_environment_for_assignment_type(
            schoolenv, assignment_type, license_props={"license_quantity": 2})
        if assignment_type is AssignmentType.USER:
            object_names = [obj1, obj2]
        else:
            object_names = [obj1]  # schools/groups can only be assigned once
        # assign
        assignment_handler.assign_objects_to_licenses(
            object_type=object_type,
            object_names=object_names,
            license_codes=[license.license_code])
        # check
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        for object_name in object_names:
            object_uuid = assignment_handler._get_object_uuid_by_name(object_type, object_name)
            license_was_assigned_correct_to_object(assignments, object_uuid)


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_remove_assignment_from_objects(assignment_type, assignment_handler, license_handler,
                                        create_environment_for_assignment_type):
    """Test that license assignment can be removed from an object"""
    object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
    with utu.UCSTestSchool() as schoolenv:
        obj1, obj2, license = create_environment_for_assignment_type(
            schoolenv, assignment_type, license_props={"license_quantity": 3})
        if assignment_type is AssignmentType.USER:
            object_names = [obj1, obj2]
        else:
            object_names = [obj1]  # schools/groups can only be assigned once
        # assign
        assignment_handler.assign_objects_to_licenses(
            object_type=object_type,
            object_names=object_names,
            license_codes=[license.license_code])
        # check
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        object_uuids = [assignment_handler._get_object_uuid_by_name(object_type, on)
                        for on in object_names]
        for object_uuid in object_uuids:
            license_was_assigned_correct_to_object(assignments, object_uuid)
        failed_assignments = \
            assignment_handler.remove_assignment_from_objects(license_code=license.license_code,
                                                              object_type=object_type,
                                                              object_names=object_names)
        assert len(failed_assignments) == 0
        assignments = get_assignments_for_license(assignment_handler, license_handler, license)
        assignees = [a.assignee for a in assignments]
        for object_uuid in object_uuids:
            assert object_uuid not in assignees


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_no_change_change_license_status(assignment_type, license_handler, assignment_handler,
                                         create_environment_for_assignment_type):
    with utu.UCSTestSchool() as schoolenv:
        object_name, _, license = create_environment_for_assignment_type(schoolenv, assignment_type)
        object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
        assert assignment_handler.change_license_status(license.license_code, object_type,
                                                        object_name, Status.ASSIGNED) is True
        assert assignment_handler.change_license_status(license.license_code, object_type,
                                                        object_name, Status.PROVISIONED) is True
        assert assignment_handler.change_license_status(license.license_code, object_type,
                                                        object_name, Status.PROVISIONED) is False


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_positive_change_license_status(assignment_type, license_handler, assignment_handler,
                                        create_environment_for_assignment_type):
    """Positive test: test all valid status changes (+ if status was set correct)"""
    object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
    with utu.UCSTestSchool() as schoolenv:
        object_name, _, license = create_environment_for_assignment_type(schoolenv, assignment_type)
        udm_license = license_handler.get_udm_license_by_code(license.license_code)

        # assign
        success = assignment_handler.assign_license(object_type=object_type,
                                                 object_name=object_name,
                                                 license=udm_license)
        assert success is True
        object_uuid = assignment_handler._get_object_uuid_by_name(object_type, object_name)
        [assignment] = assignment_handler.get_all_assignments_for_uuid(
            assignee_uuid=object_uuid, base=udm_license.dn)
        assert assignment.status == Status.ASSIGNED

        # change 1: ASSIGNED -> AVAILABLE
        success = assignment_handler.change_license_status(license_code=license.license_code,
                                                           object_type=object_type,
                                                           object_name=object_name,
                                                           status=Status.AVAILABLE)
        assert success is True
        assignments = assignment_handler.get_all_assignments_for_uuid(
            assignee_uuid=object_uuid, base=udm_license.dn)
        assert len(assignments) == 0

        # reassign
        success = assignment_handler.assign_license(object_type=object_type,
                                                    object_name=object_name,
                                                    license=udm_license)
        assert success is True

        [assignment] = assignment_handler.get_all_assignments_for_uuid(
            assignee_uuid=object_uuid, base=udm_license.dn)
        assert assignment.status == Status.ASSIGNED

        # change 2: ASSIGNED -> PROVISIONED
        success = assignment_handler.change_license_status(license_code=license.license_code,
                                                           object_type=object_type,
                                                           object_name=object_name,
                                                           status=Status.PROVISIONED)
        assert success is True
        [assignment] = assignment_handler.get_all_assignments_for_uuid(
            assignee_uuid=object_uuid, base=udm_license.dn)
        assert assignment.status == Status.PROVISIONED


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_negative_change_license_status(assignment_type, license_handler, assignment_handler,
                                        create_environment_for_assignment_type):
    """Negative test: test all invalid status changes"""
    object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
    with utu.UCSTestSchool() as schoolenv:
        object_name, _, license = create_environment_for_assignment_type(schoolenv, assignment_type)
        udm_license = license_handler.get_udm_license_by_code(license.license_code)

        # the status can only be changed for assignments which already have an assignee
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.change_license_status(license_code=license.license_code,
                                                     object_type=object_type,
                                                     object_name=object_name,
                                                     status=Status.PROVISIONED)
        assert "No assignment for license with" in str(excinfo.value)

        # assign the license and set its status to "provisioned"
        assignment_handler.assign_license(object_type=object_type,
                                          object_name=object_name,
                                          license=udm_license)
        assignment_handler.change_license_status(license_code=license.license_code,
                                                 object_type=object_type,
                                                 object_name=object_name,
                                                 status=Status.PROVISIONED)

        # license-assignments which have the status provisioned can't change their status.
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.change_license_status(license_code=license.license_code,
                                                     object_type=object_type,
                                                     object_name=object_name,
                                                     status=Status.AVAILABLE)
        assert "Invalid status transition from PROVISIONED to AVAILABLE." in str(excinfo.value)


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
@pytest.mark.parametrize(
    "user_roles",
    [
        ("student:school:demoschool",),
        ("teacher:school:demoschool",),
        ("teacher:school:demoschool", "staff:school:demoschool"),
    ],
)
@pytest.mark.parametrize("license_type", ["Lehrkraft", "Demo", ""])
def test_check_license_type_is_correct(assignment_type, user_roles, license_type,
                                       assignment_handler, mock):
    """Test that a license with string type "Lehrkraft" can not be assigned to a student"""
    mock_user = mock.Mock(**{"props.ucsschoolRole": user_roles, "props.username": "dummyusername"})
    mock_license = mock.Mock(**{"props.special_type": license_type})
    if license_type == "Lehrkraft" and any(r.startswith("student") for r in user_roles):
        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler._check_license_special_type_against_user(mock_license, mock_user)
        assert "License with special type 'Lehrkraft' can't be assigned to user" in str(excinfo.value)
    else:
        assignment_handler._check_license_special_type_against_user(mock_license, mock_user)


@pytest.mark.parametrize("assignment_type", [AssignmentType.SCHOOL,
                                             AssignmentType.CLASS,
                                             AssignmentType.WORKGROUP])
@pytest.mark.parametrize("user1_is_teacher", [True, False])
@pytest.mark.parametrize("user2_is_teacher", [True, False])
@pytest.mark.parametrize("special_type", ["Lehrkraft", "Demo", ""])
def test_assign_license_with_special_type(assignment_type, user1_is_teacher, user2_is_teacher,
                                          special_type, license_handler, assignment_handler,
                                          hostname, get_license):
    object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname, use_cache=False)
        # Create users
        user1_name, user1_dn = schoolenv.create_user(ou, is_teacher=user1_is_teacher)
        user2_name, user2_dn = schoolenv.create_user(ou, is_teacher=user2_is_teacher)

        # Create objects
        if assignment_type == AssignmentType.CLASS:
            object_name, _ = schoolenv.create_school_class(ou, users=[user1_dn, user2_dn])
            license_type = LicenseType.WORKGROUP
        elif assignment_type == AssignmentType.WORKGROUP:
            object_name, _ = schoolenv.create_workgroup(ou, users=[user1_dn, user2_dn])
            license_type = LicenseType.WORKGROUP
        elif assignment_type == AssignmentType.SCHOOL:
            object_name = ou
            license_type = LicenseType.SCHOOL
        else:
            raise RuntimeError

        # Create license
        license = get_license(ou, license_type=license_type)
        license.license_special_type = special_type
        license.license_quantity = 3
        license_handler.create(license)
        udm_license = license_handler.get_udm_license_by_code(license.license_code)

        # Try to assign
        # NOTE: special type check doesn't apply to school licenses,
        # rather students should be filtered out later when querying
        if assignment_type is not AssignmentType.SCHOOL and special_type == "Lehrkraft" \
                and not (user1_is_teacher and user2_is_teacher):
            # if not all the users are teachers for the special type Lehrkraft
            with pytest.raises(BiloAssignmentError) as excinfo:
                assignment_handler.assign_license(udm_license, object_type, object_name)
            assert excinfo.value.message.startswith(
                "This license is allowed for assignments to groups including only teachers")
        else:
            assignment_handler.assign_license(udm_license, object_type, object_name)
            assignments = [get_assignments_from_dn(assignment_handler, dn)
                           for dn in udm_license.props.assignments]
            object_uuid = assignment_handler._get_object_uuid_by_name(object_type, object_name)
            license_was_assigned_correct_to_object(assignments, object_uuid)


@pytest.mark.parametrize("assignment_type", [t for t in AssignmentType])
def test_assign_license_wrong_school(assignment_type, assignment_handler, hostname,
                                     create_environment_for_assignment_type):
    object_type = _ASSIGNMENT_TYPE_TO_OBJECT_TYPE[assignment_type]
    with utu.UCSTestSchool() as schoolenv:
        ou1_object_name, _, _ = create_environment_for_assignment_type(schoolenv, assignment_type)
        ou2, _ = schoolenv.create_ou(ou_name="testou102", name_edudc=hostname, use_cache=False)
        _, _, ou2_license = create_environment_for_assignment_type(schoolenv, assignment_type,
                                                                   custom_ou=ou2)
        ou2_udm_license = assignment_handler.get_license_by_license_code(ou2_license.license_code)

        if assignment_type is AssignmentType.USER:
            expected_message = "License can't be assigned to user in schools"
        elif assignment_type in [AssignmentType.WORKGROUP, AssignmentType.CLASS]:
            expected_message = "license can't be assigned to group " \
                               "as it doesn't belong to the same school"
        elif assignment_type is AssignmentType.SCHOOL:
            expected_message = "License can't be assigned to a different school"
        else:
            raise RuntimeError

        with pytest.raises(BiloAssignmentError) as excinfo:
            assignment_handler.assign_license(ou2_udm_license, object_type, ou1_object_name)
        assert excinfo.value.message.startswith(expected_message)
