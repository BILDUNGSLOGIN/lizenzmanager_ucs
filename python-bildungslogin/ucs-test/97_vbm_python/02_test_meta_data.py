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
## desc: Test the metadata handler, i.e. the metadata view.
## exposure: dangerous
## tags: [vbm]
## roles: [domaincontroller_master]

import datetime
from hashlib import sha256

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.handlers import BiloAssignmentError
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
        "vbmMetaDataModified": [meta_data_obj.modified.strftime("%Y-%m-%d")],
    }
    dn = "cn={},cn=metadata,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
    verify_ldap_object(
        dn,
        expected_attr=expected_attr,
        strict=True,
    )


def test_create_meta_data(meta_data_handler, meta_data, ldap_base):
    """Test that meta data can be created"""
    meta_data_handler.create(meta_data)
    check_meta_data_is_correct(meta_data, ldap_base)


def test_save_meta_data(meta_data_handler, meta_data, ldap_base):
    """Test that meta data can be saved"""
    meta_data_handler.create(meta_data)
    meta_data.title = uts.random_name()
    meta_data.description = uts.random_name()
    meta_data.author = uts.random_name()
    meta_data.publisher = uts.random_name()
    meta_data.cover = uts.random_name()
    meta_data.cover_small = uts.random_name()
    meta_data.modified = datetime.date.today()
    meta_data_handler.save(meta_data)
    check_meta_data_is_correct(meta_data, ldap_base)


def test_get_assignments_for_meta_data(license_handler, meta_data_handler, license_obj, meta_data):
    """Test that license assignments are created with AVAILABLE status and have meta data"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        license = license_obj(ou)
        license.product_id = meta_data.product_id
        license_handler.create(license)
        assignments = meta_data_handler.get_assignments_for_meta_data(meta_data)
        for assignment in assignments:
            assert assignment.status == Status.AVAILABLE
            assert assignment.license == license.license_code


def test_total_number_licenses(license_handler, meta_data_handler, meta_data, n_licenses):
    """Test that the total number of licenses in meta data backend is as expected without ignored licenses"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        total_amount_of_licenses_for_product = 0
        for lic in n_licenses(ou):
            # comment: we do not have to create the actual meta-data object for this.
            lic.product_id = meta_data.product_id
            license_handler.create(lic)
            if lic.ignored_for_display is False:
                # licenses with this attribute set are not counted.
                total_amount_of_licenses_for_product += lic.license_quantity
        assert (
            meta_data_handler.get_total_number_of_assignments(meta_data)
            == total_amount_of_licenses_for_product
        )


