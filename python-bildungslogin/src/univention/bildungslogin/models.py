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

import datetime
from typing import Optional

import attr

from .utils import LicenseType, Status


@attr.s
class Assignment(object):
    assignee = attr.ib()  # type: str
    time_of_assignment = attr.ib()  # type: datetime.date
    status = attr.ib()  # type: str
    license = attr.ib()  # type: Status


@attr.s
class License(object):
    license_code = attr.ib()  # type: str
    product_id = attr.ib()  # type: str
    license_quantity = attr.ib()  # type: int
    license_provider = attr.ib()  # type: str
    purchasing_reference = attr.ib()  # type: str
    utilization_systems = attr.ib()  # type: str
    validity_start_date = attr.ib()  # type: Optional[datetime.date]
    validity_end_date = attr.ib()  # type: Optional[datetime.date]
    validity_duration = attr.ib()  # type: str
    license_special_type = attr.ib()  # type: str
    ignored_for_display = attr.ib()  # type: bool
    delivery_date = attr.ib()  # type: Optional[datetime.date]
    license_school = attr.ib()  # type: str
    num_assigned = attr.ib(default=0)  # type: Optional[int]
    num_available = attr.ib(default=0)  # type: Optional[int]

    @property
    def license_type(self):  # type: () -> str
        """we only have volume and single-licenses, not mass-licenses"""
        if self.license_quantity > 1:
            return LicenseType.VOLUME
        else:
            return LicenseType.SINGLE


@attr.s
class MetaData(object):
    product_id = attr.ib()  # type: str
    title = attr.ib(default="")  # type: str
    description = attr.ib(default="")  # type: str
    author = attr.ib(default="")  # type: str
    publisher = attr.ib(default="")  # type: str
    cover = attr.ib(default="")  # type: str
    cover_small = attr.ib(default="")  # type: str
    modified = attr.ib(default=datetime.date.today())  # type: datetime.date
