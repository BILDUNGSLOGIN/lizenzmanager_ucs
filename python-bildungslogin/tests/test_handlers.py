# -*- coding: utf-8 -*-
import datetime
import random
import sys
import uuid
from hashlib import sha256
from typing import Dict, Tuple

import pytest

import univention.bildungslogin.handlers
from univention.bildungslogin.exceptions import BiloAssignmentError, BiloLicenseNotFoundError
from univention.bildungslogin.handlers import ObjectType
from univention.bildungslogin.models import Assignment, License, MetaData, Status

if sys.version_info[0] >= 3:
    from unittest.mock import MagicMock, Mock, call, patch
else:
    from mock import MagicMock, Mock, call, patch

try:
    from univention.udm.base import BaseObject, BaseObjectProperties
except ImportError:

    class BaseObject(object):
        def __init__(self):
            self.dn = ""
            self.props = None
            self.options = []
            self.policies = []
            self.position = ""
            self.superordinate = None
            self._udm_module = None

    class BaseObjectProperties(object):
        def __init__(self, udm_obj):
            self._udm_obj = udm_obj


@pytest.fixture
def unsaved_udm_object():
    def _func():  # type: () -> BaseObject
        obj = BaseObject()
        obj.position = "dc=example,dc=com"
        obj.dn = "cn=foo,{}".format(obj.position)
        obj.props = BaseObjectProperties(obj)
        obj.options = []
        obj.policies = []
        obj.superordinate = obj.position
        return obj

    return _func


@pytest.fixture
def fake_udm_assignment_object(unsaved_udm_object):
    def _func(license_dn):  # type: (str) -> BaseObject
        obj = unsaved_udm_object()  # type: BaseObject
        obj.position = license_dn
        obj.superordinate = obj.position
        obj.props.assignee = None
        obj.props.cn = str(uuid.uuid4())
        obj.dn = "cn={},{}".format(obj.props.cn, obj.position)
        obj.props.status = "AVAILABLE"
        obj.props.time_of_assignment = None
        return obj

    return _func


@pytest.fixture
def fake_udm_license_object(unsaved_udm_object):
    def _func():  # type: () -> BaseObject
        obj = unsaved_udm_object()  # type: BaseObject
        obj.position = "cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=example,dc=com"
        obj.superordinate = obj.position
        obj.props.code = "ABC-{!s}".format(uuid.uuid4())
        obj.props.cn = sha256(obj.props.code).hexdigest()
        obj.dn = "cn={},{}".format(obj.props.cn, obj.position)
        obj.props.assignments = []
        obj.props.delivery_date = datetime.date(2021, 1, 1)
        obj.props.expired = False
        obj.props.ignored = False
        obj.props.num_assigned = 0
        obj.props.num_available = 0
        obj.props.num_expired = 0
        obj.props.product_id = "urn:bilo:medium:A0001#01-02-TZ"
        obj.props.provider = "ABC"
        obj.props.purchasing_reference = "2001-01-01T11:12:13 -02:00 010203"
        obj.props.quantity = 0
        obj.props.school = "DEMOSCHOOL"
        obj.props.special_type = None
        obj.props.utilization_systems = ""
        obj.props.validity_start_date = None
        obj.props.validity_end_date = None
        obj.props.validity_duration = None
        obj.props.license_type = "VOLUME"
        return obj

    return _func


@pytest.fixture
def license_with_assignments(fake_udm_assignment_object, fake_udm_license_object, random_username):
    def _func(assignment_total, assignment_available, license_props=None):
        # type: (int, int) -> Tuple[BaseObject, Dict[str, BaseObject]]
        license = fake_udm_license_object()  # type: BaseObject
        license.props.quantity = assignment_total
        license.props.num_available = assignment_available
        license.props.num_assigned = assignment_total - assignment_available
        if license_props:
            for attr, value in license_props.items():
                setattr(license.props, attr, value)
        assignments = {}
        for _ in range(assignment_total - assignment_available):
            ass_obj = fake_udm_assignment_object(license.dn)
            ass_obj.props.status = "ASSIGNED"
            ass_obj.props.assignee = random_username()
            license.props.assignments.append(ass_obj.dn)
            assignments[ass_obj.dn] = ass_obj
        for _ in range(assignment_available):
            ass_obj = fake_udm_assignment_object(license.dn)
            license.props.assignments.append(ass_obj.dn)
            assignments[ass_obj.dn] = ass_obj
        random.shuffle(license.props.assignments)
        return license, assignments

    return _func


