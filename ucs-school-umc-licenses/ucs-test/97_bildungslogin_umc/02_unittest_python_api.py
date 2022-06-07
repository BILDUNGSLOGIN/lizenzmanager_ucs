import pytest
from univention.management.console.modules.licenses import Instance


@pytest.mark.parametrize("pickup_number,school,expected_pickup_number", [
    ("123-123-123-123", "demo", "123-123-123-123"),
    (" 123-123-123-123", "demo", "123-123-123-123"),
    ("123-123-123-123 ", "demo", "123-123-123-123"),
])
def test_get_license(mock, pickup_number, school, expected_pickup_number):
    """ Test the behaviour of the get_license method """
    # Prepare mocks
    request_mock = mock.Mock(id="dummy_id",
                             options={"pickUpNumber": pickup_number,
                                      "school": school})
    license_handler = mock.Mock()
    licenses = [mock.Mock(), mock.Mock()]
    file_mock = mock.Mock()
    license_data_mock = mock.Mock()

    mock.patch("univention.management.console.modules.licenses.LicenseHandler",
               return_value=license_handler)
    load_license_file_mock = mock.patch(
        "univention.management.console.modules.licenses.load_license_file",
        return_value=licenses)
    import_license_mock = mock.patch(
        "univention.management.console.modules.licenses.import_license")
    finished_mock = mock.patch(
        "univention.management.console.modules.licenses.Instance.finished")

    license_handler.retrieve_license_data.return_value = (file_mock, license_data_mock)
    # Call
    Instance().get_license(request_mock)
    # Check
    license_handler.retrieve_license_data.assert_called_once_with(expected_pickup_number)
    load_license_file_mock.assert_called_once_with(file_mock, school)
    assert import_license_mock.call_count == len(licenses)
    import_license_mock.assert_has_calls(mock.call(license_handler, l) for l in licenses)
    finished_mock.assert_called_once_with("dummy_id", {
        "pickup": expected_pickup_number,
        "school": school,
        "licenses": license_data_mock
    })
