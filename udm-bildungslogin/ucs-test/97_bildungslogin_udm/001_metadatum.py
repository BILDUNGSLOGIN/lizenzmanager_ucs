#!/usr/share/ucs-test/runner /usr/bin/py.test -slvv
# -*- coding: utf-8 -*-
## desc: Run tests for the udm module bildungslogin/metadata
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

import datetime
from hashlib import sha256

import pytest

import univention.testing.strings as uts
from univention.config_registry import ConfigRegistry
from univention.udm import CreateError

ucr = ConfigRegistry()
ucr.load()


@pytest.mark.parametrize("attr_name", ("cn", "product_id"))
def test_required_attributes(attr_name, udm):
    """Test that for meta data the attributes cn and product_id are mandatory"""
    with pytest.raises(CreateError) as exinfo:
        obj = udm.get("bildungslogin/metadata").new()
        obj.save()
    assert "\n{}".format(attr_name) in exinfo.value.message


def test_create_metadata(create_metadata):
    """Test that a meta data object can be created in LDAP"""
    metadata = create_metadata("PRODUCT_ID", datetime.date(2000, 1, 1))
    assert metadata.props.cn == sha256("PRODUCT_ID").hexdigest()


def test_unique_product_ids(create_metadata):
    """Test that for a meta data object the product_id has to be unique"""
    product_id = "PRODUCT_ID"
    create_metadata(product_id, datetime.date(2000, 1, 1))
    with pytest.raises(CreateError) as exinfo:
        create_metadata(product_id, datetime.date(2000, 1, 2))
    assert "A metadata object with that product_id already exists" in exinfo.value.message


def test_unique_product_ids_case_insensitive(create_metadata, scramble_case):
    """Test that for a meta data object the product_id has to be unique
    in a case insensitive way."""
    product_id = uts.random_name()
    product_id_other_case = scramble_case(product_id)
    assert product_id != product_id_other_case
    create_metadata(product_id, datetime.date(2000, 1, 1))
    with pytest.raises(CreateError) as exinfo:
        create_metadata(product_id_other_case, datetime.date(2000, 1, 2))
    assert "A metadata object with that product_id already exists" in exinfo.value.message