@pytest.mark.parametrize("object_type", [ObjectType.USER, ObjectType.SCHOOL, ObjectType.GROUP])
@patch("univention.bildungslogin.handlers.UDM")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "get_license_by_license_code")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "assign_license")
def test_assign_users_to_licenses_enough_licenses(
    assign_license_mock,
    get_license_by_license_code_mock,
    udm_mock,
    object_type,
    license_with_assignments,
    random_username,
):
    """Test that licenses are used in order of soonest validity_end_date."""
    # 3 available license assignments
    assignment_available1 = 3
    assignment_total1 = random.randint(assignment_available1 + 1, assignment_available1 + 10)
    license1, assignments1 = license_with_assignments(assignment_total1, assignment_available1)
    license1.props.validity_start_date = datetime.date(2000, 1, 1)
    license1.props.validity_end_date = datetime.date(2040, 1, 1)

    # 0 available:
    assignment_available2 = 0
    assignment_total2 = random.randint(assignment_available2 + 1, assignment_available2 + 10)
    license2, assignments2 = license_with_assignments(assignment_total2, assignment_available2)
    license2.props.validity_start_date = datetime.date(2000, 1, 1)
    license2.props.validity_end_date = datetime.date(2025, 1, 1)

    # 10 available, must be used last (validity end furthest away):
    assignment_available3 = 10
    assignment_total3 = random.randint(assignment_available3 + 1, assignment_available3 + 10)
    license3, assignments3 = license_with_assignments(assignment_total3, assignment_available3)
    license3.props.validity_start_date = datetime.date(2000, 1, 1)
    license3.props.validity_end_date = datetime.date(2050, 1, 1)

    # 1 available, must be used first (validity end nearest (today)):
    assignment_available4 = 1
    assignment_total4 = random.randint(assignment_available4 + 1, assignment_available4 + 10)
    license4, assignments4 = license_with_assignments(assignment_total4, assignment_available4)
    license4.props.validity_start_date = datetime.date(2000, 1, 1)
    license4.props.validity_end_date = datetime.date.today()

    licenses = {license.props.code: license for license in (license1, license2, license3, license4)}
    get_license_by_license_code_mock.side_effect = lambda x: licenses[x]

    # More usernames than in 1 + 2 + 4, but not more than total. So we'll use all assignments from 1, 2
    # and 4, and a few from 3.
    total_available = (
        assignment_available1 + assignment_available2 + assignment_available3 + assignment_available4
    )
    num_users = random.randint(
        assignment_available1 + assignment_available2 + assignment_available4 + 2,
        total_available - 2,
    )
    usernames = [random_username() for _ in range(num_users)]

    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    result = ah.assign_objects_to_licenses(
        [lic.props.code for lic in (license1, license2, license3, license4)],
        object_type,
        usernames
    )

    # sorted by validity end:
    used_licenses = (
        [license4 for _ in range(assignment_available4)]
        + [license1 for _ in range(assignment_available1)]
        + [license2 for _ in range(assignment_available2)]
        + [license3 for _ in range(assignment_available3)]
    )
    # zip() will drop unused list items from used_licenses_codes (from license3):
    calls_to_assign_license = [call(l_c, object_type, u_n)
                                  for l_c, u_n in zip(used_licenses, usernames)]
    assert assign_license_mock.call_args_list == calls_to_assign_license
    assert result == {
        "countSuccessfulAssignments": len(usernames),
        "notEnoughLicenses": False,
        "failedAssignments": [],
        "validityInFuture": [],
    }


