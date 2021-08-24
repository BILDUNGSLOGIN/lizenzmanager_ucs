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

import univention.admin.handlers
import univention.admin.localization
import univention.admin.syntax
import univention.admin.types
import univention.admin.uexceptions
from univention.admin.layout import Tab

translation = univention.admin.localization.translation("univention.admin.handlers.bildungslogin")
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


module = "bildungslogin/assignment"
childs = False
superordinate = "bildungslogin/license"
object_name = _("Assignment")
object_name_plural = _("Assignments")
short_description = _("Assignment")
long_description = _("Assignment of a license from Bildungslogin")
operations = ["add", "edit", "remove", "search"]

options = {
    "default": univention.admin.option(
        short_description=short_description,
        default=True,
        objectClasses=["top", "bildungsloginAssignment"],
    )
}

property_descriptions = {
    "cn": univention.admin.property(
        short_description=_("CN"),
        long_description=_("CN of the license"),
        syntax=univention.admin.syntax.string,
        required=True,
        identifies=True,
        may_change=False,
    ),
    "assignee": univention.admin.property(
        short_description=_("Assignee"),
        long_description=_("Assignee of the assignment"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=True,
    ),
    "time_of_assignment": univention.admin.property(
        short_description=_("Time of assignment"),
        long_description=_("The time of the assignment"),
        syntax=univention.admin.syntax.iso8601Date,
        required=False,
        may_change=True,
    ),
    "status": univention.admin.property(
        short_description=_("Status"),
        long_description=_("Status of the assignment"),
        syntax=StatusSyntax,
        required=True,
        default="AVAILABLE",
        may_change=True,
    ),
}

layout = [
    Tab(_("General"), _("Basic Settings"), layout=[["assignee"], ["time_of_assignment", "status"]])
]

mapping = univention.admin.mapping.mapping()
for udm_name, ldap_name in [
    ("cn", "cn"),
    ("assignee", "bildungsloginAssignmentAssignee"),
    ("time_of_assignment", "bildungsloginAssignmentTimeOfAssignment"),
    ("status", "bildungsloginAssignmentStatus"),
]:
    mapping.register(udm_name, ldap_name, None, univention.admin.mapping.ListToString)


class object(univention.admin.handlers.simpleLdap):

    module = module

    def _validate_status_transition(self):
        """
        Checks if a status transition is allowed or not.
        """
        if not self.hasChanged("status"):
            return
        allowed_transitions = {
            ("AVAILABLE", "ASSIGNED"),
            ("ASSIGNED", "AVAILABLE"),
            ("ASSIGNED", "PROVISIONED"),
        }
        transition = (self.oldinfo.get("status", ""), self["status"])
        if transition not in allowed_transitions:
            raise univention.admin.uexceptions.valueError(
                _("Invalid status transition from {} to {}.").format(transition[0], transition[1])
            )

    def _validate_status_assignee(self):
        """
        Checks if a status that needs an assignee has one and if a status that must not have an assignee
        does not.
        """
        if self["status"] in ("ASSIGNED", "PROVISIONED") and not self["assignee"]:
            raise univention.admin.uexceptions.valueError(
                _("An assignment in status {} needs an assignee.").format(self["status"])
            )
        elif self["status"] == "AVAILABLE" and self["assignee"]:
            raise univention.admin.uexceptions.valueError(
                _("An assignment in status {} must not have an assignee.").format(self["status"])
            )

    def ready(self):
        result = super(object, self).ready()
        self._validate_status_assignee()
        return result

    def _ldap_pre_ready(self):
        super(object, self)._ldap_pre_ready()
        # The CN is *always* a random uid
        if not self["cn"]:
            self["cn"] = str(uuid4())

    def _ldap_pre_modify(self):
        super(object, self)._ldap_pre_modify()
        # A transition happens only on modifications.
        self._validate_status_transition()


lookup = object.lookup
lookup_filter = object.lookup_filter
identify = object.identify
