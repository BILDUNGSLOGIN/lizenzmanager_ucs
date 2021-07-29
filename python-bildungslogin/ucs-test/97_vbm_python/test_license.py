import pytest


from univention.bildungslogin.handler import LicenseHandler, BiloCreateError


def test_create(licence_handler, random_license):
    licence_handler.create(random_license)
    # todo check assignments were created
    # todo check license was created
    # licenses are unique, duplicates produce errors
    with pytest.raises(BiloCreateError):
        licence_handler.create(random_license)


def test_get_number_of_available_licenses(licence_handler, random_license):
    licence_handler.create(random_license)
    assert licence_handler.get_number_of_available_licenses(random_license) == random_license.license_quantity


def test_number_of_provisioned_and_assigned_licenses(licence_handler, assignment_handler, random_license):
    # change some assignment stati to assigned and some to provisioned
    licence_handler.create(random_license)
    # create some users
    # assignment_handler.change_license_status(random_license.license_code, username, Status.ASSIGNED)
    # assignment_handler.change_license_status(random_license.license_code, username, Status.PROVISIONED)
    pass
#
#
# def test_number_of_expired_licenses(licence_handler, random_license):
#     pass
#
#
#
# def test_number_of_licenses(licence_handler, random_license):
#     licence_handler.create(random_license)
#     # todo change some stati
#
#
# def test_get_assignments_for_license(licence_handler, random_license):
#     licence_handler.create(random_license)
#     # dafuer brauche ich eine dn
#     # licence_handler.get_assignments_for_license()

def test_get_meta_data_for_license():
    pass

def test_get_time_of_last_assignment():
    pass