@patch("univention.bildungslogin.handlers.UDM")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "get_license_by_license_code")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "assign_license")
def test_assign_users_to_licenses_warning_expired_license(
    assign_license_mock,
    get_license_by_license_code_mock,
    udm_mock,
    license_with_assignments,
    random_username,
):
    """Test that assigning a license that has expired produces a warning."""

    # validity_end_date in the past (->warning):
    assignment_available1 = random.randint(2, 10)
    assignment_total1 = random.randint(assignment_available1 + 1, assignment_available1 + 10)
    license1, assignments1 = license_with_assignments(assignment_total1, assignment_available1)
    license1.props.validity_start_date = datetime.date(2000, 1, 1)
    license1.props.validity_end_date = datetime.date(2001, 1, 1)
    # fake UDM object will not do this on its own:
    license1.props.expired = True
    license1.props.num_expired = assignment_total1

    # this license will not produce a warning:
    assignment_available2 = random.randint(2, 10)
    assignment_total2 = random.randint(assignment_available2 + 1, assignment_available2 + 10)
    license2, assignments2 = license_with_assignments(assignment_total2, assignment_available2)
    license2.props.validity_start_date = datetime.date(2000, 1, 1)
    license2.props.validity_end_date = datetime.date(2025, 1, 1)

    licenses = {license.props.code: license for license in (license1, license2)}
    get_license_by_license_code_mock.side_effect = lambda x: licenses[x]

    num_users = assignment_available2 - 1
    usernames = [random_username() for _ in range(num_users)]

    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    result = ah.assign_objects_to_licenses([license1.props.code, license2.props.code],
                                           ObjectType.USER, usernames)

    assert result == {
        "countSuccessfulAssignments": num_users,
        "notEnoughLicenses": False,
        "failedAssignments": [],
        "validityInFuture": [],
    }


@patch("univention.bildungslogin.handlers.UDM")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "get_license_by_license_code")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "assign_license")
def test_assign_users_to_licenses_warning_validity_starts_in_the_future(
    assign_license_mock,
    get_license_by_license_code_mock,
    udm_mock,
    license_with_assignments,
    random_username,
):
    """Test that assigning a license with a validity_start_date in the future produces a warning."""
    assignment_available1 = random.randint(2, 10)
    assignment_total1 = random.randint(assignment_available1 + 1, assignment_available1 + 10)
    license1, assignments1 = license_with_assignments(assignment_total1, assignment_available1)
    # validity_start_date in the future (->warning)
    license1.props.validity_start_date = datetime.date(2030, 1, 1)
    license1.props.validity_end_date = datetime.date(2040, 1, 1)

    # this license will not produce a warning:
    assignment_available2 = random.randint(2, 10)
    assignment_total2 = random.randint(assignment_available2 + 1, assignment_available2 + 10)
    license2, assignments2 = license_with_assignments(assignment_total2, assignment_available2)
    license2.props.validity_start_date = datetime.date(2000, 1, 1)
    license2.props.validity_end_date = datetime.date(2040, 1, 1)

    licenses = {license.props.code: license for license in (license1, license2)}
    get_license_by_license_code_mock.side_effect = lambda x: licenses[x]

    num_users = assignment_available1 + assignment_available2 - 1
    usernames = [random_username() for _ in range(num_users)]

    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    result = ah.assign_objects_to_licenses([license1.props.code, license2.props.code],
                                           ObjectType.USER, usernames)

    assert result == {
        "countSuccessfulAssignments": num_users,
        "notEnoughLicenses": False,
        "failedAssignments": [],
        "validityInFuture": [license1.props.code],
    }


@patch("univention.bildungslogin.handlers.UDM")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "get_license_by_license_code")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "assign_license")
def test_assign_users_to_licenses_not_enough_licenses(
    assign_license_mock,
    get_license_by_license_code_mock,
    udm_mock,
    license_with_assignments,
    random_username,
):
    """Test that with to few licenses, no license gets assigned and an error message is in the result."""
    assignment_available1 = random.randint(2, 10)
    assignment_total1 = random.randint(assignment_available1 + 1, assignment_available1 + 10)
    license1, assignments1 = license_with_assignments(assignment_total1, assignment_available1)
    license1.props.validity_start_date = datetime.date(2000, 1, 1)
    license1.props.validity_end_date = datetime.date(2040, 1, 1)

    get_license_by_license_code_mock.side_effect = lambda x: license1

    num_users = assignment_available1 + 1
    usernames = [random_username() for _ in range(num_users)]

    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    result = ah.assign_objects_to_licenses([license1.props.code], ObjectType.USER, usernames)

    assert assign_license_mock.call_args_list == []
    assert result == {
        "countSuccessfulAssignments": 0,
        "notEnoughLicenses": True,
        "failedAssignments": [],
        "validityInFuture": [],
    }

