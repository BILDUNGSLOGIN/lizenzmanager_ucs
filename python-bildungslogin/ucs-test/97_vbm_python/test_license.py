from hashlib import sha256

import pytest

from univention.bildungslogin.handler import BiloCreateError
from univention.bildungslogin.utils import Status
from univention.testing.utils import verify_ldap_object


def test_create(lo, licence_handler, random_license, ldap_base):
    licence_handler.create(random_license)
    # check license was created
    cn = sha256(random_license.license_code).hexdigest()
    license_dn = "cn={},cn=licenses,cn=bildungslogin,cn=vbm,cn=univention{}".format(cn, ldap_base)
    expected_attr = {
        "cn": [cn],
        "vbmLicenseCode": [random_license.license_code],
        "vbmProductId": [random_license.product_id],
        "vbmLicenseQuantity": [str(random_license.license_quantity)],
        "vbmLicenseProvider": [random_license.license_provider],
        "vbmPurchasingReference": [random_license.purchasing_reference],
        "vbmUtilizationSystems": [random_license.utilization_systems],
        "vbmValidityStartDate": [random_license.validity_start_date],
        "vbmValidityEndDate": [random_license.validity_end_date],
        "vbmValidityDuration": [random_license.validity_duration],
        "vbmDeliveryDate": [random_license.delivery_date],
        "vbmLicenseSchool": [random_license.license_school],
        "vbmIgnoredForDisplay": [random_license.ignored_for_display],
    }
    if random_license.license_special_type:
        expected_attr["vbmLicenseSpecialType"] = [random_license.license_special_type]
    verify_ldap_object(
        license_dn,
        expected_attr=expected_attr,
        strict=False,
    )
    # check assignments were created
    for dn in lo.searchDn(base=license_dn, scope="one"):
        expected_attr = {"vbmAssignmentStatus": [Status.AVAILABLE]}
        verify_ldap_object(dn, expected_attr=expected_attr, strict=False)

    # licenses are unique, duplicates produce errors
    with pytest.raises(BiloCreateError):
        licence_handler.create(random_license)


def test_get_number_of_available_licenses(licence_handler, random_license):
    licence_handler.create(random_license)
    assert (
        licence_handler.get_number_of_available_assignments(random_license)
        == random_license.license_quantity
    )


def test_number_of_provisioned_and_assigned_licenses(
    licence_handler, assignment_handler, random_license
):
    # change some assignment stati to assigned and some to provisioned
    licence_handler.create(random_license)
    # create some users -> ucstest-school
    # assignment_handler.change_license_status(random_license.license_code, username, Status.ASSIGNED)
    # assignment_handler.change_license_status(random_license.license_code, username, Status.PROVISIONED)
    pass


@pytest.mark.skip(reason="num_expired has to be fixed in udm")
def test_number_of_expired_licenses(licence_handler, expired_license):
    licence_handler.create(expired_license)
    assert (
        licence_handler.get_number_of_expired_assignments(expired_license)
        == expired_license.license_quantity
    )


def test_number_of_licenses(licence_handler, random_license):
    licence_handler.create(random_license)
    assert licence_handler.get_number_of_assignments(random_license) == random_license.license_quantity
    # todo change some stati -> for this i will also need users


# def test_get_assignments_for_license(licence_handler, random_license):
#     licence_handler.create(random_license)
#     # dafuer brauche ich eine dn
#     # licence_handler.get_assignments_for_license()


def test_get_meta_data_for_license():
    pass


def test_get_time_of_last_assignment():
    pass
