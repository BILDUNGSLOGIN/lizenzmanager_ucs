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
## desc: Test the cli bilo metadata import
## exposure: dangerous
## tags: [bildungslogin]
## roles: [domaincontroller_master, domaincontroller_backup]
## packages: [python-bildungslogin, udm-bildungslogin-encoders]

import datetime
import time
from typing import Any, Dict, List

import pytest

from univention.bildungslogin.exceptions import BiloCreateError, BiloProductNotFoundError
from univention.bildungslogin.handlers import MetaDataHandler
from univention.bildungslogin.media_import import (
    AuthError,
    MediaImportError,
    cmd_media_import,
    import_single_media_data,
    load_media,
    retrieve_media_feed,
)

# TODO test the actual cli tool
from univention.bildungslogin.media_import.cmd_media_import import (
    ScriptError,
    get_access_token,
    get_config,
    get_config_from_file,
    import_all_media_data,
    import_multiple_raw_media_data,
    parse_args,
    retrieve_media_data,
)

TEST_PRODUCT_ID_1 = "urn:univentiontest:medium:1234567890"
TEST_PRODUCT_ID_2 = "urn:univentiontest:medium:0987654321"
TEST_META_DATA = [
    {
        "author": None,
        "cover": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B160_X2.png",
        "cover_small": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B110_X2.png",
        "description": "Entdecken und verstehen - Schülerbuch als E-Book - 7. Schuljahr",
        "modified": datetime.date(2021, 8, 6),
        "product_id": TEST_PRODUCT_ID_1,
        "publisher": "Cornelsen",
        "title": "Entdecken und verstehen",
    },
    {
        "author": None,
        "cover": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B160_X2.png",
        "cover_small": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B110_X2.png",
        "description": "Entdecken und verstehen 2 - Schülerbuch als E-Book - 8. Schuljahr",
        "modified": datetime.date(2021, 8, 6),
        "product_id": TEST_PRODUCT_ID_2,
        "publisher": "Cornelsen",
        "title": "Entdecken und verstehen 2",
    },
]


class ArgsMock:
    product_ids = [TEST_PRODUCT_ID_1, TEST_PRODUCT_ID_2]


def get_config_mock(*args, **kwargs):  # type: (*Any, **Any) -> Dict[str, Any]
    return {
        "client_id": None,
        "client_secret": None,
        "scope": None,
        "auth_server": None,
        "resource_server": None,
    }


def meta_data_rest_api_mock(meta_data):  # type: (List[Dict[str, Any]]) -> List[Dict[str, Any]]
    return [
        {
            "status": 200,
            "query": {"id": md["product_id"]},
            "data": {
                "publisher": md["publisher"],
                "coverSmall": {
                    "href": md["cover_small"],
                    "rel": "src",
                },
                "description": md["description"],
                "title": md["title"],
                "author": "",
                "cover": {
                    "href": md["cover"],
                    "rel": "src",
                },
                "modified": int(
                    time.mktime(
                        datetime.datetime(
                            md["modified"].year, md["modified"].month, md["modified"].day
                        ).utctimetuple()
                    )
                    - time.timezone
                )
                * 1000,
                "id": md["product_id"],
            },
        }
        for md in meta_data
    ]


def retrieve_media_data_mock(*args, **kwargs):  # type: (*Any, **Any) -> List[Dict[str, Any]]
    return meta_data_rest_api_mock(TEST_META_DATA)


def parse_args_mock(*args, **kwargs):
    return ArgsMock()


@pytest.fixture
def delete_metadata_after_test(lo):
    product_ids = []

    def _func(product_id):  # type: (str) -> None
        product_ids.append(product_id)

    yield _func

    for product_id in product_ids:
        mh = MetaDataHandler(lo)
        try:
            obj = mh.get_meta_data_by_product_id(product_id)
            obj.delete()
            print("Deleted metadata {!r}.".format(product_id))
        except BiloProductNotFoundError:
            pass


def test_cli_import(delete_metadata_after_test, lo, mocker):
    """Test that a meta data import is possible."""
    mocker.patch.object(cmd_media_import, "get_config", get_config_mock)
    mocker.patch.object(cmd_media_import, "parse_args", parse_args_mock)
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.retrieve_media_data",
        retrieve_media_data_mock,
    )
    mocker.patch("univention.bildungslogin.media_import.cmd_media_import.get_access_token")
    mh = MetaDataHandler(lo)
    delete_metadata_after_test(TEST_PRODUCT_ID_1)
    delete_metadata_after_test(TEST_PRODUCT_ID_2)
    cmd_media_import.main()
    udm_metadata = mh.get_meta_data_by_product_id(TEST_PRODUCT_ID_1)
    metadata = mh.from_udm_obj(udm_metadata)
    assert metadata.__dict__ == TEST_META_DATA[0]


