#!/usr/share/ucs-test/runner /usr/bin/py.test -slv
# -*- coding: utf-8 -*-
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
## desc: Test the cli bilo license import
## exposure: dangerous
## tags: [bildungslogin]
## roles: [domaincontroller_master]

import json
import subprocess

from ldap.filter import filter_format

import univention.testing.ucsschool.ucs_test_school as utu
from univention.admin.uldap import getAdminConnection


def test_cli_import(license_file, license_handler):
    """Test that a license can be imported by the CLI tool bildungslogin-license-import"""
    with open(str(license_file), "r") as license_file_fd:
        licenses_raw = json.load(license_file_fd)
    filter_s = filter_format(
        "(|{})".format("".join(["(code=%s)"] * len(licenses_raw))),
        [license_raw["lizenzcode"] for license_raw in licenses_raw],
    )
    lo, po = getAdminConnection()
    print("filter for licenses: {}".format(filter_s))
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        try:
            subprocess.check_call(
                [
                    "bildungslogin-license-import",
                    "--license-file",
                    str(license_file),
                    "--school",
                    ou,
                ]
            )
            licenses = license_handler.get_all(filter_s=filter_s)
        finally:
            licenses_dn = lo.searchDn(filter=filter_s)
            for dn in licenses_dn:
                subprocess.check_call(
                    ["udm", "bildungslogin/license", "remove", "--dn", dn, "--recursive"]
                )
    assert set(license.license_code for license in licenses) == set(
        license_raw["lizenzcode"] for license_raw in licenses_raw
    )
