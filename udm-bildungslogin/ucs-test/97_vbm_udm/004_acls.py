#!/usr/share/ucs-test/runner /usr/bin/py.test -slvv
# -*- coding: utf-8 -*-
## desc: Run tests for the replication ACLs of the UDM modules
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## exposure: dangerous
## tags: [vbm]
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

import pytest

import univention.testing.udm as udm_test
from univention.admin.uexceptions import noObject
from univention.admin.uldap import access, getMachineConnection
from univention.config_registry import ConfigRegistry

ucr = ConfigRegistry()
ucr.load()


def test_license_acl_machine(create_license):
    code = "CODE"
    license = create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    lo, _ = getMachineConnection()
    if ucr.get("server/role") in ["domaincontroller_master", "domaincontroller_backup"]:
        assert lo.searchDn(base=license.dn)
    else:
        with pytest.raises(noObject):
            lo.searchDn(base=license.dn)


def test_license_acl_user(create_license):
    code = "CODE"
    license = create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    user_pw = "univention"
    with udm_test.UCSTestUDM() as udm:
        userdn, username = udm.create_user(password=user_pw)
        lo = access(binddn=userdn, bindpw=user_pw, base=ucr.get("ldap/base"))
        with pytest.raises(noObject):
            lo.searchDn(base=license.dn)


def test_license_acl_school_admin(create_license):
    code = "CODE"
    create_license(code, "PRODUCT_ID", 10, "DEMOSCHOOL")
    user_pw = "univention"
    with udm_test.UCSTestUDM() as udm:
        userdn, username = udm.create_user(password=user_pw, options=["ucsschoolAdministrator"])
        lo = access(binddn=userdn, bindpw=user_pw, base=ucr.get("ldap/base"))
        assert lo.searchDn("(&(objectClass=vbmLicense)(vbmLicenseCode={}))".format(code))


def test_metadata_acl_machine(create_metadata):
    metadata = create_metadata("PRODUCT_ID", datetime.date(2000, 1, 1))
    lo, _ = getMachineConnection()
    if ucr.get("server/role") in ["domaincontroller_master", "domaincontroller_backup"]:
        assert lo.searchDn(base=metadata.dn)
    else:
        with pytest.raises(noObject):
            lo.searchDn(base=metadata.dn)


def test_metadata_acl_user(create_metadata):
    metadata = create_metadata("PRODUCT_ID", datetime.date(2000, 1, 1))
    user_pw = "univention"
    with udm_test.UCSTestUDM() as udm:
        userdn, username = udm.create_user(password=user_pw)
        lo = access(binddn=userdn, bindpw=user_pw, base=ucr.get("ldap/base"))
        with pytest.raises(noObject):
            lo.searchDn(base=metadata.dn)


def test_metadata_acl_school_admin(create_metadata):
    metadata = create_metadata("PRODUCT_ID", datetime.date(2000, 1, 1))
    user_pw = "univention"
    with udm_test.UCSTestUDM() as udm:
        userdn, username = udm.create_user(password=user_pw, options=["ucsschoolAdministrator"])
        lo = access(binddn=userdn, bindpw=user_pw, base=ucr.get("ldap/base"))
        assert lo.searchDn(base=metadata.dn)