def test_repeated_cli_import(delete_metadata_after_test, lo, mocker):
    """
    Test that importing multiple times the same meta data is possible and the LDAP object will only be
    updated.
    """
    mocker.patch.object(cmd_media_import, "get_config", get_config_mock)
    mocker.patch.object(cmd_media_import, "parse_args", parse_args_mock)
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.retrieve_media_data",
        retrieve_media_data_mock,
    )
    mocker.patch("univention.bildungslogin.media_import.cmd_media_import.get_access_token")
    delete_metadata_after_test(TEST_PRODUCT_ID_1)
    delete_metadata_after_test(TEST_PRODUCT_ID_2)
    cmd_media_import.main()
    filter_s = "(&(objectClass=bildungsloginMetaData)(bildungsloginProductId={}))".format(
        TEST_PRODUCT_ID_1
    )
    entry_uuids = lo.searchDn(filter_s)
    assert len(entry_uuids) == 1
    entry_uuid1 = entry_uuids[0]
    cmd_media_import.main()
    entry_uuids = lo.searchDn(filter_s)
    assert len(entry_uuids) == 1
    entry_uuid2 = entry_uuids[0]
    assert entry_uuid1 == entry_uuid2
    cmd_media_import.main()
    entry_uuids = lo.searchDn(filter_s)
    assert len(entry_uuids) == 1
    entry_uuid3 = entry_uuids[0]
    assert entry_uuid1 == entry_uuid3


def test_import_single_media_data_raises_media_import_error(mocker, lo):
    """Test that a meta data import raises the correct error when an exception
    is raised in the MetaDataHandler."""
    mocker.patch("univention.bildungslogin.handlers.MetaDataHandler.create", side_effect=BiloCreateError)
    mh = MetaDataHandler(lo)
    single_media_data = meta_data_rest_api_mock(TEST_META_DATA)[0]
    delete_metadata_after_test(TEST_PRODUCT_ID_1)
    with pytest.raises(MediaImportError):
        import_single_media_data(meta_data_handler=mh, raw_media_data=single_media_data)


def test_import_multiple_raw_media_data_raises_media_import_error(mocker, lo):
    """Test that a meta data import does not raise errors if exceptions are raised
    in MetaDataHandler, but the errors are returned as strings."""
    mocker.patch(
        "univention.bildungslogin.handlers.MetaDataHandler.create",
        side_effect=[BiloCreateError, BiloCreateError],
    )
    mh = MetaDataHandler(lo)
    multiple_media_data = meta_data_rest_api_mock(TEST_META_DATA)
    delete_metadata_after_test(TEST_PRODUCT_ID_1)
    delete_metadata_after_test(TEST_PRODUCT_ID_2)
    error_message = import_multiple_raw_media_data(
        meta_data_handler=mh, raw_media_data=multiple_media_data
    )
    for raw_data in multiple_media_data:
        assert raw_data["query"]["id"] in error_message


def test_import_multiple_raw_media_data_raises_MediaNotFoundError(mocker, lo):
    """Test that a meta data import does not raise errors if exceptions are raised
    in MetaDataHandler, but the errors are returned as strings if the media can't be found."""
    mh = MetaDataHandler(lo)
    multiple_media_data = meta_data_rest_api_mock(TEST_META_DATA)
    multiple_media_data[0]["status"] = 404
    delete_metadata_after_test(TEST_PRODUCT_ID_1)
    delete_metadata_after_test(TEST_PRODUCT_ID_2)
    error_message = import_multiple_raw_media_data(
        meta_data_handler=mh, raw_media_data=multiple_media_data
    )
    assert multiple_media_data[0]["query"]["id"] in error_message
    assert multiple_media_data[1]["query"]["id"] not in error_message


