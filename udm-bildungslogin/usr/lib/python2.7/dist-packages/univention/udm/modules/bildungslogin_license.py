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
# you and Univention.
#
# This program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/>.

"""
Module and object specific for "bildungslogin/license" UDM module.
"""

from __future__ import absolute_import, unicode_literals

import datetime

from ..encoders import (
    DatePropertyEncoder,
    DisabledPropertyEncoder,
    StringIntPropertyEncoder,
    dn_list_property_encoder_for,
)
from .generic import GenericModule, GenericObject, GenericObjectProperties


class ExpiredPropertyEncoder(DisabledPropertyEncoder):
    @staticmethod
    def encode(value=None):
        if value is None:
            return None
        return "1" if value else "0"


class BildungsloginLicenseObjectProperties(GenericObjectProperties):
    """bildungslogin/license UDM properties."""

    _encoders = {
        "quantity": StringIntPropertyEncoder,
        "validity_start_date": DatePropertyEncoder,
        "validity_end_date": DatePropertyEncoder,
        "ignored": DisabledPropertyEncoder,
        "delivery_date": DatePropertyEncoder,
        "num_assigned": StringIntPropertyEncoder,
        "num_expired": StringIntPropertyEncoder,
        "num_available": StringIntPropertyEncoder,
        "assignments": dn_list_property_encoder_for("bildungslogin/assignment"),
        "usage_status": DisabledPropertyEncoder,
        "expired": ExpiredPropertyEncoder,
        "expiry_date": DatePropertyEncoder,
        "validity_status": DisabledPropertyEncoder,
        "registered": DisabledPropertyEncoder,
    }


class BildungsloginLicenseObject(GenericObject):
    """Better representation of bildungslogin/license properties."""

    udm_prop_class = BildungsloginLicenseObjectProperties
    now = datetime.date.today()


class BildungsloginLicenseModule(GenericModule):
    """BildungsloginLicenseObject factory"""

    _udm_object_class = BildungsloginLicenseObject

    class Meta:
        supported_api_versions = [1, 2]
        suitable_for = ["bildungslogin/license"]
