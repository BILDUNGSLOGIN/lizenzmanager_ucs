#!/usr/share/ucs-test/runner /usr/bin/py.test -slvv --cov --cov-config=.coveragerc --cov-append --cov-report=
# -*- coding: utf-8 -*-
## desc: Test simple UDM API encoders for bildungslogin/*
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## exposure: dangerous
## tags: [bildungslogin]
## packages: [udm-bildungslogin-encoders]

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

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
from univention.config_registry import ConfigRegistry
from univention.testing.utils import verify_ldap_object
from univention.udm.base import BaseObject

ucr = ConfigRegistry()
ucr.load()


@pytest.mark.parametrize("correct_assignee", [True, False])
def test_assignment_dn_encoder(create_license, udm, lo, correct_assignee):
    assert udm.api_version >= 1

    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        username, user_dn = schoolenv.create_student(ou)
        entry_uuid = lo.get(user_dn, attr=["entryUUID"])["entryUUID"][0]
        license_obj = create_license(str(uuid.uuid4()), str(uuid.uuid4()), 1, ou, "SINGLE")
        assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
        assignment.props.status = "AVAILABLE"
        assignment.save()

        assignment.props.status = "ASSIGNED"
        if correct_assignee:
            assignment.props.assignee = entry_uuid
        else:
            assignment.props.assignee = "SOME_STRING"
        assignment.props.time_of_assignment = datetime.date.today()
        assignment.save()

        if correct_assignee:
            assert assignment.props.assignee.obj.dn == user_dn
        else:
            assert assignment.props.assignee.obj == None  # noqa: E711


def test_bildungslogin_assignment(create_license, udm):
    """Test that the license assignment is stored in LDAP with the expected type for each attribute"""
    assert udm.api_version >= 1

    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license_obj = create_license(str(uuid.uuid4()), str(uuid.uuid4()), 1, ou, "SINGLE")
        assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
        assignment.props.status = "AVAILABLE"
        assignment.save()

        verify_ldap_object(
            assignment.dn,
            expected_attr={
                "univentionObjectType": ["bildungslogin/assignment"],
                "bildungsloginAssignmentStatus": [assignment.props.status],
            },
            primary=True,
        )

        assignment.props.status = "ASSIGNED"
        assignment.props.assignee = str(uuid.uuid4())
        assignment.props.time_of_assignment = datetime.date.today()
        assignment.save()

        verify_ldap_object(
            assignment.dn,
            expected_attr={
                "univentionObjectType": ["bildungslogin/assignment"],
                "bildungsloginAssignmentStatus": [assignment.props.status],
                "bildungsloginAssignmentAssignee": [assignment.props.assignee],
                "bildungsloginAssignmentTimeOfAssignment": [
                    assignment.props.time_of_assignment.strftime("%Y-%m-%d")
                ],
            },
            primary=True,
        )


def test_bildungslogin_license(create_license, udm):
    """Test that the license is stored in LDAP with the expected type for each attribute"""
    assert udm.api_version >= 1

    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        assigned_num = random.randint(1, 4)
        total_num = random.randint(assigned_num + 1, assigned_num + 10)
        license_obj = create_license(str(uuid.uuid4()), str(uuid.uuid4()), total_num, ou, "VOLUME")
        assert license_obj.props.quantity == total_num

        # test UDM conversion for properties actually stored in LDAP
        verify_ldap_object(
            license_obj.dn,
            expected_attr={
                "univentionObjectType": ["bildungslogin/license"],
                "bildungsloginDeliveryDate": [license_obj.props.delivery_date.strftime("%Y-%m-%d")],
                "bildungsloginIgnoredForDisplay": ["1" if license_obj.props.ignored else "0"],
                "bildungsloginLicenseQuantity": [str(license_obj.props.quantity)],
                "bildungsloginValidityEndDate": [
                    license_obj.props.validity_end_date.strftime("%Y-%m-%d")
                ],
                "bildungsloginValidityStartDate": [
                    license_obj.props.validity_start_date.strftime("%Y-%m-%d")
                ],
            },
            primary=True,
        )

        # test UDM conversion for virtual properties
        assignments = []
        for _ in range(total_num):
            assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
            assignment.props.status = "AVAILABLE"
            assignment.save()
            assignments.append(assignment)

        for assignment in assignments[:assigned_num]:
            assignment.props.status = "ASSIGNED"
            assignment.props.assignee = str(uuid.uuid4())
            assignment.props.time_of_assignment = datetime.date.today()
            assignment.save()

        license_obj.reload()

        assert license_obj.props.quantity == total_num
        assert license_obj.props.expired is True
        assert license_obj.props.num_expired == total_num - assigned_num
        assert license_obj.props.num_assigned == assigned_num
        assert license_obj.props.num_available == 0
        assert set(license_obj.props.assignments) == {a.dn for a in assignments}
        assignment_objs = license_obj.props.assignments.objs
        assert all(isinstance(obj, BaseObject) for obj in assignment_objs)
        assert {a_obj.dn for a_obj in assignment_objs} == {a.dn for a in assignments}


def test_bildungslogin_metadata(create_metadata, udm):
    """Test that the meta data is stored in LDAP with the expected type for each attribute"""
    assert udm.api_version >= 1

    metadate_obj = create_metadata(str(uuid.uuid4()))

    verify_ldap_object(
        metadate_obj.dn,
        expected_attr={
            "univentionObjectType": ["bildungslogin/metadata"],
            "bildungsloginMetaDataCover": [metadate_obj.props.cover],
            "bildungsloginMetaDataCoverSmall": [metadate_obj.props.cover_small],
            "bildungsloginMetaDataDescription": [metadate_obj.props.description],
            "bildungsloginMetaDataModified": [metadate_obj.props.modified.strftime("%Y-%m-%d")],
            "bildungsloginMetaDataPublisher": [metadate_obj.props.publisher],
            "bildungsloginMetaDataTitle": [metadate_obj.props.title],
            "bildungsloginProductId": [metadate_obj.props.product_id],
        },
        primary=True,
    )
