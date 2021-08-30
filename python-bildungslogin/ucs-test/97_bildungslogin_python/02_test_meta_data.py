#!/usr/share/ucs-test/runner /usr/bin/py.test -slvv --cov-config=.coveragerc --cov-append --cov-report=
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
## tags: [bildungslogin]
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## packages: [python-bildungslogin, udm-bildungslogin-encoders]

import datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Optional

import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.handlers import BiloAssignmentError
from univention.bildungslogin.utils import Status
from univention.testing.utils import verify_ldap_object

if TYPE_CHECKING:
    from univention.bildungslogin.handlers import MetaDataHandler
    from univention.bildungslogin.models import MetaData


def check_meta_data_is_correct(meta_data_obj, ldap_base):
    cn = sha256(meta_data_obj.product_id).hexdigest()
    expected_attr = {
        "cn": [cn],
        "bildungsloginProductId": [meta_data_obj.product_id],
        "bildungsloginMetaDataTitle": [meta_data_obj.title],
        "bildungsloginMetaDataDescription": [meta_data_obj.description],
        "bildungsloginMetaDataAuthor": [meta_data_obj.author],
        "bildungsloginMetaDataPublisher": [meta_data_obj.publisher],
        "bildungsloginMetaDataCover": [meta_data_obj.cover],
        "bildungsloginMetaDataCoverSmall": [meta_data_obj.cover_small],
        "bildungsloginMetaDataModified": [meta_data_obj.modified.strftime("%Y-%m-%d")],
    }
    dn = "cn={},cn=metadata,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
    verify_ldap_object(
        dn,
        expected_attr=expected_attr,
        strict=True,
        primary=True,
    )


def get_total_number_of_assignments(meta_data_handler, meta_data, school=None):
    # type: (MetaDataHandler, MetaData, Optional[str]) -> int
    """count the total number of assignments"""
    licenses_of_product = meta_data_handler.get_non_ignored_licenses_for_product_id(
        meta_data.product_id, school
    )
    return sum(udm_license.props.quantity for udm_license in licenses_of_product)


def get_number_of_available_assignments(meta_data_handler, meta_data, school=None):
    # type: (MetaDataHandler, MetaData, Optional[str]) -> int
    """count the number of assignments with status available"""
    licenses_of_product = meta_data_handler.get_non_ignored_licenses_for_product_id(
        meta_data.product_id, school
    )
    return sum(udm_license.props.num_available for udm_license in licenses_of_product)


def get_number_of_provisioned_and_assigned_assignments(meta_data_handler, meta_data, school=None):
    # type: (MetaDataHandler, MetaData, Optional[str]) -> int
    """count the number of assignments with status provisioned or assigned"""
    licenses_of_product = meta_data_handler.get_non_ignored_licenses_for_product_id(
        meta_data.product_id, school
    )
    return sum(udm_license.props.num_assigned for udm_license in licenses_of_product)


def get_number_of_expired_assignments(meta_data_handler, meta_data, school=None):
    # type: (MetaDataHandler, MetaData, Optional[str]) -> int
    """count the number of assignments with status expired"""
    licenses_of_product = meta_data_handler.get_non_ignored_licenses_for_product_id(
        meta_data.product_id, school
    )
    return sum(udm_license.props.num_expired for udm_license in licenses_of_product)


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


