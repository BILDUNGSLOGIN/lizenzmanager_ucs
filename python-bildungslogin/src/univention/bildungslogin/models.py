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

from typing import Optional

from utils import LicenseType, Status, my_string_to_int


class Assignment(object):
    def __init__(self, username, license, time_of_assignment, status):
        # type: (str, str, str, Status) -> None
        self.assignee = username
        self.time_of_assignment = time_of_assignment
        self.status = status
        self.license = license

    def to_dict(self):
        return self.__dict__


class License(object):
    def __init__(
        self,
        license_code,
        product_id,
        license_quantity,
        license_provider,
        purchasing_reference,
        utilization_systems,
        validity_start_date,
        validity_end_date,
        validity_duration,
        license_special_type,
        ignored_for_display,
        delivery_date,
        license_school,
        num_available=None,
    ):  # type: (str, str, str, str, str, str, str, str, str, str, str, str, str, Optional[int]) -> None
        self.license_code = license_code
        self.product_id = product_id
        self.license_quantity = license_quantity
        self.license_provider = license_provider
        self.purchasing_reference = purchasing_reference
        self.utilization_systems = utilization_systems
        self.validity_start_date = validity_start_date
        self.validity_end_date = validity_end_date
        self.validity_duration = validity_duration
        self.license_special_type = license_special_type
        self.ignored_for_display = ignored_for_display
        self.delivery_date = delivery_date
        self.license_school = license_school
        self.num_available = num_available

    @property
    def license_type(self):  # type: () -> str
        """we only have volume and single-licenses, not mass-licenses"""
        if my_string_to_int(self.license_quantity) > 1:
            return LicenseType.VOLUME
        else:
            return LicenseType.SINGLE

    def to_dict(self):
        return self.__dict__


class MetaData(object):
    def __init__(
        self,
        product_id,
        title=None,
        description=None,
        author=None,
        publisher=None,
        cover=None,
        cover_small=None,
        modified=None,
    ):  # type: (str, str, str, str, str, str, str, str) -> None
        self.product_id = product_id
        self.title = title
        self.description = description
        self.author = author
        self.publisher = publisher
        self.cover = cover
        self.cover_small = cover_small
        self.modified = modified

    def to_dict(self):
        return self.__dict__
