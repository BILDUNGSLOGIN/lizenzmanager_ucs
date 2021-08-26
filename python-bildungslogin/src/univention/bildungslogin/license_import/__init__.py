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

import datetime
import json
from typing import Any, Dict, List, Optional

from jsonschema import validate

from ..handlers import LicenseHandler
from ..models import License

LICENSE_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
    "$comment": "License Import configuration schema. License: GNU AGPL v3, Copyright 2021 Univention GmbH",
    "title": "license-import",
    "description": "license-import data",
    "type": "array",
    "definitions": {
        "nonemptystring": {
            "type": "string",
            "minLength": 1,
        },
    },
    "items": {
        "type": "object",
        "properties": {
            "lizenzcode": {"$ref": "#/definitions/nonemptystring"},
            "product_id": {"$ref": "#/definitions/nonemptystring"},
            "lizenzanzahl": {"type": "integer"},
            "lizenzgeber": {"$ref": "#/definitions/nonemptystring"},
            "kaufreferenz": {"type": "string"},
            "nutzungssysteme": {"type": "string"},
            "gueltigkeitsbeginn": {"type": "string"},
            "gueltigkeitsende": {"type": "string"},
            "gueltigkeitsdauer": {"type": "string"},
            "sonderlizenz": {"type": "string"},
        },
        "required": [
            "lizenzcode",
            "product_id",
            "lizenzanzahl",
            "lizenzgeber",
            "kaufreferenz",
            "nutzungssysteme",
            "gueltigkeitsbeginn",
            "gueltigkeitsende",
            "gueltigkeitsdauer",
            "sonderlizenz",
        ],
    },
}


def convert_raw_license_date(date_str):  # type: (str) -> Optional[datetime.date]
    if date_str:
        return datetime.datetime.strptime(date_str, "%d-%m-%Y").date()
    else:
        return None


def load_license(license_raw, school):  # type: (Dict[str, Any], str) -> License
    license = License(
        license_code=license_raw["lizenzcode"],
        product_id=license_raw["product_id"],
        license_quantity=license_raw["lizenzanzahl"],
        license_provider=license_raw["lizenzgeber"],
        purchasing_reference=license_raw["kaufreferenz"],
        utilization_systems=license_raw["nutzungssysteme"],
        validity_start_date=convert_raw_license_date(license_raw["gueltigkeitsbeginn"]),
        validity_end_date=convert_raw_license_date(license_raw["gueltigkeitsende"]),
        validity_duration=license_raw["gueltigkeitsdauer"],
        license_special_type=license_raw["sonderlizenz"],
        ignored_for_display=False,
        delivery_date=datetime.date.today(),
        license_school=school,
    )
    check_and_fix_license_code(license)
    return license


def load_license_file(license_file, school):  # type: (str, str) -> List[License]
    with open(license_file, "r") as license_file_fd:
        licenses_raw = json.load(license_file_fd)
    validate(instance=licenses_raw, schema=LICENSE_SCHEMA)
    licenses = [load_license(license_raw, school) for license_raw in licenses_raw]
    return licenses


def import_license(license_handler, license):  # type: (LicenseHandler, License) -> None
    license_handler.create(license)


def check_and_fix_license_code(license):  # type: (License) -> None
    """
    If the license code does not start with the provider short, it is appended.
    """
    if not license.license_code.lower().startswith("{}-".format(license.license_provider.lower())):
        license.license_code = "{}-{}".format(license.license_provider, license.license_code)