@patch("univention.bildungslogin.handlers.UDM", MagicMock())
@patch.object(univention.bildungslogin.handlers.LicenseHandler,
              "get_assignments_for_license_with_filter")
def test_get_assigned_users_from_user_license(get_assignments_mock, license_with_assignments):
    """
    Test that verifies the generation of the correct assigned
    users dictionary for user licenses.
    """
    udm_license, assignments = \
        license_with_assignments(1, 0, license_props={"license_type": "SINGLE"})
    license = univention.bildungslogin.handlers.LicenseHandler.from_udm_obj(udm_license)
    assignment_object = Assignment(
        assignee="TESTUSER",
        license="CODE",
        time_of_assignment=datetime.date.today(),
        status=Status.ASSIGNED,
    )
    get_assignments_mock.return_value = [assignment_object]
    lh = univention.bildungslogin.handlers.LicenseHandler(Mock())
    with patch.object(lh, "_users_mod") as users_mod_mock:
        udm_user = Mock()
        udm_user.props.username = "TESTUSER"
        users_mod_mock.search.return_value = (value for value in (udm_user,))
        result = lh.get_assigned_users(license)
    # assert result == [
    #     {
    #         "username": assignment_object.assignee,
    #         "status": assignment_object.status,
    #         "statusLabel": Status.label(assignment_object.status),
    #         "dateOfAssignment": assignment_object.time_of_assignment,
    #     }
    # ]


@patch("univention.bildungslogin.handlers.UDM", MagicMock())
@patch.object(univention.bildungslogin.handlers.LicenseHandler,
              "get_assignments_for_license_with_filter")
def test_get_assigned_users_from_group_license(get_assignments_mock, license_with_assignments):
    """
    Test that verifies the generation of the correct assigned
    users dictionary for group licenses.
    """
    udm_license, assignments = \
        license_with_assignments(1, 0, license_props={"license_type": "WORKGROUP"})
    license = univention.bildungslogin.handlers.LicenseHandler.from_udm_obj(udm_license)
    assignment_object = Assignment(
        assignee="TEST GROUP",
        license="CODE",
        time_of_assignment=datetime.date.today(),
        status=Status.ASSIGNED,
    )
    get_assignments_mock.return_value = [assignment_object]
    lh = univention.bildungslogin.handlers.LicenseHandler(Mock())
    udm_user = Mock(**{"props.username": "TEST USER"})
    udm_group = Mock(**{"props.users.objs": (u for u in (udm_user,))})
    with patch.object(lh, "_groups_mod") as groups_mod_mock:
        groups_mod_mock.search.return_value = (g for g in (udm_group,))
        result = lh.get_assigned_users(license)
    # assert result == [
    #     {
    #         "username": udm_user.props.username,
    #         "status": assignment_object.status,
    #         "statusLabel": "Assigned",
    #         "dateOfAssignment": assignment_object.time_of_assignment,
    #     }
    # ]

@patch("univention.bildungslogin.handlers.UDM", MagicMock())
@patch.object(univention.bildungslogin.handlers.LicenseHandler,
              "get_assignments_for_license_with_filter")
def test_get_assigned_users_from_school_license(get_assignments_mock, license_with_assignments):
    """
    Test that verifies the generation of the correct assigned
    users dictionary for school licenses.
    """
    udm_license, assignments = \
        license_with_assignments(1, 0, license_props={"license_type": "SCHOOL",
                                                      "special_type": "Lehrkraft"})
    license = univention.bildungslogin.handlers.LicenseHandler.from_udm_obj(udm_license)
    assignment_object = Assignment(
        assignee="TEST SCHOOL",
        license="CODE",
        time_of_assignment=datetime.date.today(),
        status=Status.ASSIGNED,
    )
    get_assignments_mock.return_value = [assignment_object]
    lh = univention.bildungslogin.handlers.LicenseHandler(Mock())
    udm_student = Mock(**{"props.username": "TEST STUDENT",
                          "props.ucsschoolRole": ["student:school:smth"]})
    udm_teacher = Mock(**{"props.username": "TEST TEACHER",
                          "props.ucsschoolRole": ["teacher:school:smth"]})
    udm_school = Mock(**{"props.name": "SCHOOL NAME"})
    with patch.object(lh, "_schools_mod") as schools_mod_mock, \
            patch.object(lh, "_users_mod") as users_mod_mock:
        schools_mod_mock.search.return_value = (s for s in (udm_school,))
        users_mod_mock.search.return_value = (u for u in (udm_student, udm_teacher))
        result = lh.get_assigned_users(license)
    result[0].pop("roles", None)
    assert result == [
        {
            "username": udm_teacher.props.username,
            "status": assignment_object.status,
            "statusLabel": "Assigned",
            "dateOfAssignment": assignment_object.time_of_assignment,
        }
    ]


