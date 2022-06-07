# -*- coding: utf-8 -*-
import tempfile
from copy import deepcopy

import pytest
from jsonschema import ValidationError, validate
from mock import Mock, mock_open, patch
from typing import List, Optional, Type

from univention.bildungslogin.exceptions import AuthError, BiloServerError, LicenseNotFoundError, \
    LicenseSaveError, LicenseValidationError, ScriptError
from univention.bildungslogin.license_retrieval import LICENSE_RETRIEVAL_SCHEMA, \
    confirm_licenses_package, get_access_token, \
    retrieve_licenses_package, save_license_package_to_json
from univention.bildungslogin.license_retrieval.cmd_license_retrieval import get_config, \
    get_config_from_file, parse_args, \
    retrieve_licenses

test_license_package_raw = {
    "licenses": [
        {
            "lizenzcode": "WES-TEST-CODE-LZL18",
            "product_id": "urn:bilo:medium:WEB-14-124227",
            "lizenzanzahl": 60,
            "lizenzgeber": "WES",
            "kaufreferenz": "Testcode ohne Medienzugriff",
            "nutzungssysteme": "Antolin",
            "gueltigkeitsbeginn": "",
            "gueltigkeitsende": "30-08-2021",
            "gueltigkeitsdauer": "Schuljahreslizenz",
            "sonderlizenz": ""
        },
        {
            "lizenzcode": "WES-TEST-CODE-LZL19",
            "product_id": "urn:bilo:medium:WEB-14-124227",
            "lizenzanzahl": 10,
            "lizenzgeber": "WES",
            "kaufreferenz": "Lizenzmanager-Testcode",
            "nutzungssysteme": "Testcode ohne Medienzugriff",
            "gueltigkeitsbeginn": "",
            "gueltigkeitsende": "",
            "gueltigkeitsdauer": "Schuljahreslizenz",
            "sonderlizenz": "Lehrkraft"
        }
    ],
    "package_id": "VHT-123-123-123"
}


def test_license_schema():
    """Test that the schema works with our sample test_license_package_raw.
    We assume the test_license_package_raw to be valid"""
    validate(instance=test_license_package_raw, schema=LICENSE_RETRIEVAL_SCHEMA)


@pytest.mark.parametrize(
    "field_name",
    ["licenses", "package_id"],
)
def test_license_schema_validation_required_fails(field_name):
    """All fields have to be present at least. A missing value in the license package should raise a ValidationError"""
    test_license_broken = deepcopy(test_license_package_raw)
    del test_license_broken[field_name]
    with pytest.raises(ValidationError):
        validate(instance=test_license_broken, schema=LICENSE_RETRIEVAL_SCHEMA)


@pytest.mark.parametrize(
    "field_name",
    ["lizenzcode", "product_id", "lizenzanzahl", "lizenzgeber"],
)
def test_license_schema_validation_required_fails2(field_name):
    """All fields have to be present at least within the licenses.
    A missing value in the license should raise a ValidationError"""
    test_license_broken = deepcopy(test_license_package_raw)
    del test_license_broken["licenses"][0][field_name]
    with pytest.raises(ValidationError):
        validate(instance=test_license_broken, schema=LICENSE_RETRIEVAL_SCHEMA)


@patch('json.dump')
@patch('__builtin__.open', new_callable=mock_open())
def test_save_data_to_file(m, m_json):
    save_license_package_to_json(test_license_package_raw, test_license_package_raw['package_id'])

    # assertion that open was called
    m.assert_called_with('/usr/shared/bildungslogin/license_package-VHT-123-123-123.json', 'w')

    # assert that m_json is called with the correct license package
    m_json.assert_called_with(test_license_package_raw['licenses'], m.return_value.__enter__.return_value)


@patch("requests.post")
def test_get_access_token(post_mock):
    # type: (Mock) -> None
    """ Test the behaviour of the get_access_token function """

    # Valid response
    post_mock.return_value = Mock(**{
        "status_code": 200,
        "json.return_value": {"access_token": "expected_token"}
    })
    res = get_access_token("", "", "", "")
    assert res == "expected_token"

    # Invalid response
    post_mock.return_value = Mock(**{
        "status_code": 404,
        "json.return_value": {"error_description": "expected_error"}
    })
    with pytest.raises(AuthError) as context:
        get_access_token("", "", "", "")
    assert context.value.message == "Authorization failed: expected_error"


