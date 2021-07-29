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

import json
import time

import datetime
from typing import Dict

from univention.admin.uldap import getAdminConnection
from univention.bildungslogin.handler import LicenseHandler, BiloCreateError
from univention.bildungslogin.models import License


def load_license(license_raw, school):  # type: (Dict, str) -> License
    return License(
        license_code=license_raw['lizenzcode'],
        product_id=license_raw['product_id'],
        license_quantity=license_raw['lizenzanzahl'],
        license_provider=license_raw['lizenzgeber'],
        purchasing_reference=license_raw['kaufreferenz'],
        utilization_systems=license_raw['nutzungssysteme'],
        validity_start_date=license_raw['gueltigkeitsbeginn'],
        validity_end_date=license_raw['gueltigkeitsende'],
        validity_duration=license_raw['gueltigkeitsdauer'],
        license_special_type=license_raw['sonderlizenz'],
        ignored_for_display="0",
        delivery_date=datetime.datetime.now().isoformat().split('T')[0],
        license_school=school,
    )


def import_licenses(license_file, school):  # type: (str, str) -> None
    lo, po = getAdminConnection()
    with open(license_file, 'r') as license_file_fd:
        licenses_raw = json.load(license_file_fd)
    licenses = [load_license(license_raw, school) for license_raw in licenses_raw]
    lh = LicenseHandler(lo)
    for license in licenses:
        # todo remove me
        try:
            lh.create(license)
        except BiloCreateError:
            print("skipping for testing")
