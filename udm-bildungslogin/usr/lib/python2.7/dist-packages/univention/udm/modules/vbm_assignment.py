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
Module and object specific for "vbm/assignment" UDM module.
"""

from __future__ import absolute_import, unicode_literals

from ldap.filter import filter_format

from ..encoders import DatePropertyEncoder, DnPropertyEncoder
from ..utils import UDebug
from .generic import GenericModule, GenericObject, GenericObjectProperties


class EntryUuidPropertyEncoder(DnPropertyEncoder):
    udm_module_name = "users/user"

    def _dn_to_udm_object(self, value):
        filter_s = filter_format("(&(univentionObjectType=users/user)(entryUUID=%s))", (value,))
        dns = self._udm.connection.searchDn(filter_s)
        if len(dns) != 1:
            UDebug.error("Assignee for 'vbm/assignment' with {!r} not found.".format(filter_s))
            return None
        return super(EntryUuidPropertyEncoder, self)._dn_to_udm_object(dns[0])


class VbmAssignmentObjectProperties(GenericObjectProperties):
    """vbm/assignment UDM properties."""

    _encoders = {
        "assignee": EntryUuidPropertyEncoder,
        "time_of_assignment": DatePropertyEncoder,
    }


class VbmAssignmentObject(GenericObject):
    """Better representation of vbm/assignment properties."""

    udm_prop_class = VbmAssignmentObjectProperties


class VbmAssignmentModule(GenericModule):
    """VbmAssignmentObject factory"""

    _udm_object_class = VbmAssignmentObject

    class Meta:
        supported_api_versions = [1, 2]
        suitable_for = ["vbm/assignment"]
