#!/usr/share/ucs-test/runner /usr/bin/py.test -slvv
# -*- coding: utf-8 -*-
## desc: Run tests for the udm module bildungslogin/assignment
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
import pytest

from univention.admin.uexceptions import valueInvalidSyntax
from univention.udm import CreateError, ModifyError, NoSuperordinate


def test_create_assignment(create_license, udm):
    """Test that a license assignment object can be created in LDAP"""
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
    assignment.props.status = "AVAILABLE"
    assignment.save()
    assert assignment.position == license_obj.dn


def test_wrong_superordinate(create_metadata, udm):
    """TODO add test description"""
    metadata = create_metadata(product_id="PRODUCT")
    with pytest.raises(NoSuperordinate):
        udm.get("bildungslogin/assignment").new(metadata.dn)


@pytest.mark.parametrize(
    "status,assignee", [("AVAILABLE", ""), ("ASSIGNED", "USER"), ("PROVISIONED", "USER")]
)
def test_allowed_status(status, assignee, create_license, udm):
    """Test that an assignment has a status that can change from AVAILABLE to ASSIGNED and PROVISIONED"""
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
    assignment.props.status = status
    assignment.props.assignee = assignee
    assignment.save()
    assert assignment.position == license_obj.dn


def test_wrong_status(create_license, udm):
    """Test that an assignment can not have an unknown status"""
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
    assignment.props.status = "SOME_STATUS"
    with pytest.raises(valueInvalidSyntax):
        assignment.save()


@pytest.mark.parametrize(
    "old_status,new_status,old_assignee,new_assignee",
    [
        ("AVAILABLE", "ASSIGNED", "", "USER"),
        ("ASSIGNED", "AVAILABLE", "USER", ""),
        ("ASSIGNED", "PROVISIONED", "USER", "USER"),
    ],
)
def test_allowed_status_transitions(
    old_status, new_status, old_assignee, new_assignee, create_license, udm
):
    """
    Test that for an assignment the status is allowed to change:

    old_status -> new_status, old_assignee -> new_assignee

    AVAILABLE -> ASSIGNED, "" -> "USER"
    ASSIGNED -> AVAILABLE, "USER" -> ""
    ASSIGNED -> PROVISIONED, "USER" -> "USER"
    """
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
    assignment.props.status = old_status
    assignment.props.assignee = old_assignee
    assignment.save()
    assignment.props.status = new_status
    assignment.props.assignee = new_assignee
    assignment.save()


@pytest.mark.parametrize(
    "old_status,new_status,old_assignee,new_assignee",
    [
        ("AVAILABLE", "PROVISIONED", "", "USER"),
        ("PROVISIONED", "ASSIGNED", "USER", "USER"),
        ("PROVISIONED", "AVAILABLE", "USER", ""),
    ],
)
def test_wrong_status_transitions(
    old_status, new_status, old_assignee, new_assignee, create_license, udm
):
    """
    Test that for an assignment the status is not allowed to change:

    old_status -> new_status, old_assignee -> new_assignee

    AVAILABLE -> PROVISIONED, "" -> "USER"
    PROVISIONED -> ASSIGNED, "USER" -> "USER"
    PROVISIONED -> AVAILABLE, "USER" -> ""
    """
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
    assignment.props.status = old_status
    assignment.props.assignee = old_assignee
    assignment.save()
    assignment.props.status = new_status
    assignment.props.assignee = new_assignee
    with pytest.raises(ModifyError) as exinfo:
        assignment.save()
    assert "Invalid status transition" in exinfo.value.message


@pytest.mark.parametrize("status", ("ASSIGNED", "PROVISIONED"))
def test_status_require_assignee(status, create_license, udm):
    """Test that for an assignment an assignee is needed"""
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
    assignment.props.status = status
    with pytest.raises(CreateError) as exinfo:
        assignment.save()
    assert "An assignment in status {} needs an assignee.".format(status) in exinfo.value.message


def test_status_available_no_assignee(create_license, udm):
    """Test that for an assignment with status AVAILABLE no assignee should be set"""
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("bildungslogin/assignment").new(license_obj.dn)
    assignment.props.status = "AVAILABLE"
    assignment.props.assignee = "SOME_USER"
    with pytest.raises(CreateError) as exinfo:
        assignment.save()
    assert "An assignment in status AVAILABLE must not have an assignee." in exinfo.value.message
