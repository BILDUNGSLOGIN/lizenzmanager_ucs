import pytest


@pytest.fixture()
def licence_provider():
    return "abc"


@pytest.fixture()
def licence_code(provider):
    return "{}-{}".format(provider, "asdf-adf-g9")


@pytest.fixture()
def product_id():
    return "xyz"


@pytest.fixture()
def dummy_licence(licence_code, licence_provider):
    licence = Licence(licence_code,
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

