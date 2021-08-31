# -*- coding: utf-8 -*-

import random
import sys
import tempfile

import pytest

if sys.version_info[0] >= 3:
    from unittest.mock import MagicMock, call, patch, sentinel
else:
    from mock import MagicMock, call, patch, sentinel

import univention.bildungslogin.media_import.cmd_media_update
from univention.bildungslogin.models import MetaData


def test_load_last_update_timestamp_no_ts_file(random_name):
    """Test load_last_update_timestamp() when no file exists"""
    assert (
        univention.bildungslogin.media_import.cmd_media_update.load_last_update_timestamp(
            "/tmp/{}".format(random_name())
        )
        == 0
    )


def test_load_last_update_timestamp_with_ts_file():
    """Test load_last_update_timestamp() when a file with a timestamp exists"""
    with tempfile.NamedTemporaryFile() as fp:
        num = random.randint(1, 10000)
        fp.write(str(num))
        fp.flush()
        assert (
            univention.bildungslogin.media_import.cmd_media_update.load_last_update_timestamp(fp.name)
            == num
        )


def test_save_last_update_timestamp():
    """Test load_last_update_timestamp() when a file with a timestamp exists"""
    with tempfile.NamedTemporaryFile() as fp:
        num = random.randint(1, 10000)
        univention.bildungslogin.media_import.cmd_media_update.save_last_update_timestamp(num, fp.name)
        fp.seek(0)
        assert fp.read() == str(num)


@patch("univention.bildungslogin.handlers.UDM")
@patch("univention.bildungslogin.media_import.cmd_media_update.save_last_update_timestamp")
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.load_last_update_timestamp", return_value=0
)
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.import_multiple_raw_media_data",
    return_value="",
)
@patch("univention.bildungslogin.media_import.cmd_media_update.retrieve_media_data")
@patch("univention.bildungslogin.media_import.cmd_media_update.retrieve_media_feed")
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.get_access_token",
    return_value=sentinel.access_token,
)
@patch("univention.bildungslogin.media_import.cmd_media_update.get_config_from_file")
@patch("univention.bildungslogin.handlers.MetaDataHandler.get_all")
def test_update_ldap_meta_data(
    get_all_mock,
    get_config_from_file_mock,
    get_access_token_mock,
    retrieve_media_feed_mock,
    retrieve_media_data_mock,
    import_multiple_raw_media_data_mock,
    load_last_update_timestamp_mock,
    save_last_update_timestamp_mock,
    udm_mock,
):
    """Test the meta data update function."""
    # product IDs in LDAP:
    p_ids = {"urn:bilo:medium:ABC-{}".format(random.randint(10000, 20000)) for _ in range(30)}
    get_all_mock.return_value = [MetaData(product_id=p_id) for p_id in p_ids]
    get_config_from_file_mock.return_value = {
        "client_id": None,
        "client_secret": None,
        "scope": None,
        "auth_server": None,
        "resource_server": None,
    }
    num_returned_p_ids = random.randint(5, 15)
    # product IDs updated on server:
    retrieve_media_feed_mock.return_value = random.sample(p_ids, num_returned_p_ids)
    # dates in meta data:
    dates = [random.randint(1, 2000) for _ in range(num_returned_p_ids)]
    raw_media_data = [{"status": 200, "data": {"modified": d}} for d in dates]
    retrieve_media_data_mock.return_value = raw_media_data
    product_ids_to_update = set(retrieve_media_feed_mock.return_value).intersection(p_ids)

    result = univention.bildungslogin.media_import.cmd_media_update.update_ldap_meta_data(MagicMock())

    assert load_last_update_timestamp_mock.called_once()
    assert get_config_from_file_mock.called_once()
    assert get_access_token_mock.called_once()
    assert retrieve_media_feed_mock.called_once()
    assert save_last_update_timestamp_mock.called_once()
    assert import_multiple_raw_media_data_mock.called_once()

    assert retrieve_media_data_mock.called
    assert retrieve_media_data_mock.call_args == call(
        sentinel.access_token, None, sorted(product_ids_to_update)
    )
    assert save_last_update_timestamp_mock.call_args == call(min(dates))
    assert result is True


@patch("univention.bildungslogin.media_import.cmd_media_update.save_last_update_timestamp")
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.load_last_update_timestamp", return_value=0
)
@patch("univention.bildungslogin.media_import.cmd_media_update.retrieve_media_data")
@patch("univention.bildungslogin.media_import.cmd_media_update.retrieve_media_feed")
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.get_access_token",
    return_value=sentinel.access_token,
)
@patch("univention.bildungslogin.media_import.cmd_media_update.get_config_from_file")
@patch("univention.bildungslogin.handlers.MetaDataHandler.get_all")
@patch("univention.bildungslogin.media_import.cmd_media_update.import_multiple_raw_media_data")
def test_error_message_after_failed_import(
    get_all_mock,
    get_config_from_file_mock,
    get_access_token_mock,
    retrieve_media_feed_mock,
    retrieve_media_data_mock,
    load_last_update_timestamp_mock,
    save_last_update_timestamp_mock,
    import_multiple_raw_media_data_mock,
):
    """Test that update_ldap_meta_data return False if errors were raised during the media import."""
    import_multiple_raw_media_data_mock.return_value = "something_went_wrong"
    result = univention.bildungslogin.media_import.cmd_media_update.update_ldap_meta_data(MagicMock())
    assert result is False


@patch("univention.bildungslogin.handlers.UDM")
@patch("univention.bildungslogin.media_import.cmd_media_update.save_last_update_timestamp")
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.load_last_update_timestamp", return_value=0
)
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.import_multiple_raw_media_data",
    return_value="",
)
@patch("univention.bildungslogin.media_import.cmd_media_update.retrieve_media_data")
@patch("univention.bildungslogin.media_import.cmd_media_update.retrieve_media_feed")
@patch(
    "univention.bildungslogin.media_import.cmd_media_update.get_access_token",
    return_value=sentinel.access_token,
)
@patch("univention.bildungslogin.media_import.cmd_media_update.get_config_from_file")
@patch("univention.bildungslogin.handlers.MetaDataHandler.get_all")
def test_update_ldap_meta_data_with_no_updated_products(
    get_all_mock,
    get_config_from_file_mock,
    get_access_token_mock,
    retrieve_media_feed_mock,
    retrieve_media_data_mock,
    import_multiple_raw_media_data_mock,
    load_last_update_timestamp_mock,
    save_last_update_timestamp_mock,
    udm_mock,
):
    """Test that update_ldap_meta_data returns True no product ids were updated."""
    retrieve_media_feed_mock.return_value = []
    result = univention.bildungslogin.media_import.cmd_media_update.update_ldap_meta_data(MagicMock())
    assert result is True


@pytest.mark.parametrize(
    "update_ldap_meta_data_return,exit_code",
    [(True, 1), (False, 0)],
)
def test_main(mocker, update_ldap_meta_data_return, exit_code):
    """Test that update_ldap_meta_data passed the correct return value."""
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_update.getAdminConnection",
        return_value=("lo", "pos"),
    )
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_update.update_ldap_meta_data",
        return_value=update_ldap_meta_data_return,
    )
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        univention.bildungslogin.media_import.cmd_media_update.main()
        assert pytest_wrapped_e.value.code == exit_code
