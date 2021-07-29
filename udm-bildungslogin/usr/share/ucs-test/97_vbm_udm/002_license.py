#!/usr/share/ucs-test/runner /usr/bin/py.test -s
## desc: Run tests for the udm module vbm/license
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
from hashlib import sha256

import pytest
from univention.udm import CreateError


@pytest.mark.parametrize("attr_name", (
    "cn",
    "code",
    "product_id",
    "quantity",
    "school",
    "validity_start_date",
    "validity_end_date",
    "delivery_date",
    ))
def test_required_attributes(attr_name, udm):
    with pytest.raises(CreateError) as exinfo:
        obj = udm.get("vbm/license").new()
        obj.save()
    assert "\n{}".format(attr_name) in exinfo.value.message


def test_create_license(create_license):
    license_obj = create_license("LICENSE_CODE", "PRODUCT_ID", 10, "DEMOSCHOOL")
    assert license_obj.props.cn == sha256("LICENSE_CODE").hexdigest()


def test_unique_codes(create_license):
    code = "CODE"
    create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    with pytest.raises(CreateError) as exinfo:
        create_license(code, "PRODUCT_ID2", 22, "SOME_SCHOOL")
    assert "A license with that code already exists" in exinfo.value.message
