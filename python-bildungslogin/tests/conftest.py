import pytest


@pytest.fixture()
def license_provider():
    return "abc"


@pytest.fixture()
def license_code(provider):
    return "{}-{}".format(provider, "asdf-adf-g9")


@pytest.fixture()
def product_id():
    return "xyz"


@pytest.fixture()
def dummy_license(license_code, license_provider):
    license = License(license_code,
                product_id,
                licence_quantity,
                licence_provider,
                purchasing_date,
                utilization_systems,
                validity_start_date,
                validity_end_date,
                validity_duration,
                licence_special_type,
                ignored_for_display,
                delivery_date,
        "DEMOSCHOOL")
    return licence

