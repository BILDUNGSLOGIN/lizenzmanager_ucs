#!/usr/share/ucs-test/runner /usr/bin/py.test -s
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
## desc: search for licenses
## exposure: dangerous
## tags: [vbm]
## roles: [domaincontroller_master]


import univention.testing.ucsschool.ucs_test_school as utu


def test_search_for_license_code(license_handler, meta_data_handler, meta_data, license):
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()

        license.product_id = meta_data.product_id
        license.license_school = ou
        license_handler.create(license)
        meta_data_handler.create(meta_data)
        res = license_handler.search_for_licenses(pattern=license.license_code, school=ou)
        assert len(res) == 1
        expected_res = {
            "licenseId": license.license_code,
            "productId": license.product_id,
            "productName": meta_data.title,
            "publisher": meta_data.publisher,
            "licenseCode": license.license_code,
            "licenseType": license.license_type,
            "countAquired": license_handler.get_total_number_of_assignments(license),
            "countAssigned": license_handler.get_number_of_provisioned_and_assigned_assignments(license),
            "countExpired": 0,  # self.get_number_of_expired_assignments(license),
            "countAvailable": license_handler.get_number_of_available_assignments(license),
            "importDate": license.delivery_date,
        }
        assert expected_res in res
        # todo fuzzy search does not work yet: substring searches need an index.
        # for i in range(len(license.license_code)):
        #     pattern = license.license_code[:i]
        #     res = license_handler.search_for_licenses(pattern=pattern, school=ou)
        #     assert expected_res in res
