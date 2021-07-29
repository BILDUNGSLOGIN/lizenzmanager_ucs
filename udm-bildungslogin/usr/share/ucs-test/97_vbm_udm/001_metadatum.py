#!/usr/share/ucs-test/runner /usr/bin/py.test -s
## desc: Run tests for the udm module vbm/metadatum
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


@pytest.mark.parametrize("attr_name", ("cn", "product_id"))
def test_required_attributes(attr_name, udm):
    with pytest.raises(CreateError) as exinfo:
        obj = udm.get("vbm/metadatum").new()
        obj.save()
    assert "\n{}".format(attr_name) in exinfo.value.message


def test_create_metadatum(create_metadatum):
    datum = create_metadatum("PRODUCT_ID", "2000-01-01")
    assert datum.props.cn == sha256("PRODUCT_ID").hexdigest()


def test_unique_product_ids(create_metadatum):
    create_metadatum("PRODUCT_ID", "2000-01-01")
    with pytest.raises(CreateError) as exinfo:
        create_metadatum("PRODUCT_ID", "2000-01-01")
    assert "A Metadatum with that product_id already exists" in exinfo.value.message