# Test cases for test_retrieve_licenses_package in the format of:
# - Response code (int)
# - Expected exception (Exception or None)
# - Expected exception message (str or None)
retrieve_licenses_package_cases = [
    (200, None, None),
    (208, None, None),
    (200, LicenseValidationError, ("Downloaded json does not conform "
                                   "to required json format: validation error")),
    (208, LicenseValidationError, ("Downloaded json does not conform "
                                   "to required json format: validation error")),
    (404, LicenseNotFoundError, ("404: No license package found for the transferred "
                                 "pickup number: dummy_pickup_number")),
    (500, BiloServerError, "Please check with Bildungslogin and try again"),
    (231, BiloServerError, "Unknown status code: 231"),
]


@pytest.mark.parametrize("response_code,expected_exception,expected_message",
                         retrieve_licenses_package_cases)
@patch("requests.get")
@patch("univention.bildungslogin.license_retrieval.validate")
def test_retrieve_licenses_package(validate_mock, get_mock, response_code,
                                   expected_exception, expected_message):
    # type: (Mock, Mock, int, Optional[Exception], Optional[str]) -> None
    """ Test the behaviour of the retrieve_licenses_package function """
    # Init values
    response_json = "dummy_json"
    # Init mocks
    get_mock.return_value = Mock(**{
        "status_code": response_code,
        "json.return_value": response_json})
    if expected_exception == LicenseValidationError:
        validate_mock.side_effect = ValidationError("validation error")

    # Run the case depending on whether we expect an exception or not
    if expected_exception:
        with pytest.raises(expected_exception) as context:
            retrieve_licenses_package("dummy_token", "dummy_server", "dummy_pickup_number")
        assert context.value.message == expected_message
    else:
        output = retrieve_licenses_package("dummy_token", "dummy_server", "dummy_pickup_number")
        assert output == (response_code, response_json)

    # Check that request.get was called with correct parameters
    get_mock.assert_called_once_with(
        url="dummy_server/external/publisher/v2/licensepackage",
        data={"package_id": "dummy_pickup_number"},
        headers={"Authorization": "Bearer dummy_token",
                 "Content-Type": "application/x-www-form-urlencoded"})

    # Check the call to validate function
    if expected_exception in [None, LicenseValidationError]:
        validate_mock.assert_called_once_with(instance=response_json,
                                              schema=LICENSE_RETRIEVAL_SCHEMA)
    else:
        validate_mock.assert_not_called()


# test_confirm_licenses_package cases in the following format:
# - response code
# - expected raised exception
# - expected exception message
test_confirm_licenses_package_cases = [
    (200, None, None),
    (409, None, None),
    (404, LicenseNotFoundError, "404: No license package found for "
                                "the transferred pickup number: dummy_pickup_number"),
    (231, BiloServerError, "Unknown status code: 231"),
]
@pytest.mark.parametrize("response_code,expected_exception,expected_message",
                         test_confirm_licenses_package_cases)
@patch("requests.post")
def test_confirm_licenses_package(post_mock, response_code, expected_exception, expected_message):
    # type: (Mock, int, Optional[Exception], Optional[str]) -> None
    """ Test the behaviour of the confirm_licenses_package function """
    # Prepare mock
    post_mock.return_value = Mock(status_code=response_code)

    # Call the confirm_licenses_package
    if expected_exception:
        with pytest.raises(expected_exception) as context:
            confirm_licenses_package("dummy_token", "dummy_server", "dummy_pickup_number")
        assert context.value.message == expected_message
    else:
        output = confirm_licenses_package("dummy_token", "dummy_server", "dummy_pickup_number")
        assert output == response_code

    # Check the call to requests.post
    post_mock.assert_called_once_with(
        "dummy_server/external/publisher/v2/licensepackage/confirm",
        data={"package_id": "dummy_pickup_number"},
        headers={
            "Authorization": "Bearer dummy_token",
            "Content-Type": "application/x-www-form-urlencoded",
        })