def test_total_number_licenses(license_handler, meta_data_handler, meta_data, n_licenses, hostname):
    """Test that the total number of licenses in meta data backend is as expected without ignored licenses"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        total_amount_of_licenses_for_product = 0
        for lic in n_licenses(ou):
            # comment: we do not have to create the actual meta-data object for this.
            lic.product_id = meta_data.product_id
            license_handler.create(lic)
            if lic.ignored_for_display is False:
                # licenses with this attribute set are not counted.
                total_amount_of_licenses_for_product += lic.license_quantity
        assert (
            get_total_number_of_assignments(meta_data_handler, meta_data)
            == total_amount_of_licenses_for_product
        )
        # ou is case insensitive. Because there is only one license, the number is the same if
        # no school is passed.
        for ou_name in (None, ou, ou.upper(), ou.swapcase()):
            assert (
                get_total_number_of_assignments(meta_data_handler, meta_data, ou_name)
                == total_amount_of_licenses_for_product
            )


def test_product_license_numbers(
    license_handler,
    license_obj,
    expired_license_obj,
    meta_data_handler,
    meta_data,
    assignment_handler,
    hostname,
):
    """
    Test to create a MetaData object and all combinations of licenses with the following properties in
    relation to the MetaData object

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
        ou_related, _ = schoolenv.create_ou(name_edudc=hostname)
        ou_unrelated = uts.random_name()
        while ou_related == ou_unrelated:
            ou_unrelated = uts.random_name()
        ou_unrelated, _ = schoolenv.create_ou(ou_unrelated, name_edudc=hostname)
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

        assert expected_count_aquired == get_total_number_of_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_expired == get_number_of_expired_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_assigned == get_number_of_provisioned_and_assigned_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_available == get_number_of_available_assignments(
            meta_data_handler, meta_data, ou_related
        )

        for (student_usernames, license) in for_assignment:
            assignment_handler.assign_users_to_licenses(
                usernames=student_usernames, license_codes=[license.license_code]
            )
        expected_count_assigned = num_of_licenses_per_type * num_students
        expected_count_available = expected_count_available - expected_count_assigned

        assert expected_count_aquired == get_total_number_of_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_expired == get_number_of_expired_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_assigned == get_number_of_provisioned_and_assigned_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_available == get_number_of_available_assignments(
            meta_data_handler, meta_data, ou_related
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

        assert expected_count_aquired == get_total_number_of_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_expired == get_number_of_expired_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_assigned == get_number_of_provisioned_and_assigned_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_available == get_number_of_available_assignments(
            meta_data_handler, meta_data, ou_related
        )

        # expire one of the licenses and check the counts again
        o = license_handler.get_udm_license_by_code(to_expire.license_code)
        o._orig_udm_object.lo.modify(
            o.dn, [("bildungsloginValidityEndDate", o.props.validity_end_date, "2000-01-01")]
        )
        num_of_newly_expired_licenses = (
            license_quantity - num_students
        )  # we assign num_students to each license so the number of expired licenses should be
        #    our quantity minus the number of assigned students

        expected_count_expired = expected_count_expired + num_of_newly_expired_licenses
        expected_count_available = expected_count_available - num_of_newly_expired_licenses

        assert expected_count_aquired == get_total_number_of_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_expired == get_number_of_expired_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_assigned == get_number_of_provisioned_and_assigned_assignments(
            meta_data_handler, meta_data, ou_related
        )
        assert expected_count_available == get_number_of_available_assignments(
            meta_data_handler, meta_data, ou_related
        )


def test_number_of_provisioned_and_assigned_licenses(
    license_handler,
    meta_data_handler,
    assignment_handler,
    meta_data,
    license_obj,
    hostname,
):
    """Test the number of provisioned licenses is included in the number of assigned licenses"""
    num_students = 3
    num_teachers = 3
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
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
        num_assigned = get_number_of_provisioned_and_assigned_assignments(meta_data_handler, meta_data)
        assert num_assigned == num_students + num_teachers
        for user_name in users[:2]:
            assignment_handler.change_license_status(
                username=user_name,
                license_code=license.license_code,
                status=Status.PROVISIONED,
            )
        # ou is case insensitive. Because there is only one license, the number is the same if
        # no school is passed.
        for ou_name in (None, ou, ou.upper(), ou.swapcase()):
            num_assigned = get_number_of_provisioned_and_assigned_assignments(
                meta_data_handler, meta_data, ou_name
            )
            assert num_assigned == num_students + num_teachers
        # after provisioning the code to some users, the number should still be the same.
        num_assigned = get_number_of_provisioned_and_assigned_assignments(meta_data_handler, meta_data)
        assert num_assigned == num_students + num_teachers
        # the number of available licenses for this product should be the total number - the number
        # of users which just got the license for this product
        total_num = get_total_number_of_assignments(meta_data_handler, meta_data)
        assert get_number_of_available_assignments(meta_data_handler, meta_data) == total_num - len(
            users
        )


def test_number_of_expired_licenses(
    license_handler, meta_data_handler, meta_data, n_expired_licenses, hostname
):
    """Test the number of expired licenses is as expected"""
    total_amount_of_licenses_for_product = 0
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        # an assignment is not expired if end_date + duration < today
        for lic in n_expired_licenses(ou):
            lic.product_id = meta_data.product_id
            license_handler.create(lic)
            total_amount_of_licenses_for_product += license_handler.get_number_of_expired_assignments(
                lic
            )
        assert (
            get_number_of_expired_assignments(meta_data_handler, meta_data)
            == total_amount_of_licenses_for_product
        )


@pytest.mark.xfail(reason="Not implemented yet.")
def test_get_all():
    raise NotImplementedError("Missing test for MetadataHandler.get_all()")
