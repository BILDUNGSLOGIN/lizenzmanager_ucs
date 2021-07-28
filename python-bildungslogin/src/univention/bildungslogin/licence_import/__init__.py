# -*- coding: utf-8 -*-
#
# Copyright 2021 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public Licence version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a licence agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public Licence for more details.
#
# You should have received a copy of the GNU Affero General Public
# Licence with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licences/AGPL-3; if not, see
# <http://www.gnu.org/licences/>.

import json
import time

from typing import Dict

from univention.bildungslogin.licence import Licence


def load_licence(licence_raw, school):  # type: (Dict, str) -> Licence
    return Licence(
        licence_code=licence_raw['lizenzcode'],
        product_id=licence_raw['product_id'],
        licence_quantity=licence_raw['lizenzanzahl'],
        licence_provider=licence_raw['lizenzgeber'],
        purchasing_date=licence_raw['kaufreferenz'],
        utilization_systems=licence_raw['nutzungssysteme'],
        validity_start_date=licence_raw['gueltigkeitsbeginn'],
        validity_end_date=licence_raw['gueltigkeitsende'],
        validity_duration=licence_raw['gueltigkeitsdauer'],
        licence_special_type=licence_raw['sonderlizenz'],
        ignored_for_display=False,
        delivery_date=str(int(time.time())),
        licence_school=school,
    )


def import_licences(licence_file, school):  # type: (str, str) -> None
    with open(licence_file, 'r') as licence_file_fd:
        licences_raw = json.load(licence_file_fd)
    licences = [load_licence(licence_raw, school) for licence_raw in licences_raw]
    for licence in licences:
        licence.save()