def test_parse_args():
    # type: () -> None
    """ Test the behaviour of the parse_args function """

    # Valid args
    args = parse_args(["--pickup-number", "1", "--school", "2"])
    assert args.pickup_number == "1"
    assert args.school == "2"
    assert args.config_file is None

    # Valid args + Optional
    args = parse_args(["--pickup-number", "1", "--school", "2", "--config-file", "3"])
    assert args.pickup_number == "1"
    assert args.school == "2"
    assert args.config_file == "3"

    # Raises when missing required parameter
    with pytest.raises(SystemExit):
        parse_args(["--pickup-number", "1"])

    # Raises when no parameter provided
    with pytest.raises(SystemExit):
        parse_args()


@patch("univention.bildungslogin.license_retrieval.cmd_license_retrieval.confirm_licenses_package")
@patch("univention.bildungslogin.license_retrieval.cmd_license_retrieval.save_license_package_to_json")
@patch("univention.bildungslogin.license_retrieval.cmd_license_retrieval.retrieve_licenses_package")
@patch("univention.bildungslogin.license_retrieval.cmd_license_retrieval.get_access_token")
@patch("univention.bildungslogin.license_retrieval.cmd_license_retrieval.get_config_from_file")
def test_retrieve_licenses(get_config_mock, get_token_mock,
                           retrieve_package_mock, save_package_mock,
                           confirm_license_mock):
    # type: (Mock, Mock, Mock, Mock, Mock) -> None
    """ Test the behaviour of the retrieve_licenses function """

    # Mocks defined in the order of them being called in retrieve_licenses function
    mocks = [get_config_mock, get_token_mock,
             retrieve_package_mock, save_package_mock,
             confirm_license_mock]

    license_response = {"licenses": "dummy_licenses"}
    pickup_number = "dummy_pickup_number"

    def _init_mocks():
        """ Reset mocks and init them with valid values """
        for mock in mocks:
            mock.reset_mock()
            mock.return_value = None
            mock.side_effect = None
        get_config_mock.return_value = {
            key: "dummy_{}".format(key) for key in
            ["client_id", "client_secret", "scope", "auth_server", "resource_server"]
        }
        get_token_mock.return_value = "dummy_token"
        retrieve_package_mock.return_value = (200, license_response)
        save_package_mock.return_value = "dummy_path"
        confirm_license_mock.return_value = 200

    ### Case with valid inputs ###
    _init_mocks()
    output = retrieve_licenses(config=None, pickup_number=pickup_number)
    assert output == ("dummy_path", "dummy_licenses")
    get_config_mock.assert_called_once_with("/etc/bildungslogin/config.ini")
    get_token_mock.assert_called_once_with("dummy_client_id", "dummy_client_secret",
                                           "dummy_scope", "dummy_auth_server")
    retrieve_package_mock.assert_called_once_with("dummy_token", "dummy_resource_server",
                                                  pickup_number)
    save_package_mock.assert_called_once_with(license_response, pickup_number)
    confirm_license_mock.assert_called_once_with("dummy_token", "dummy_resource_server",
                                                 pickup_number)

    def _test_exception(mock, expected_exception=Exception, expected_message="dummy error"):
        # type: (Mock, Type[Exception], str) -> None
        """ Test case when given mock raises an exception """
        _init_mocks()
        mock.side_effect = Exception("dummy error")
        with pytest.raises(expected_exception) as context:
            retrieve_licenses(config=None, pickup_number="")
        assert context.value.message == expected_message
        # Check that no other mock was called
        for mock in mocks[mocks.index(mock)+1:]:
            mock.assert_not_called()

    ### Cases when mocks raise errors ###
    _test_exception(get_config_mock)
    _test_exception(get_token_mock, AuthError, "Unable to get access: dummy error")
    _test_exception(retrieve_package_mock)
    _test_exception(save_package_mock, LicenseSaveError,
                    "Unable to save license as a json: dummy error")
    _test_exception(confirm_license_mock)

    ### Case when "retrieve" and "confirm" endpoints return unlikely response codes ###
    _init_mocks()
    confirm_license_mock.return_value = 409
    with pytest.raises(BiloServerError) as context:
        retrieve_licenses(config=None, pickup_number=pickup_number)
    assert context.value.message == "Server error: New license was already confirmed"


