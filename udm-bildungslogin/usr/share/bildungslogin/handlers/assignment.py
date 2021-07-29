#!/usr/bin/python2.7
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

from uuid import uuid4
import univention.admin.syntax
import univention.admin.uexceptions
import univention.admin.handlers
import univention.admin.types
import univention.admin.localization
from univention.admin.layout import Tab

translation = univention.admin.localization.translation("univention.admin.handlers.vbm")
_ = translation.translate


class StatusSyntax(univention.admin.syntax.simple):

    type_class = univention.admin.types.StringType

    @classmethod
    def parse(cls, text):
        if text not in ("AVAILABLE", "ASSIGNED", "PROVISIONED"):
            raise univention.admin.uexceptions.valueInvalidSyntax(
                _("The status must be one of AVAILABLE, ASSIGNED or PROVISIONED")
            )
        return text


module = "vbm/assignment"
childs = False
superordinate = 'vbm/license'
object_name = _('Assignment')
object_name_plural = _('Assignments')
short_description = _("Assignment")
long_description = _("Assignment of a license from the VBM Bildungslogin")
operations = ["add", "edit", "remove", "search"]

options = {
    "default": univention.admin.option(
        short_description=short_description,
        default=True,
        objectClasses=["top", "vbmAssignment"]
    )
}

property_descriptions = {
    "cn": univention.admin.property(
            short_description=_("CN"),
            long_description=_("CN of the license"),
            syntax=univention.admin.syntax.string,
            required=True,
            identifies=True,
            may_change=False
        ),
    "assignee": univention.admin.property(
        short_description=_("Assignee"),
        long_description=_("Assignee of the assignment"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=True
    ),
    "time_of_assignment": univention.admin.property(
            short_description=_("Time of assignment"),
            long_description=_("The time of the assignment"),
            syntax=univention.admin.syntax.date,
            required=False,
            may_change=True
        ),
    "status": univention.admin.property(
        short_description=_("Status"),
        long_description=_("Status of the assignment"),
        syntax=StatusSyntax,
        required=True,
        default="AVAILABLE",
        may_change=True
    )
}

layout = [
    Tab(_("General"), _("Basic Settings"), layout=[
        ["cn"],
        ["assignee"],
        ["time_of_assignment", "status"]
    ])
]

mapping = univention.admin.mapping.mapping()
for udm_name, ldap_name in [
    ("cn", "cn"),
    ("assignee", "vbmAssignmentAssignee"),
    ("time_of_assignment", "vbmAssignmentTimeOfAssignment"),
    ("status", "vbmAssignmentStatus"),
]:
    mapping.register(udm_name, ldap_name, None, univention.admin.mapping.ListToString)


class object(univention.admin.handlers.simpleLdap):

    module = module

    def _validate_status_transition(self):
        if not self.hasChanged("status"):
            return
        forbidden_transitions = {
            ("AVAILABLE", "PROVISIONED"),
            ("PROVISIONED", "ASSIGNED"),
            ("PROVISIONED", "AVAILABLE")
        }
        transition = (self.oldinfo.get("status", ""), self["status"])
        if transition in forbidden_transitions:
            raise univention.admin.uexceptions.valueError(
                _("Invalid status transition from {} to {}.").format(transition[0], transition[1])
            )

    def _ldap_pre_ready(self):
        # The CN is *always* a random uid
        if not self["cn"]:
            self["cn"] = str(uuid4())

    def _ldap_pre_modify(self):
        self._validate_status_transition()


lookup = object.lookup
lookup_filter = object.lookup_filter
identify = object.identify