def test_import_all_media_data_raises_script_error(mocker, lo):
    """Test that a ScriptError is thrown at the top level of the import,
    if an error was raised in MetaDataHandler."""
    mocker.patch.object(cmd_media_import, "get_config", get_config_mock)
    mocker.patch.object(cmd_media_import, "parse_args", parse_args_mock)
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.retrieve_media_data",
        retrieve_media_data_mock,
    )
    mocker.patch("univention.bildungslogin.media_import.cmd_media_import.get_access_token")
    mocker.patch("univention.bildungslogin.handlers.MetaDataHandler.create", side_effect=BiloCreateError)
    delete_metadata_after_test(TEST_PRODUCT_ID_1)
    delete_metadata_after_test(TEST_PRODUCT_ID_2)
    with pytest.raises(ScriptError) as exc:
        import_all_media_data(
            **{
                "client_id": None,
                "client_secret": None,
                "scope": None,
                "auth_server": None,
                "resource_server": None,
                "lo": lo,
                "product_ids": [TEST_PRODUCT_ID_1, TEST_PRODUCT_ID_2],
            }
        )
        assert TEST_PRODUCT_ID_1 in exc.value


def test_main_raises_script_error(mocker):
    """Test that ScriptErrors, which are thrown during the import, do not lead to
    a fail of the import. Other exceptions should fail, because they are not expected."""
    mocker.patch.object(cmd_media_import, "get_config", get_config_mock)
    mocker.patch.object(cmd_media_import, "parse_args", parse_args_mock)
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.retrieve_media_data",
        retrieve_media_data_mock,
    )
    mocker.patch("univention.bildungslogin.media_import.cmd_media_import.get_access_token")
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.import_all_media_data",
        side_effect=ScriptError,
    )
    # import should not fail for ScriptErrors
    cmd_media_import.main()
    # import should fail for other errors
    with pytest.raises(Exception):
        mocker.patch(
            "univention.bildungslogin.media_import.cmd_media_import.import_all_media_data",
            side_effect=Exception,
        )
        cmd_media_import.main()


def test_retrieve_media_data(mocker):
    """Test if the function retrieve_media_data can be called. It will raise an
    error if no product id is passed."""
    mocker.patch("univention.bildungslogin.media_import.requests.post")
    retrieve_media_data("", "", [TEST_PRODUCT_ID_1])
    with pytest.raises(TypeError):
        retrieve_media_data("", "", None)


def test_retrieve_media_feed(mocker):
    """Test if the function test_retrieve_media_feed can be called
    without raising any errors."""
    mocker.patch("univention.bildungslogin.media_import.requests.post")
    retrieve_media_feed("", "", 1)


def test_get_access_token(mocker):
    """When requesting an access token the format should be as expected."""

    class dummy_response(dict):
        status_code = 200

        def json(self):
            return {"access_token": "expected_token", "error_description": "expected_error"}

    mocker.patch("univention.bildungslogin.media_import.requests.post", dummy_response)
    res = get_access_token("", "", "", "")
    assert res == "expected_token"
    with pytest.raises(AuthError):
        dummy_response.status_code = 404
        get_access_token("", "", "", "")


def test_get_config_from_file():
    """The media import should raise a ScriptError if the file does not exist
    and not fail with or provided config.ini."""
    with pytest.raises(ScriptError):
        get_config_from_file("non-existent-file")
    get_config_from_file("/etc/bildungslogin/config.ini")


def test_get_config_calls_get_config_from_file(mocker):
    """The media import should call get_config_from_file if config_file is passed."""
    mock_get_config_from_file = mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.get_config_from_file"
    )
    args = parse_args(
        [
            "--config-file",
            "mock-file",
            "--client-id",
            None,
            "--auth-server",
            "localhost",
            "--resource-server",
            "localhost",
            TEST_PRODUCT_ID_1,
        ]
    )
    get_config(args)
    mock_get_config_from_file.assert_called_once_with("mock-file")


@pytest.mark.parametrize(
    "required_field,required_value",
    [("--client-id", "some-client-id"), ("--scope", "some-scope"), ("--client-secret", "secret")],
)
def test_get_config_exit_if_missing_args(required_field, required_value):
    """The media import should exit if a required argument is missing."""
    args = [
        "--client-id",
        "some-client-id",
        "--scope",
        "some-scope",
        "--client-secret",
        "secret",
        TEST_PRODUCT_ID_1,
    ]
    args.remove(required_field)
    args.remove(required_value)
    args = parse_args(args)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        get_config(args)
        assert pytest_wrapped_e.value.code == 1


@pytest.mark.parametrize("error", [KeyError, ValueError])
def test_load_media_raises_MediaImportError(mocker, error):
    mocker.patch("univention.bildungslogin.models.MetaData.__init__", side_effect=KeyError)
    single_media_data = meta_data_rest_api_mock(TEST_META_DATA)[0]
    with pytest.raises(MediaImportError):
        load_media(single_media_data)
