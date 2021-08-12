# -*- coding: utf-8 -*-
import datetime
import random
import sys
import uuid
from hashlib import sha256
from typing import Dict, Tuple

import pytest

import univention.bildungslogin.handlers
from univention.udm.base import BaseObject, BaseObjectProperties

if sys.version_info[0] >= 3:
    from unittest.mock import MagicMock, call, patch
else:
    from mock import MagicMock, call, patch


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
        obj.props.delivery_date = "2021-01-01"
        obj.props.expired = "0"
        obj.props.ignored = "0"
        obj.props.num_assigned = "0"
        obj.props.num_available = "0"
        obj.props.num_expired = "0"
        obj.props.product_id = "urn:bilo:medium:A0001#01-02-TZ"
        obj.props.provider = "ABC"
        obj.props.purchasing_reference = "2001-01-01T11:12:13 -02:00 010203"
        obj.props.quantity = "0"
        obj.props.school = "DEMOSCHOOL"
        obj.props.special_type = None
        return obj

    return _func


@pytest.fixture
def license_with_assignments(fake_udm_assignment_object, fake_udm_license_object, random_username):
    def _func(
        assignment_total, assignment_available
    ):  # type: (int, int) -> Tuple[BaseObject, Dict[str, BaseObject]]
        license = fake_udm_license_object()  # type: BaseObject
        license.props.quantity = str(assignment_total)
        license.props.num_available = str(assignment_available)
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


@patch("univention.bildungslogin.handlers.UDM")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "get_license_by_license_code")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "assign_to_license")
def test_assign_users_to_licenses_enough_licenses(
    assign_to_license_mock, get_license_by_license_code_mock, udm_mock, license_with_assignments, random_username
):
    # 3 available license assignments, validity_start_date in the future (->warning):
    assignment_available1 = 3
    assignment_total1 = random.randint(assignment_available1 + 1, assignment_available1 + 10)
    license1, assignments1 = license_with_assignments(assignment_total1, assignment_available1)
    license1.props.validity_start_date = "2030-01-01"
    license1.props.validity_end_date = "2040-01-01"

    # 0 available:
    assignment_available2 = 0
    assignment_total2 = random.randint(assignment_available2 + 1, assignment_available2 + 10)
    license2, assignments2 = license_with_assignments(assignment_total2, assignment_available2)
    license2.props.validity_start_date = "2000-01-01"
    license2.props.validity_end_date = "2025-01-01"

    # 10 available, must be used last (validity end furthest away):
    assignment_available3 = 10
    assignment_total3 = random.randint(assignment_available3 + 1, assignment_available3 + 10)
    license3, assignments3 = license_with_assignments(assignment_total3, assignment_available3)
    license3.props.validity_start_date = "2000-01-01"
    license3.props.validity_end_date = "2050-01-01"

    # 1 available, must be used first (validity end nearest (today)):
    assignment_available4 = 1
    assignment_total4 = random.randint(assignment_available4 + 1, assignment_available4 + 10)
    license4, assignments4 = license_with_assignments(assignment_total4, assignment_available4)
    license4.props.validity_start_date = "2000-01-01"
    license4.props.validity_end_date = datetime.date.today().strftime("%Y-%m-%d")

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
    result = ah.assign_users_to_licenses(
        [lic.props.code for lic in (license1, license2, license3, license4)], usernames
    )

    # sorted by validity end:
    used_licenses_codes = (
        [license4.props.code for _ in range(assignment_available4)]
        + [license1.props.code for _ in range(assignment_available1)]
        + [license2.props.code for _ in range(assignment_available2)]
        + [license3.props.code for _ in range(assignment_available3)]
    )
    # zip() will drop unused list items from used_licenses_codes (from license3):
    calls_to_assign_to_license = [call(l_c, u_n) for l_c, u_n in zip(used_licenses_codes, usernames)]
    assert assign_to_license_mock.call_args_list == calls_to_assign_to_license
    assert result == {
        "countUsers": len(usernames),
        "errors": {},
        "warnings": {license1.props.code: "Gültigkeitsbeginn liegt in der Zukunft."},
    }


@patch("univention.bildungslogin.handlers.UDM")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "get_license_by_license_code")
@patch.object(univention.bildungslogin.handlers.AssignmentHandler, "assign_to_license")
def test_assign_users_to_licenses_not_enough_licenses(
    assign_to_license_mock, get_license_by_license_code_mock, udm_mock, license_with_assignments, random_username
):
    assignment_available1 = random.randint(2, 10)
    assignment_total1 = random.randint(assignment_available1 + 1, assignment_available1 + 10)
    license1, assignments1 = license_with_assignments(assignment_total1, assignment_available1)
    license1.props.validity_start_date = "2000-01-01"
    license1.props.validity_end_date = "2040-01-01"

    get_license_by_license_code_mock.side_effect = lambda x: license1

    num_users = assignment_available1 + 1
    usernames = [random_username() for _ in range(num_users)]

    ah = univention.bildungslogin.handlers.AssignmentHandler(MagicMock())
    result = ah.assign_users_to_licenses([license1.props.code], usernames)

    calls_to_get_license_by_license_code = [call(license1.props.code)]
    assert get_license_by_license_code_mock.call_args_list == calls_to_get_license_by_license_code
    assert assign_to_license_mock.call_args_list == []
    assert result == {
        "countUsers": 0,
        "errors": {
            "*": "There are less available licenses than the number of users. No licenses have "
            "been assigned."
        },
        "warnings": {},
    }
