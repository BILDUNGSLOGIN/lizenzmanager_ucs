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
from typing import Optional, Type

import attr

from .utils import _


class Status(object):
    """ Assignment status """
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"

    @classmethod
    def label(cls, status):
        return {
            cls.ASSIGNED: _("Assigned"),
            cls.PROVISIONED: _("Provisioned"),
            cls.AVAILABLE: _("Available"),
        }[status]


class LicenseType(object):
    """ Type of the license """
    VOLUME = "VOLUME"
    SINGLE = "SINGLE"
    WORKGROUP = "WORKGROUP"
    SCHOOL = "SCHOOL"

    @classmethod
    def label(cls, license_type):
        return {
            cls.VOLUME: _("Volume license"),
            cls.SINGLE: _("Single license"),
            cls.WORKGROUP: _("Workgroup license"),
            cls.SCHOOL: _("School license"),
        }[license_type]

    @classmethod
    def init_from_api(cls, license_type):
        # type: (Type[LicenseType], str) -> str
        """ Initialize the LicenseType from the value defined in the API """
        if license_type == "Schullizenz":
            return cls.SCHOOL
        elif license_type == "Lerngruppenlizenz":
            return cls.WORKGROUP
        elif license_type == "Volumenlizenz":
            return cls.VOLUME
        elif license_type == "Einzellizenz":
            return cls.SINGLE
        raise ValueError("Unknown license type value: '{}'".format(license_type))


class Role(object):
    """ Role of the user """
    STAFF = "staff"
    STUDENT = "student"
    TEACHER = "teacher"
    TEACHER_STAFF = "teacher_and_staff"
    SCHOOL_ADMIN = "school_admin"

    @classmethod
    def label(cls, role):
        role_list = []
        for role in cls.roles_labels(role):
            role_label = {
                cls.STAFF: _("Staff"),
                cls.STUDENT: _("Student"),
                cls.TEACHER: _("Teacher"),
                cls.TEACHER_STAFF: _("Teacher and staff"),
                cls.SCHOOL_ADMIN: _("Admin")
            }[role]
            role_list.append(role_label)
        return role_list

    @classmethod
    def roles_labels(cls, roles):
        roles_labels = []
        for role in roles:
            roles_labels.append(role.split(':')[0])
        return roles_labels


@attr.s
class Assignment(object):
    assignee = attr.ib()  # type: str
    time_of_assignment = attr.ib()  # type: datetime.date
    status = attr.ib()  # type: Status
    license = attr.ib()  # type: str


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
    license_type = attr.ib()  # type: str
    license_special_type = attr.ib()  # type: str
    ignored_for_display = attr.ib()  # type: bool
    delivery_date = attr.ib()  # type: Optional[datetime.date]
    license_school = attr.ib()  # type: str
    num_assigned = attr.ib(default=0)  # type: Optional[int]
    num_available = attr.ib(default=0)  # type: Optional[int]

    @property
    def is_expired(self):
        """ Check if license is expired """
        if self.validity_end_date is None:
            return False
        return self.validity_end_date < datetime.date.today()


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
