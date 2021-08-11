#!/usr/share/ucs-test/runner /usr/bin/py.test -s
# -*- coding: utf-8 -*-
## desc: Run tests for the replication ACLs of the UDM modules
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## exposure: dangerous
## tags: [vbm]

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


def test_metadata_acl_machine(create_metadata):
    metadata = create_metadata("PRODUCT_ID", "2000-01-01")
    lo, _ = getMachineConnection()
    if ucr.get("server/role") in ["domaincontroller_master", "domaincontroller_backup"]:
        assert lo.searchDn(base=metadata.dn)
    else:
        with pytest.raises(noObject):
            lo.searchDn(base=metadata.dn)


def test_metadata_acl_user(create_metadata):
    metadata = create_metadata("PRODUCT_ID", "2000-01-01")
    user_pw = "univention"
    with udm_test.UCSTestUDM() as udm:
        userdn, username = udm.create_user(password=user_pw)
        lo = access(binddn=userdn, bindpw=user_pw, base=ucr.get("ldap/base"))
        with pytest.raises(noObject):
            lo.searchDn(base=metadata.dn)
