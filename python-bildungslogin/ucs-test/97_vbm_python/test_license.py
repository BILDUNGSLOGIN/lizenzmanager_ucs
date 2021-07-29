import pytest


from univention.bildungslogin.handler import LicenseHandler, BiloCreateError


def test_create(licence_handler, random_license):
    licence_handler.create(random_license)
    # todo check assignments were created
    # todo check license was created
    # licenses are unique, duplicates produce errors
    with pytest.raises(BiloCreateError) as exc:
        licence_handler.create(random_license)


def test_get_number_of_available_licenses(licence_handler, random_license):
    # todo create a random number of licenses
    licence_handler.create(random_license)
    assert licence_handler.get_number_of_available_licenses(random_license) == random_license.license_quantity


#
#
# def test_number_of_provisioned_and_assigned_licenses():
#     pass
#
#
# def test_number_of_expired_licenses():
#     pass
#
#
# def test_number_of_licenses():
#     pass
#
#
#
#
def test_get_assignments_for_license(licence_handler, random_license):
    licence_handler.create(random_license)
    # dafuer brauche ich eine dn
    # licence_handler.get_assignments_for_license()
