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
Module and object specific for "vbm/metadata" UDM module.
"""

from __future__ import absolute_import, unicode_literals

from ..encoders import DatePropertyEncoder
from .generic import GenericModule, GenericObject, GenericObjectProperties


class VbmMetadataObjectProperties(GenericObjectProperties):
    """vbm/metadata UDM properties."""

    _encoders = {"modified": DatePropertyEncoder}


class VbmMetadataObject(GenericObject):
    """Better representation of vbm/metadata properties."""

    udm_prop_class = VbmMetadataObjectProperties


class VbmMetadataModule(GenericModule):
    """VbmMetadataObject factory"""

    _udm_object_class = VbmMetadataObject

    class Meta:
        supported_api_versions = [1, 2]
        suitable_for = ["vbm/metadata"]