def test_product_license_numbers(
    license_handler,
    license_obj,
    expired_license_obj,
    meta_data_handler,
    meta_data,
    assignment_handler,
):
    """
    Test to create a MetaData object and all combinations of licenses with the following properties in relation to the MetaData object
    # - ou is     related
    # - ou is not related
    # - product_id is     related
    # - product_id is not related
    # - is_ignored_for_display is True
    # - is_ignored_for_display is False
    # - expired is True
    # - expired is False
    """
    with utu.UCSTestSchool() as schoolenv:
        ou_related, _ = schoolenv.create_ou()
        ou_unrelated = uts.random_name()
        while ou_related == ou_unrelated:
            ou_unrelated = uts.random_name()
        ou_unrelated, _ = schoolenv.create_ou(ou_unrelated)
        product_id_related = "xxx"
        product_id_unrelated = "yyy"
        meta_data.product_id = product_id_related
        license_quantity = 3  # number of assignable licenses per license object
        num_of_licenses_per_type = 2  # create x of each license combination
        num_students = 2  # number of students we will assign licenses to

        for_assignment = []  # used for license_handler.assign_users_to_licenses
        to_expire = None  # license we will later expire to check counts again
        for is_ou_related in [True, False]:
            for is_product_id_related in [True, False]:
                for is_ignored_for_display in [True, False]:
                    for is_expired in [True, False]:
                        for x in range(num_of_licenses_per_type):
                            ou = ou_related if is_ou_related else ou_unrelated
                            product_id = (
                                product_id_related if is_product_id_related else product_id_unrelated
                            )
                            func = expired_license_obj if is_expired else license_obj
                            license = func(ou)
                            license.product_id = product_id
                            license.ignored_for_display = is_ignored_for_display
                            license.license_quantity = license_quantity
                            license_handler.create(license)

                            student_usernames = [
                                schoolenv.create_student(ou)[0] for i in range(num_students)
                            ]
                            for_assignment.append((student_usernames, license))
                            if (
                                is_ou_related
                                and is_product_id_related
                                and not is_ignored_for_display
                                and not is_expired
                            ):
                                to_expire = license

        # the num for the expectation is license_quantity * num_of_licenses_per_type * x
        # where x is the number of licenses where at least ou_related, product_id_related and !ignored_for_display
        # is true.

        expected_count_aquired = (
            license_quantity * num_of_licenses_per_type * 2
        )  # 2 = (expired + !expired))
        expected_count_assigned = 0  # no assignments yet
        expected_count_expired = (
            license_quantity * num_of_licenses_per_type * 1
        ) - expected_count_assigned  # 1 = expired
        expected_count_available = (
            license_quantity * num_of_licenses_per_type * 1
        ) - expected_count_assigned  # 1 = !expired

        assert expected_count_aquired == meta_data_handler.get_total_number_of_assignments(
            meta_data, ou_related
        )
        assert expected_count_expired == meta_data_handler.get_number_of_expired_assignments(
            meta_data, ou_related
        )
        assert (
            expected_count_assigned
            == meta_data_handler.get_number_of_provisioned_and_assigned_assignments(
                meta_data, ou_related
            )
        )
        assert expected_count_available == meta_data_handler.get_number_of_available_assignments(
            meta_data, ou_related
        )

        for (student_usernames, license) in for_assignment:
            assignment_handler.assign_users_to_licenses(
                usernames=student_usernames, license_codes=[license.license_code]
            )
        expected_count_assigned = num_of_licenses_per_type * num_students
        expected_count_available = expected_count_available - expected_count_assigned

        assert expected_count_aquired == meta_data_handler.get_total_number_of_assignments(
            meta_data, ou_related
        )
        assert expected_count_expired == meta_data_handler.get_number_of_expired_assignments(
            meta_data, ou_related
        )
        assert (
            expected_count_assigned
            == meta_data_handler.get_number_of_provisioned_and_assigned_assignments(
                meta_data, ou_related
            )
        )
        assert expected_count_available == meta_data_handler.get_number_of_available_assignments(
            meta_data, ou_related
        )

        # after provisioning the code to some users, the numbers should still be the same.
        for (student_usernames, license) in for_assignment:
            try:
                assignment_handler.change_license_status(
                    username=student_usernames[0],
                    license_code=license.license_code,
                    status=Status.PROVISIONED,
                )
            except BiloAssignmentError:
                pass

        assert expected_count_aquired == meta_data_handler.get_total_number_of_assignments(
            meta_data, ou_related
        )
        assert expected_count_expired == meta_data_handler.get_number_of_expired_assignments(
            meta_data, ou_related
        )
        assert (
            expected_count_assigned
            == meta_data_handler.get_number_of_provisioned_and_assigned_assignments(
                meta_data, ou_related
            )
        )
        assert expected_count_available == meta_data_handler.get_number_of_available_assignments(
            meta_data, ou_related
        )

        # expire one of the licenses and check the counts again
        o = license_handler.get_udm_license_by_code(to_expire.license_code)
        o._orig_udm_object.lo.modify(
            o.dn, [("vbmValidityEndDate", o.props.validity_end_date, "2000-01-01")]
        )
        num_of_newly_expired_licenses = (
            license_quantity - num_students
        )  # we assign num_students to each license so the number of expired licenses should be
        #    our quantity minus the number of assigned students

        expected_count_expired = expected_count_expired + num_of_newly_expired_licenses
        expected_count_available = expected_count_available - num_of_newly_expired_licenses

        assert expected_count_aquired == meta_data_handler.get_total_number_of_assignments(
            meta_data, ou_related
        )
        assert expected_count_expired == meta_data_handler.get_number_of_expired_assignments(
            meta_data, ou_related
        )
        assert (
            expected_count_assigned
            == meta_data_handler.get_number_of_provisioned_and_assigned_assignments(
                meta_data, ou_related
            )
        )
        assert expected_count_available == meta_data_handler.get_number_of_available_assignments(
            meta_data, ou_related
        )


def test_number_of_provisioned_and_assigned_licenses(
    license_handler,
    meta_data_handler,
    assignment_handler,
    meta_data,
    license_obj,
):
    """Test the number of provisioned licenses is included in the number of assigned licenses"""
    num_students = 3
    num_teachers = 3
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        student_usernames = [schoolenv.create_student(ou)[0] for i in range(num_students)]
        teacher_usernames = [schoolenv.create_teacher(ou)[0] for i in range(num_teachers)]
        users = student_usernames + teacher_usernames
        license = license_obj(ou)
        license.product_id = meta_data.product_id
        license.ignored_for_display = False  # we only want correct assignments here
        license.license_quantity = len(users) + 1
        license_handler.create(license)
        assignment_handler.assign_users_to_licenses(
            usernames=users, license_codes=[license.license_code]
        )
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


def test_number_of_expired_licenses(license_handler, meta_data_handler, meta_data, n_expired_licenses):
    """Test the numer of expired licenses is as expected"""
    total_amount_of_licenses_for_product = 0
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        # an assignment is not expired if end_date + duration < today
        for lic in n_expired_licenses(ou):
            lic.product_id = meta_data.product_id
            license_handler.create(lic)
            total_amount_of_licenses_for_product += license_handler.get_number_of_expired_assignments(
                lic
            )
        assert (
            meta_data_handler.get_number_of_expired_assignments(meta_data)
            == total_amount_of_licenses_for_product
        )


def test_get_all_product_ids(meta_data_handler, n_meta_data):
    """Test that the value of all product ids in meta data are as expected"""
    product_ids_expected = set()
    for m in n_meta_data:
        meta_data_handler.create(m)
        product_ids_expected.add(m.product_id)
    assert product_ids_expected.issubset(set(meta_data_handler.get_all_product_ids()))


def test_get_all_publishers(meta_data_handler, n_meta_data):
    """Test that the value of all publishers in meta data are as expected"""
    publishers = []
    for m in n_meta_data:
        meta_data_handler.create(m)
        publishers.append(m.publisher)
    assert set(publishers).issubset(set(meta_data_handler.get_all_publishers()))