@pytest.mark.parametrize("fields,expect_success", [
    ([], False),
    (["client_id"], False),
    (["client_id", "client_secret"], False),
    (["client_id", "client_secret", "scope"], True),
    (["client_id", "client_secret", "scope", "additional_field"], True),
])
@patch("univention.bildungslogin.license_retrieval.cmd_license_retrieval.get_config_from_file")
def test_get_config(get_config_mock, fields, expect_success):
    # type: (Mock, List[str], bool) -> None
    """ Test the behaviour of the get_config function """
    expected_config = {key: "dummy value" for key in fields}
    get_config_mock.return_value = expected_config.copy()

    if expect_success:
        config = get_config(Mock(config_file="dummy file"))
        assert config == expected_config
    else:
        with pytest.raises(SystemExit) as context:
            get_config(Mock(config_file="dummy file"))
        assert context.value.message == 1
    get_config_mock.assert_called_once_with("dummy file")


def test_get_config_from_file():
    # type: () -> None
    """ Test the behaviour of the get_config_from_file function """

    valid_config_structure = {
        "Auth": {
            "ClientId": "dummy_client_id",
            "ClientSecret": "dummy_client_secret",
            "Scope": "dummy_scope",
        },
        "APIEndpoint": {
            "AuthServer": "dummy_auth_server",
            "ResourceServer": "dummy_resource_server",
        }
    }

    def _create_config_file(config_file, config_structure):
        lines = []
        for section, content in config_structure.items():
            lines.append("[{}]\n".format(section))
            for key, value in content.items():
                lines.append("{} = {}\n".format(key, value))
        config_file.writelines(lines)
        config_file.seek(0)

    # Valid case
    with tempfile.NamedTemporaryFile(mode="r+") as tmp_file:
        _create_config_file(tmp_file, valid_config_structure)
        config = get_config_from_file(tmp_file.name)
        assert config == {
            "client_id": "dummy_client_id",
            "client_secret": "dummy_client_secret",
            "scope": "dummy_scope",
            "auth_server": "dummy_auth_server",
            "resource_server": "dummy_resource_server",
        }

    # Valid case with additional fields in the config file
    with tempfile.NamedTemporaryFile(mode="r+") as tmp_file:
        config_structure = deepcopy(valid_config_structure)
        config_structure["Auth"]["Extra1"] = "Test"
        config_structure["Extra"] = {"Extra2": "Test"}
        _create_config_file(tmp_file, config_structure)
        config = get_config_from_file(tmp_file.name)
        assert config == {
            "client_id": "dummy_client_id",
            "client_secret": "dummy_client_secret",
            "scope": "dummy_scope",
            "auth_server": "dummy_auth_server",
            "resource_server": "dummy_resource_server",
        }

    # Valid case with missing fields
    with tempfile.NamedTemporaryFile(mode="r+") as tmp_file:
        config_structure = deepcopy(valid_config_structure)
        del(config_structure["Auth"]["ClientId"])
        del(config_structure["APIEndpoint"])
        _create_config_file(tmp_file, config_structure)
        config = get_config_from_file(tmp_file.name)
        assert config == {
            "client_secret": "dummy_client_secret",
            "scope": "dummy_scope",
        }

    # Empty file
    with tempfile.NamedTemporaryFile(mode="r+") as tmp_file:
        _create_config_file(tmp_file, {})
        config = get_config_from_file(tmp_file.name)
        assert config == {}

    # File doesn't exist
    with pytest.raises(ScriptError) as context:
        get_config_from_file("/dummy.ini")
    assert "Failed to load config from '/dummy.ini':" in context.value.message


# def test_():
#     # type: () -> None
#     """ Test the behaviour of the  function """
