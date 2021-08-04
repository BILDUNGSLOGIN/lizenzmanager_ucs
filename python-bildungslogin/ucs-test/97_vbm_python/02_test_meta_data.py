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
## desc: Test the metadata handler, i.e. the metadata view.
## exposure: dangerous
## tags: [vbm]
## roles: [domaincontroller_master]

import datetime
from hashlib import sha256

import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.utils import Status
from univention.testing.utils import verify_ldap_object


def check_meta_data_is_correct(meta_data_obj, ldap_base):
    cn = sha256(meta_data_obj.product_id).hexdigest()
    expected_attr = {
        "cn": [cn],
        "vbmProductId": [meta_data_obj.product_id],
        "vbmMetaDataTitle": [meta_data_obj.title],
        "vbmMetaDataDescription": [meta_data_obj.description],
        "vbmMetaDataAuthor": [meta_data_obj.author],
        "vbmMetaDataPublisher": [meta_data_obj.publisher],
        "vbmMetaDataCover": [meta_data_obj.cover],
        "vbmMetaDataCoverSmall": [meta_data_obj.cover_small],
        "vbmMetaDataModified": [meta_data_obj.modified],
    }

    dn = "cn={},cn=metadata,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
    verify_ldap_object(
        dn,
        expected_attr=expected_attr,
        strict=True,
    )


def test_create_meta_data(meta_data_handler, meta_data, ldap_base):
    meta_data_handler.create(meta_data)
    check_meta_data_is_correct(meta_data, ldap_base)


def test_save_meta_data(meta_data_handler, meta_data, ldap_base):
    meta_data_handler.create(meta_data)
    meta_data.title = uts.random_name()
    meta_data.description = uts.random_name()
    meta_data.author = uts.random_name()
    meta_data.publisher = uts.random_name()
    meta_data.cover = uts.random_name()
    meta_data.cover_small = uts.random_name()
    meta_data.modified = datetime.datetime.today().strftime("%Y-%m-%d")
    meta_data_handler.save(meta_data)
    check_meta_data_is_correct(meta_data, ldap_base)


def test_get_assignments_for_meta_data(license_handler, meta_data_handler, license, meta_data):
    license.product_id = meta_data.product_id
    license_handler.create(license)
    assignments = meta_data_handler.get_assignments_for_meta_data(meta_data)
    for assignment in assignments:
        assert assignment.status == Status.AVAILABLE
        assert assignment.license == license.license_code


def test_total_number_licenses(license_handler, meta_data_handler, meta_data, n_licenses):
    total_amount_of_licenses_for_product = 0
    for lic in n_licenses:
        # comment: we do not have to create the actual meta-data object for this.
        lic.product_id = meta_data.product_id
        license_handler.create(lic)
        total_amount_of_licenses_for_product += lic.license_quantity
    assert (
        meta_data_handler.get_total_number_of_assignments(meta_data)
        == total_amount_of_licenses_for_product
    )


def test_number_of_provisioned_and_assigned_licenses(
    license_handler,
    meta_data_handler,
    assignment_handler,
    meta_data,
    license,
):
    # 00_vbm_test_assignments
    # the number of provisioned licenses is included in the number of assigned licenses
    num_students = 3
    num_teachers = 3
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license.product_id = meta_data.product_id
        license.license_school = ou
        license_handler.create(license)
        student_usernames = [schoolenv.create_student(ou)[0] for _ in range(num_students)]
        teacher_usernames = [schoolenv.create_teacher(ou)[0] for _ in range(num_teachers)]
        users = student_usernames + teacher_usernames
        assignment_handler.assign_users_to_license(usernames=users, licenses_code=license.license_code)
        num_assigned = meta_data_handler.get_number_of_provisioned_and_assigned_assignments(meta_data)
        assert num_assigned == num_students + num_teachers
        for user_name in users[:2]:
            assignment_handler.change_license_status(
                username=user_name,
                license_code=license.license_code,
                status=Status.PROVISIONED,
            )
        # after provisioning the code to some users, the number should still be the same.
        num_assigned = meta_data_handler.get_number_of_provisioned_and_assigned_assignments(meta_data)
        assert num_assigned == num_students + num_teachers
        # the number of available licenses for this product should be the total number - the number
        # of users which just got the license for this product
        total_num = meta_data_handler.get_total_number_of_assignments(meta_data)
        assert meta_data_handler.get_number_of_available_assignments(meta_data) == total_num - len(users)


@pytest.mark.skip(reason="num_expired has to be fixed in udm")
def test_number_of_expired_licenses(license_handler, meta_data_handler, meta_data, n_expired_licenses):
    total_amount_of_licenses_for_product = 0
    # a assignment is not expired if end_date + duration < today
    for lic in n_expired_licenses:
        lic.product_id = meta_data.product_id
        license_handler.create(lic)
        total_amount_of_licenses_for_product += license_handler.get_number_of_expired_assignments(lic)
    assert (
        meta_data_handler.get_number_of_expired_assignments(meta_data)
        == total_amount_of_licenses_for_product
    )


def test_get_all_product_ids(meta_data_handler, n_meta_data):
    product_ids_expected = set()
    for m in n_meta_data:
        meta_data_handler.create(m)
        product_ids_expected.add(m.product_id)
    assert set(meta_data_handler.get_all_product_ids()).issubset(product_ids_expected)


def test_get_all_publishers(meta_data_handler, n_meta_data):
    publishers = []
    for m in n_meta_data:
        meta_data_handler.create(m)
        publishers.append(m.publisher)
    assert set(publishers).issubset(set(meta_data_handler.get_all_publishers()))
