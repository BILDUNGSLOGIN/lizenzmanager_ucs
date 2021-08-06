# -*- coding: utf-8 -*-
#
# Copyright 2021 Univention GmbH
#
# http://www.univention.de/
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
# <http://www.gnu.org/licenses/>.

from __future__ import print_function

from datetime import datetime
from typing import List

import requests

from univention.bildungslogin.handlers import BiloCreateError, MetaDataHandler
from univention.bildungslogin.models import MetaData


class AuthError(Exception):
    pass


class MediaNotFoundError(Exception):
    pass


class MediaImportError(Exception):
    pass


def get_access_token(client_id, client_secret, scope, auth_server):
    # type: (str, str, str, str) -> str
    response = requests.post(
        auth_server,
        data={"grant_type": "client_credentials", "scope": scope},
        auth=(
            client_id,
            client_secret,
        ),
    )
    if response.status_code != 200:
        raise AuthError("Authorization failed: %s" % (response.json()["error_description"],))
    return response.json()["access_token"]


def get_all_media_data(client_id, client_secret, scope, auth_server, resource_server, product_ids):
    # type: (str, str, str, str, str, List[str]) -> List[dict]
    access_token = get_access_token(client_id, client_secret, scope, auth_server)
    return requests.post(
        resource_server + "/external/univention/media/query",
        json=[{"id": product_id} for product_id in product_ids],
        headers={
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/vnd.de.bildungslogin.mediaquery+json",
        },
    ).json()


def load_media(raw_media_data):  # type: (dict) -> MetaData
    if raw_media_data["status"] == 200:
        data = raw_media_data["data"]
        try:
            return MetaData(
                product_id=data["id"],
                title=data["title"],
                description=data["description"],
                author=data["author"],
                publisher=data["publisher"],
                cover=data["cover"][
                    "href"
                ],  # TODO what does data['cover'] look like if there is no cover
                cover_small=data["coverSmall"]["href"],
                modified=datetime.utcfromtimestamp(data["modified"] // 1000).strftime("%Y-%m-%d"),
            )
        except (KeyError, ValueError) as exc:
            raise MediaImportError(str(exc))
    else:
        raise MediaNotFoundError()


def import_single_media_data(meta_data_handler, raw_media_data):
    # type: (MetaDataHandler, List[dict]) -> None
    md = load_media(raw_media_data)
    try:
        meta_data_handler.create(md)
    except BiloCreateError as exc:
        raise MediaImportError(str(exc))