@patch("univention.bildungslogin.handlers.UDM")
def test_get_udm_license_by_code_index_error(_udm_mock):
    """Tests that get_udm_license_by_code raises an Exception if no license with code was found."""
    lh = univention.bildungslogin.handlers.LicenseHandler(MagicMock())
    with patch.object(lh, "_get_all") as get_all_mock:
        get_all_mock.return_value = []
        with pytest.raises(BiloLicenseNotFoundError):
            lh.get_udm_license_by_code("CODE")


@patch("univention.bildungslogin.handlers.UDM")
def test_get_meta_data_by_product_id_no_data_found(_udm_mock):
    """Tests that an empty Metadata object is returned if no Metadata was found for a given product id"""
    lh = univention.bildungslogin.handlers.LicenseHandler(MagicMock())
    with patch.object(lh, "_meta_data_mod") as meta_data_mod_mock:
        meta_data_mod_mock.search.return_value = []
        result = lh.get_meta_data_by_product_id("ID")
    assert result == MetaData(product_id="ID")


@patch("univention.bildungslogin.handlers.UDM")
def test_get_meta_data_for_license_no_data_found(udm_mock, license_with_assignments):
    """Tests that an empty Metadata object is returned if no Metadata was found for a given license"""
    license, _ = license_with_assignments(1, 1)
    license.props.product_id = "ID"
    lh = univention.bildungslogin.handlers.LicenseHandler(MagicMock())
    with patch.object(lh, "_meta_data_mod") as meta_data_mod_mock:
        meta_data_mod_mock.search.return_value = []
        result = lh.get_meta_data_for_license(license)
    assert result == MetaData(product_id="ID")


@pytest.mark.parametrize("object_type", [ObjectType.USER, ObjectType.SCHOOL, ObjectType.GROUP])
@patch("univention.bildungslogin.handlers.UDM")
def test_remove_assignment_from_users_failed_assignments(_udm_mock, object_type):
    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    with patch.object(ah, "change_license_status") as change_mock:
        change_mock.side_effect = BiloAssignmentError("ERROR_MSG")
        result = ah.remove_assignment_from_objects("CODE", object_type, ["A"])
    assert len(result) == 1
    assert result[0] == ("A", "ERROR_MSG")


@pytest.mark.parametrize("object_type", [ObjectType.USER, ObjectType.SCHOOL, ObjectType.GROUP])
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "get_license_by_license_code")
@patch("univention.bildungslogin.handlers.UDM")
def test_change_license_status_invalid_status(_udm_mock, get_license_by_license_code_mock,
                                              license_with_assignments, object_type):
    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    get_license_by_license_code_mock.return_value = license_with_assignments(1, 1)
    with pytest.raises(BiloAssignmentError):
        ah.change_license_status("CODE", object_type, "USERNAME", "INVALID_STATUS")


@patch("univention.bildungslogin.handlers.UDM")
def test_get_license_by_license_code_not_found(_udm_mock):
    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    with patch.object(ah, "_licenses_mod") as license_mod_mock:
        license_mod_mock.search.side_effect = IndexError
        with pytest.raises(BiloLicenseNotFoundError):
            ah.get_license_by_license_code("SOME_INVALID_CODE")


@patch("univention.bildungslogin.handlers.UDM")
def test_get_user_by_username_no_users(_udm_mock):
    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    with patch.object(ah, "_users_mod") as users_mod_mock:
        users_mod_mock.search.return_value = []
        with pytest.raises(BiloAssignmentError):
            ah.get_user_by_username("SOME_USERNAME")
