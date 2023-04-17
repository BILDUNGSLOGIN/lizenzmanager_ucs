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

import datetime
from hashlib import sha256
from typing import Optional

from ldap.filter import filter_format

import univention.admin.handlers
import univention.admin.localization
import univention.admin.syntax
import univention.admin.uexceptions
from univention.admin.layout import Tab
from univention.admin.syntax import iso8601Date

translation = univention.admin.localization.translation("univention.admin.handlers.bildungslogin")
_ = translation.translate

module = "bildungslogin/license"
childs = True
childmodules = ["bildungslogin/assignment"]
object_name = _("Licenses")
object_name_plural = _("Licenses")
short_description = _("License")
long_description = _("License from Bildungslogin")
operations = ["add", "edit", "remove", "search"]  # TODO: Do we want a remove operation or not?
default_containers = ["cn=licenses,cn=bildungslogin,cn=vbm,cn=univention"]

options = {
    "default": univention.admin.option(
        short_description=short_description,
        default=True,
        objectClasses=["top", "bildungsloginLicense"],
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
    "code": univention.admin.property(
        short_description=_("License code"),
        long_description=_("License code of the license"),
        syntax=univention.admin.syntax.string,
        required=True,
        unique=True,
        may_change=False,
    ),
    "product_id": univention.admin.property(
        short_description=_("Product ID"),
        long_description=_("The product ID"),
        syntax=univention.admin.syntax.string,
        required=True,
        may_change=False,
    ),
    "quantity": univention.admin.property(
        short_description=_("Quantity"),
        long_description=_("Amount of licenses"),
        syntax=univention.admin.syntax.integer,
        required=True,
        may_change=False,
    ),
    "provider": univention.admin.property(
        short_description=_("Provider"),
        long_description=_("The provider of the license"),
        syntax=univention.admin.syntax.string,
        required=True,
        may_change=False,
    ),
    "purchasing_reference": univention.admin.property(
        short_description=_("Purchasing reference"),
        long_description=_("The purchasing reference"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=False,
    ),
    "utilization_systems": univention.admin.property(
        short_description=_("Utilization systems"),
        long_description=_("The utilization systems"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=False,
    ),
    "validity_start_date": univention.admin.property(
        short_description=_("Validity start date"),
        long_description=_("The date from which the license is valid"),
        syntax=univention.admin.syntax.iso8601Date,
        required=False,
        may_change=False,
    ),
    "validity_end_date": univention.admin.property(
        short_description=_("Validity end date"),
        long_description=_("The date from which the license is not valid anymore"),
        syntax=univention.admin.syntax.iso8601Date,
        required=False,
        may_change=False,
    ),
    "validity_duration": univention.admin.property(
        short_description=_("Validity duration"),
        long_description=_("The validity duration"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=False,
    ),
    "special_type": univention.admin.property(
        short_description=_("Special type"),
        long_description=_("The special type"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=False,
    ),
    "ignored": univention.admin.property(
        short_description=_("Ignored"),
        long_description=_("Whether this license is ignored for assignments"),
        syntax=univention.admin.syntax.boolean,
        required=True,
        default="0",
    ),
    "delivery_date": univention.admin.property(
        short_description=_("Delivery date"),
        long_description=_("The delivery date"),
        syntax=univention.admin.syntax.iso8601Date,
        required=True,
        may_change=False,
    ),
    "school": univention.admin.property(
        short_description=_("School"),
        long_description=_("The school"),
        syntax=univention.admin.syntax.string,
        required=True,
        may_change=False,
    ),
    "num_assigned": univention.admin.property(
        short_description=_("Number of assigned"),
        long_description=_("Number of assigned or provisioned licenses"),
        syntax=univention.admin.syntax.integer,
        dontsearch=True,
        editable=False,
    ),
    "num_expired": univention.admin.property(
        short_description=_("Number of expired licenses"),
        long_description=_("Number of expired licenses"),
        syntax=univention.admin.syntax.integer,
        dontsearch=True,
        editable=False,
    ),
    "num_available": univention.admin.property(
        short_description=_("Number of available licenses"),
        long_description=_("Number of available licenses"),
        syntax=univention.admin.syntax.integer,
        dontsearch=True,
        editable=False,
    ),
    "assignments": univention.admin.property(
        short_description=_("Assignments"),
        long_description=_("The assignments belonging to this license"),
        syntax=univention.admin.syntax.ldapDn,
        multivalue=True,
    ),
    "expired": univention.admin.property(
        short_description=_("Expired"),
        long_description=_("Is the license expired or not"),
        syntax=univention.admin.syntax.boolean,
        dontsearch=True,
        editable=False,
    ),
    "license_type": univention.admin.property(
        short_description=_("License Type"),
        long_description=_("The type of the license as provided by the publisher"),
        syntax=univention.admin.syntax.string,
        required=True,
        may_change=False,
    ),
    "usage_status": univention.admin.property(
        short_description=_("Usage Status"),
        long_description=_("The usage status provided by the bildungslogin api"),
        syntax=univention.admin.syntax.boolean,
        may_change=True,
        editable=False,
    ),
    "expiry_date": univention.admin.property(
        short_description=_("Expiry Date"),
        long_description=_("The date the license expires for usage"),
        syntax=univention.admin.syntax.iso8601Date,
        may_change=True,
        editable=False,
    ),
    "validity_status": univention.admin.property(
        short_description=_("Validity status"),
        long_description=_("The validity of the license, dictated by the bildungslogin api"),
        syntax=univention.admin.syntax.boolean,
        may_change=True,
        editable=False,
    ),
    "registered": univention.admin.property(
        short_description=_("Registered"),
        long_description=_("If the license was already registered to the api"),
        syntax=univention.admin.syntax.boolean,
        may_change=True,
        editable=False,
    ),
}

layout = [
    Tab(
        _("General"),
        _("Basic Settings"),
        layout=[
            ["code", "product_id"],
            ["ignored"],
            ["quantity", "num_available"],
            ["provider", "purchasing_reference"],
            ["utilization_systems"],
            ["validity_start_date", "validity_end_date"],
            ["validity_duration", "special_type", "license_type"],
            ["delivery_date", "school"],
            ["num_assigned", "num_expired"],
            ["usage_status", "expiry_date"],
            ["validity_status", "registered"],
        ],
    )
]

mapping = univention.admin.mapping.mapping()
for udm_name, ldap_name in [
    ("cn", "cn"),
    ("code", "bildungsloginLicenseCode"),
    ("product_id", "bildungsloginProductId"),
    ("quantity", "bildungsloginLicenseQuantity"),
    ("provider", "bildungsloginLicenseProvider"),
    ("purchasing_reference", "bildungsloginPurchasingReference"),
    ("utilization_systems", "bildungsloginUtilizationSystems"),
    ("validity_start_date", "bildungsloginValidityStartDate"),
    ("validity_end_date", "bildungsloginValidityEndDate"),
    ("validity_duration", "bildungsloginValidityDuration"),
    ("special_type", "bildungsloginLicenseSpecialType"),
    ("ignored", "bildungsloginIgnoredForDisplay"),
    ("delivery_date", "bildungsloginDeliveryDate"),
    ("school", "bildungsloginLicenseSchool"),
    ("license_type", "bildungsloginLicenseType"),
    ("usage_status", "bildungsloginUsageStatus"),
    ("expiry_date", "bildungsloginExpiryDate"),
    ("validity_status", "bildungsloginValidityStatus"),
    ("registered", "bildungsloginRegistered")
]:
    mapping.register(udm_name, ldap_name, None, univention.admin.mapping.ListToString)


class object(univention.admin.handlers.simpleLdap):
    module = module

    def _get_total_number_of_assignments(self):  # type: () -> int
        """
        Get the total number of assignments for the license.
        The SINGLE and VOLUME licenses use the quantity field to represent this information.
        However, the WORKGROUP and SCHOOL licenses use the quantity field for different purpose:
            To represent, how many users can the assigned object (group/school) contain.
            But such licenses can only be assigned once -> returning 1 for these cases
        """
        if self["license_type"] in ["WORKGROUP", "SCHOOL"]:
            return 1
        return self._to_int(self["quantity"])

    def _load_num_assigned(self):
        if self.exists():
            self.info["num_assigned"] = str(
                len(
                    self.lo.searchDn(
                        "(&(objectClass=bildungsloginAssignment)"
                        "(|(bildungsloginAssignmentStatus=ASSIGNED)(bildungsloginAssignmentStatus=PROVISIONED)))",
                        base=str(self.dn),
                    )
                )
            )

    def _load_num_expired(self):
        """ Count the number of expired unassigned licenses """
        if self.exists():
            if self["expired"] == "0":
                self.info["num_expired"] = "0"
            else:
                num_assignments_total = self._get_total_number_of_assignments()
                num_assigned = self._to_int(self["num_assigned"])
                self.info["num_expired"] = str(num_assignments_total - num_assigned)

    def _load_assignments(self):
        if self.exists():
            self["assignments"] = self.lo.searchDn(
                "(objectClass=bildungsloginAssignment)", base=str(self.dn)
            )

    def _load_expired(self):
        """The license is expired, when `validity_end_date` is later than 'today'."""
        if not self.get("validity_end_date"):
            self.info["expired"] = "0"
            return
        validity_end_date = iso8601Date.to_datetime(self.get("validity_end_date"))
        self.info["expired"] = "1" if validity_end_date < datetime.date.today() else "0"

    def _load_num_available(self):
        if self.exists():
            if self["expired"] == "0":
                num_assignments_total = self._get_total_number_of_assignments()
                num_assigned = self._to_int(self["num_assigned"])
                self.info["num_available"] = str(num_assignments_total - num_assigned)
            else:
                self.info["num_available"] = "0"

    @staticmethod
    def _to_int(value):  # type: (Optional[str]) -> int
        return int(value) if value else 0

    def _ldap_pre_ready(self):
        super(object, self)._ldap_pre_ready()
        # The CN is *always* set to the hash256 of the license code
        if self["code"] and not self["cn"]:
            self["cn"] = sha256(self["code"]).hexdigest()

    def _ldap_pre_create(self):
        super(object, self)._ldap_pre_create()
        # The code, and thus the vbmLicenseCode of any license must be unique in the domain
        if self.lo.searchDn(
            filter_format(
                "(&(objectClass=bildungsloginLicense)(bildungsloginLicenseCode=%s))",
                [self["code"]],
            )
        ):
            raise univention.admin.uexceptions.valueError(_("A license with that code already exists"))
        super(object, self)._ldap_pre_create()

    def ready(self):
        super(object, self).ready()
        school_filter = "(objectClass=ucsschoolOrganizationalUnit)"
        schools = [item[1]["ou"][0] for item in self.lo.search(school_filter, attr=["ou"])]
        if self["school"].lower() not in [school.lower() for school in schools]:
            raise univention.admin.uexceptions.valueError(
                _(
                    'The school "{}" does not exist. Choose from: \n{}'.format(
                        self["school"], "\n".join(schools)
                    )
                )
            )

    def open(self):
        super(object, self).open()
        self._load_num_assigned()
        self._load_assignments()
        self._load_expired()
        self._load_num_available()
        self._load_num_expired()
        self.save()


lookup = object.lookup
lookup_filter = object.lookup_filter
identify = object.identify
