#!/usr/share/ucs-test/runner /usr/bin/py.test -slv
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
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## packages: [python-bildungslogin, udm-bildungslogin-encoders]

import datetime
import time
from typing import Any, Dict, List

import pytest

from univention.bildungslogin.exceptions import BiloProductNotFoundError
from univention.bildungslogin.handlers import MetaDataHandler
from univention.bildungslogin.media_import import cmd_media_import

# TODO test the actual cli tool


TEST_PRODUCT_ID = "urn:univentiontest:medium:1234567890"
TEST_META_DATA = [
    {
        "author": None,
        "cover": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B160_X2.png",
        "cover_small": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B110_X2.png",
        "description": "Entdecken und verstehen - Schülerbuch als E-Book - 7. Schuljahr",
        "modified": datetime.date(2021, 8, 6),
        "product_id": TEST_PRODUCT_ID,
        "publisher": "Cornelsen",
        "title": "Entdecken und verstehen",
    }
]


class ArgsMock:
    product_ids = [TEST_PRODUCT_ID]


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
def delete_metatdata_after_test(lo):
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


def test_cli_import(delete_metatdata_after_test, lo, mocker):
    """Test that a metda data import os possible."""
    mocker.patch.object(cmd_media_import, "get_config", get_config_mock)
    mocker.patch.object(cmd_media_import, "parse_args", parse_args_mock)
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.retrieve_media_data",
        retrieve_media_data_mock,
    )
    mocker.patch("univention.bildungslogin.media_import.cmd_media_import.get_access_token")
    mh = MetaDataHandler(lo)
    delete_metatdata_after_test(TEST_PRODUCT_ID)
    cmd_media_import.main()
    udm_metadata = mh.get_meta_data_by_product_id(TEST_PRODUCT_ID)
    metadata = mh.from_udm_obj(udm_metadata)
    assert metadata.__dict__ == TEST_META_DATA[0]


def test_repeated_cli_import(delete_metatdata_after_test, lo, mocker):
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
    delete_metatdata_after_test(TEST_PRODUCT_ID)
    cmd_media_import.main()
    filter_s = "(&(objectClass=bildungsloginMetaData)(bildungsloginProductId={}))".format(
        TEST_PRODUCT_ID
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
