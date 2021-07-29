#!/usr/share/ucs-test/runner /usr/bin/py.test -s
## desc: Run tests for the udm module vbm/assignment
## exposure: dangerous
## tags: [vbm]
## packages: [udm-bildungslogin]
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

from univention.udm import NoSuperordinate, ModifyError


def test_create_assignment(create_license, udm):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("vbm/assignment").new(license_obj.dn)
    assignment.props.status = "AVAILABLE"
    assignment.save()
    assert assignment.position == license_obj.dn


def test_wrong_superordinate(create_metadatum, udm):
    metadatum = create_metadatum(product_id="PRODUCT")
    with pytest.raises(NoSuperordinate):
        udm.get("vbm/assignment").new(metadatum.dn)


@pytest.mark.parametrize("status", ("AVAILABLE", "ASSIGNED", "PROVISIONED"))
def test_allowed_status(status, create_license, udm):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("vbm/assignment").new(license_obj.dn)
    assignment.props.status = status
    assignment.save()
    assert assignment.position == license_obj.dn


def test_wrong_status(create_license, udm):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("vbm/assignment").new(license_obj.dn)
    assignment.props.status = "SOME_STATUS"
    with pytest.raises(valueInvalidSyntax):
        assignment.save()


@pytest.mark.parametrize("old_status,new_status", [
    ("AVAILABLE", "ASSIGNED"),
    ("ASSIGNED", "AVAILABLE"),
    ("ASSIGNED", "PROVISIONED")
])
def test_allowed_status_transitions(old_status, new_status, create_license, udm):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("vbm/assignment").new(license_obj.dn)
    assignment.props.status = old_status
    assignment.save()
    assignment.props.status = new_status
    assignment.save()


@pytest.mark.parametrize("old_status,new_status", [
    ("AVAILABLE", "PROVISIONED"),
    ("PROVISIONED", "ASSIGNED"),
    ("PROVISIONED", "AVAILABLE")
])
def test_wrong_status_transitions(old_status, new_status, create_license, udm):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assignment = udm.get("vbm/assignment").new(license_obj.dn)
    assignment.props.status = old_status
    assignment.save()
    assignment.props.status = new_status
    with pytest.raises(ModifyError) as exinfo:
        assignment.save()
    assert "Invalid status transition" in exinfo.value.message
