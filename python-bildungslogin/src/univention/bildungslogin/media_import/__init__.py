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

import datetime
import re
from copy import deepcopy
from typing import Any, Dict, List

import requests
from jsonschema import validate

from univention.bildungslogin.handlers import BiloCreateError, BiloProductNotFoundError, MetaDataHandler
from univention.bildungslogin.models import MetaData

HTTP_URL_START = re.compile(r"^http.?://")


MEDIA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "definitions": {
        "link": {
            "description": "Ein Link-Element analog zum HTML-Link. Die Semantik (wohin f\u00fchrt der Link)"
            " wird durch das rel-Attribut ausgedr\u00fcckt",
            "properties": {
                "href": {
                    "description": "eine g\u00fcltige URL",
                    "format": "uri",
                    "maxLength": 500,
                    "type": "string",
                },
                "rel": {"enum": ["src", "self"], "type": "string"},
            },
            "type": "object",
        },
        "timestamp": {
            "description": "Ein Zeitstempel als POSIX timestamp integer (https://en.wikipedia.org/wiki/Unix_time)",
            "type": "integer",
        },
        "urn": {
            "description": "Uniform Resource Name, https://de.wikipedia.org/wiki/Uniform_Resource_Name",
            "pattern": "^urn(:[a-z0-9]{1,32})+:[\\S]+$",
            "type": "string",
            "maxLength": 100,
        },
        "Author": {"description": "Autor des Medium", "maxLength": 100, "type": "string"},
        "Cover": {
            "description": "Bild zur Darstellung im Medienregal, in der Regalansicht."
            " Breite 120px, Höhe max. 160px.",
            "$ref": "#/definitions/link",
        },
        "CoverSmall": {
            "description": "Bild zur Darstellung im Medienregal, in der Listenansicht. Höhe max. 65px.",
            "$ref": "#/definitions/link",
        },
        "Description": {
            "description": "Beschreibung des Mediums, verwendet zur Anzeige im Bildungslogin Medienregal",
            "maxLength": 500,
            "type": "string",
        },
        "MediumIdentifier": {
            "$ref": "#/definitions/urn",
            "description": "im Kontext eines Verlages eindeutiger Bezeichner eines Mediums. "
            "Als Namespace Identifier wird 'bilo:medium' verwendet.",
            "title": "MediumId",
        },
        "ModifiedTimestamp": {
            "$ref": "#/definitions/timestamp",
            "description": "Zeitstempel der letzten Änderung",
        },
        "Publisher": {
            "description": "Der Verlag, der dieses Medium bereitstellt. "
            "Als eindeutiger Bezeichner wird hier das Verlagskürzel verwendet, welches auch als Prefix "
            "der BundleCodes dient",
            "maxLength": 10,
            "type": "string",
        },
        "Title": {
            "description": "Titel des Angebots zur Anzeige im Medienregal, z.B. bei einem Buch der Buchtitel,"
            " bei einer Anwendung Name der Anwendung etc.",
            "maxLength": 100,
            "minLength": 1,
            "type": "string",
        },
    },
    "description": "Ein Eintrag bzw. Element im Medienregal. Repräsentiert einen Verweis auf einen "
    "digitalen Bildungsinhalt",
    "id": "http://bildungslogin.t-systems-mms.eu/api/publisher/schemas/media.schema.json#",
    "properties": {
        "author": {"$ref": "#/definitions/Author"},
        "cover": {"$ref": "#/definitions/Cover"},
        "coverSmall": {"$ref": "#/definitions/CoverSmall"},
        "description": {"$ref": "#/definitions/Description"},
        "id": {"$ref": "#/definitions/MediumIdentifier"},
        "modified": {"$ref": "#/definitions/ModifiedTimestamp"},
        "publisher": {"$ref": "#/definitions/Publisher"},
        "title": {"$ref": "#/definitions/Title"},
    },
    "required": ["id", "title", "publisher", "cover", "coverSmall", "modified"],
    "title": "Medium",
    "type": "object",
}


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
        auth=(client_id, client_secret),
    )
    if response.status_code != 200:
        raise AuthError("Authorization failed: %s" % (response.json()["error_description"],))
    return response.json()["access_token"]


def retrieve_media_data(access_token, resource_server, product_ids):
    # type: (str, str, List[str]) -> List[dict]
    return requests.post(
        resource_server + "/external/univention/media/query",
        json=[{"id": product_id} for product_id in product_ids],
        headers={
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/vnd.de.bildungslogin.mediaquery+json",
        },
    ).json()


def retrieve_media_feed(access_token, resource_server, modified_after):
    # type: (str, str, int) -> List[str]
    return requests.post(
        resource_server + "/external/univention/media/feed",
        json={"modifiedAfter": modified_after},
        headers={
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/vnd.de.bildungslogin.mediafeed-query+json",
        },
    ).json()


def load_media(raw_media_data):  # type: (Dict[str, Any]) -> MetaData
    if raw_media_data["status"] == 200:
        data = cleaned_data(raw_media_data)
        validate(instance=data, schema=MEDIA_SCHEMA)
        try:
            return MetaData(
                product_id=data["id"],
                title=data["title"],
                description=data.get("description", ""),
                author=data.get("author", ""),
                publisher=data["publisher"],
                cover=data["cover"][
                    "href"
                ],  # TODO what does data['cover'] look like if there is no cover
                cover_small=data["coverSmall"]["href"],
                modified=datetime.datetime.utcfromtimestamp(data["modified"] // 1000).date(),
            )
        except (KeyError, ValueError) as exc:
            raise MediaImportError(str(exc))
    else:
        raise MediaNotFoundError()


def cleaned_data(raw_media_data):  # type: (Dict[str, Any]) -> Dict[str, Any]
    data = raw_media_data["data"]
    result = deepcopy(data)
    if not HTTP_URL_START.match(data["cover"]["href"]):
        result["cover"]["href"] = ""
    if not HTTP_URL_START.match(data["coverSmall"]["href"]):
        result["coverSmall"]["href"] = ""
    return result


def import_single_media_data(meta_data_handler, raw_media_data):
    # type: (MetaDataHandler, List[dict]) -> None
    md = load_media(raw_media_data)
    try:
        meta_data_handler.get_meta_data_by_product_id(md.product_id)
        meta_data_handler.save(md)
        return
    except BiloProductNotFoundError:
        # doesn't exist in LDAP yet, create it
        pass
    try:
        meta_data_handler.create(md)
    except BiloCreateError as exc:
        raise MediaImportError(str(exc))
