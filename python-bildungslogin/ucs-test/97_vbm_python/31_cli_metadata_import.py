#!/usr/share/ucs-test/runner /usr/bin/py.test -s
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
## tags: [vbm]
## roles: [domaincontroller_master]

from univention.admin.uldap import getAdminConnection
from univention.bildungslogin.handlers import MetaDataHandler
from univention.bildungslogin.media_import import cmd_media_import

# TODO test the actual cli tool


TEST_PRODUCT_ID = "urn:univention-test:medium:1234567890"


class ArgsMock:
    product_ids = [TEST_PRODUCT_ID]


def get_config_mock(*args, **kwargs):
    return {
        "client_id": None,
        "client_secret": None,
        "scope": None,
        "auth_server": None,
        "resource_server": None,
    }


def get_all_media_data_mock(*args, **kwargs):
    return [
        {
            "status": 200,
            "query": {"id": TEST_PRODUCT_ID},
            "data": {
                "publisher": "Cornelsen",
                "coverSmall": {
                    "href": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B110_X2.png",
                    "rel": "src",
                },
                "description": "Entdecken und verstehen - Schülerbuch als E-Book - 7. Schuljahr",
                "title": "Entdecken und verstehen",
                "author": "",
                "cover": {
                    "href": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B160_X2.png",
                    "rel": "src",
                },
                "modified": 1628258416000,
                "id": TEST_PRODUCT_ID,
            },
        }
    ]


def parse_args_mock(*args, **kwargs):
    return ArgsMock()


def test_cli_import(mocker):
    mocker.patch.object(cmd_media_import, "get_config", get_config_mock)
    mocker.patch.object(cmd_media_import, "parse_args", parse_args_mock)
    mocker.patch(
        "univention.bildungslogin.media_import.cmd_media_import.get_all_media_data",
        get_all_media_data_mock,
    )
    lo, po = getAdminConnection()
    mh = MetaDataHandler(lo)
    cmd_media_import.main()
    udm_metadata = mh.get_meta_data_by_product_id(TEST_PRODUCT_ID)
    metadata = mh.from_udm_obj(udm_metadata)
    udm_metadata.delete()
    assert metadata.__dict__ == {
        "author": None,
        "cover": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B160_X2.png",
        "cover_small": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B110_X2.png",
        "description": "Entdecken und verstehen - Schülerbuch als E-Book - 7. Schuljahr",
        "modified": "2021-08-06",
        "product_id": TEST_PRODUCT_ID,
        "publisher": "Cornelsen",
        "title": "Entdecken und verstehen",
    }
