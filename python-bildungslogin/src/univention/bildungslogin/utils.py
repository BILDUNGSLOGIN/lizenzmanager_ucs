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

import logging
from datetime import datetime


class Status(object):
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"


class LicenseType:
    VOLUME = "Volumenlizenz"
    SINGLE = "Einzellizenz"


def get_logger():  # type: () -> logging.Logger
    return logging.getLogger(__name__)


def my_string_to_int(num):  # type: (str) -> int
    return int(num) if num else 0


def parse_raw_license_date(date_str):  # type: (str) -> datetime
    return datetime.strptime(date_str, "%d-%m-%Y")
