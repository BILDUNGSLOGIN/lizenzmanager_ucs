# -*- coding: utf-8 -*-
import itertools
from hashlib import sha256

import pytest

import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.utils import Status
from univention.testing.utils import verify_ldap_object


def test_create_meta_data(meta_data_handler, random_meta_data, ldap_base):
    cn = sha256(random_meta_data.product_id).hexdigest()
    expected_attr = {
        "cn": [cn],
        "vbmProductId": [random_meta_data.product_id],
        "vbmMetaDataTitle": [random_meta_data.title],
        "vbmMetaDataDescription": [random_meta_data.description],
        "vbmMetaDataAuthor": [random_meta_data.author],
        "vbmMetaDataPublisher": [random_meta_data.publisher],
        "vbmMetaDataCover": [random_meta_data.cover],
        "vbmMetaDataCoverSmall": [random_meta_data.cover_small],
        "vbmMetaDataModified": [random_meta_data.modified],
    }
    meta_data_handler.create(random_meta_data)
    dn = "cn={},cn=metadata,cn=bildungslogin,cn=vbm,cn=univention,{}".format(cn, ldap_base)
    verify_ldap_object(
        dn,
        expected_attr=expected_attr,
        strict=True,
    )


def test_number_of_available_licenses(
    licence_handler, meta_data_handler, random_meta_data, random_n_random_licenses
):
    total_amount_of_licenses_for_product = 0
    for lic in random_n_random_licenses:
        # comment: we do not have to create the meta-data for this
        lic.product_id = random_meta_data.product_id
        licence_handler.create(lic)
        total_amount_of_licenses_for_product += lic.license_quantity
    assert (
        meta_data_handler.get_number_of_available_assignments(random_meta_data)
        == total_amount_of_licenses_for_product
    )


def test_number_of_provisioned_and_assigned_licenses(
    licence_handler, meta_data_handler, assignment_handler, random_meta_data, random_license
):
    # 00_vbm_test_assignments
    # the number of provisioned licenses is included in the number of assigned licenses
    num_students = 3
    num_teachers = 3
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        random_license.product_id = random_meta_data.product_id
        random_license.license_school = ou
        licence_handler.create(random_license)
        student_usernames = [schoolenv.create_student(ou)[0] for _ in range(num_students)]
        teacher_usernames = [schoolenv.create_teacher(ou)[0] for _ in range(num_teachers)]
        users = student_usernames + teacher_usernames
        assignment_handler.assign_users_to_license(
            usernames=users, licenses_code=random_license.license_code
        )
        num_assigned = meta_data_handler.get_number_of_provisioned_and_assigned_assignments(
            random_meta_data
        )
        assert num_assigned == num_students + num_teachers
        for user_name in users[:2]:
            assignment_handler.change_license_status(
                username=user_name, license_code=random_license.license_code, status=Status.PROVISIONED
            )
        # after provisioning the code to some users, the number should still be the same.
        num_assigned = meta_data_handler.get_number_of_provisioned_and_assigned_assignments(
            random_meta_data
        )
        assert num_assigned == num_students + num_teachers


@pytest.mark.skip(reason="num_expired has to be fixed in udm")
def test_number_of_expired_licenses(
    licence_handler, meta_data_handler, random_meta_data, random_n_expired_licenses
):
    total_amount_of_licenses_for_product = 0
    # a assignment is not expired if end_date + duration < today
    for lic in random_n_expired_licenses:
        lic.product_id = random_meta_data.product_id
        licence_handler.create(lic)
        total_amount_of_licenses_for_product += licence_handler.get_number_of_expired_assignments(lic)
    assert (
        meta_data_handler.get_number_of_expired_assignments(random_meta_data)
        == total_amount_of_licenses_for_product
    )


def test_total_number_of_licenses(
    licence_handler,
    meta_data_handler,
    random_meta_data,
    random_n_random_licenses,
    random_n_expired_licenses,
):
    total_amount_of_licenses_for_product = 0
    # udm: number of assignments which are not provisioned + expired
    # todo also assigned licenses
    all_licenses = [
        random_n_random_licenses,
        # random_n_expired_licenses, # comment out after fix in udm
    ]
    for lic in itertools.chain(*all_licenses):
        lic.product_id = random_meta_data.product_id
        licence_handler.create(lic)
        total_amount_of_licenses_for_product += licence_handler.get_number_of_assignments(lic)
    assert (
        meta_data_handler.get_number_of_assignments(random_meta_data)
        == total_amount_of_licenses_for_product
    )
