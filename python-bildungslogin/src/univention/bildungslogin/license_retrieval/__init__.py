# -*- coding: utf-8 -*-
#
# Copyright 2022 Univention GmbH
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

import json
import os
import requests
from typing import Tuple

from ..exceptions import (
    AuthError, LicenseValidationError,
    LicenseNotFoundError, BiloServerError)
from jsonschema import validate, ValidationError

PULL_LICENSE_RESPONSE_MOCK = {
    "licenses": [
        {
            "lizenzcode": "WES-TEST-CODE-LZL21",
            "product_id": "urn:bilo:medium:050131",
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
            "lizenzcode": "WES-TEST-CODE-LZL23",
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
    "package_id": "VHT-9MV-EYD-iz5"
}

LICENSE_RETRIEVAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        "restrictednonnullstring": {
            "type": "string",
            "minLength": 0,
            "maxlength": 255
        },
        "restrictedstring": {
            "type": ["string", "null"],
            "minLength": 0,
            "maxlength": 255
        },

    },
    "properties": {
        "licenses": {
            "type": "array",
            "items": [
                {
                    "type": "object",
                    "properties": {
                        "lizenzcode": {
                            "$ref": "#/definitions/restrictednonnullstring"
                        },
                        "product_id": {
                            "$ref": "#/definitions/restrictednonnullstring"
                        },
                        "lizenzanzahl": {
                            "type": "integer", "minimum": 0
                        },
                        "lizenzgeber": {
                            "$ref": "#/definitions/restrictednonnullstring"
                        },
                        "kaufreferenz": {
                            "$ref": "#/definitions/restrictedstring"
                        },
                        "nutzungssysteme": {
                            "$ref": "#/definitions/restrictedstring"
                        },
                        "gueltigkeitsbeginn": {
                            "type": ["string", "null"]
                        },
                        "gueltigkeitsende": {
                            "type": ["string", "null"]
                        },
                        "gueltigkeitsdauer": {
                            "$ref": "#/definitions/restrictedstring"
                        },
                        "sonderlizenz": {
                            "type": ["string", "null"]
                        }
                    },
                    "required": [
                        "lizenzcode",
                        "product_id",
                        "lizenzanzahl",
                        "lizenzgeber"
                    ]
                }
            ]
        },
        "package_id": {
            "type": "string"
        }
    },
    "required": [
        "licenses",
        "package_id"
    ]
}


def get_access_token(client_id, client_secret, scope, auth_server, proxies=None, debug=False):
    # type: (str, str, str, str, dict) -> str
    response = requests.post(
        auth_server,
        data={"grant_type": "client_credentials", "scope": scope},
        auth=(client_id, client_secret),
        proxies=proxies
    )

    if debug:
        print(response.content)

    if response.status_code != 200:
        raise AuthError("Authorization failed: %s" % (response.json()["error_description"],))
    return response.json()["access_token"]


def save_license_package_to_json(license_package, pickup_number):
    path = '/usr/shared/bildungslogin'

    # Check whether the specified path exists or not
    is_exist = os.path.exists(path)

    if not is_exist:
        # Create a new directory because it does not exist
        os.makedirs(path)

    filename = path + '/license_package-{}.json'.format(pickup_number)
    with open(filename, 'w') as f:
        json.dump(license_package['licenses'], f)
    return filename


def retrieve_licenses_package(access_token, resource_server, pickup_number, proxies=None, debug=False):
    # type: (str, str, str, dict) -> Tuple[int, dict]
    """
    Retrieves the license package from the server by its pickup number and validates it.
    Returns the response code and retrieved JSON body in case of success.
    """
    r = requests.get(
        url=resource_server + "/licenserouting/v1/licensepackage",
        params={'package_id': pickup_number},
        headers={"Authorization": "Bearer " + access_token,
                 "Content-Type": "application/x-www-form-urlencoded"},
        proxies=proxies
    )
    if debug:
        print(r.url)
    if r.status_code == 200 or r.status_code == 208:
        try:
            validate(instance=r.json(), schema=LICENSE_RETRIEVAL_SCHEMA)
        except ValidationError as exc:
            raise LicenseValidationError("Downloaded json does not conform to "
                                         "required json format: {}".format(exc.message))
        return r.status_code, r.json()

    if r.status_code == 404:
        raise LicenseNotFoundError("404: No license package found for "
                                   "the transferred pickup number: {}".format(pickup_number))
    if r.status_code == 500:
        raise BiloServerError("Please check with Bildungslogin and try again")
    raise BiloServerError("Unknown status code: {}".format(r.status_code))


def confirm_licenses_package(access_token, resource_server, pickup_number, proxies=None):
    # type: (str, str, str, dict) -> int
    """
    Sends the confirmation to the server that the license package was retrieved.
    Returns the response code in case of success.
    """
    response = requests.post(
        resource_server + "/external/publisher/v2/licensepackage/confirm",
        data={"package_id": pickup_number},
        headers={
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        proxies=proxies
    )

    if response.status_code in [200, 409]:
        return response.status_code

    if response.status_code == 404:
        raise LicenseNotFoundError("404: No license package found for "
                                   "the transferred pickup number: {}".format(pickup_number))
    else:
        raise BiloServerError("Unknown status code: {}".format(response.status_code))
