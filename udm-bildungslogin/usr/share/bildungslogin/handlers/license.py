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
from ldap.filter import filter_format

import univention.admin.syntax
import univention.admin.handlers
import univention.admin.localization
import univention.admin.uexceptions
from univention.admin.layout import Tab
from hashlib import sha256

translation = univention.admin.localization.translation("univention.admin.handlers.vbm")
_ = translation.translate

module = "vbm/license"
childs = True
childmodules = ['vbm/assignment']
object_name = _('Licenses')
object_name_plural = _('Licenses')
short_description = _("License")
long_description = _("License from the VBM Bildungslogin")
operations = ["add", "edit", "remove", "search"]  # TODO: Do we want a remove operation or not?

options = {
    "default": univention.admin.option(
        short_description=short_description,
        default=True,
        objectClasses=["top", "vbmLicense"],
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
    "code": univention.admin.property(
        short_description=_("License code"),
        long_description=_("License code of the license"),
        syntax=univention.admin.syntax.string,
        required=True,
        unique=True,
        may_change=False
    ),
    "product_id": univention.admin.property(
        short_description=_("Product ID"),
        long_description=_("The product ID"),
        syntax=univention.admin.syntax.string,
        required=True,
        may_change=False
    ),
    "quantity": univention.admin.property(
        short_description=_("Quantity"),
        long_description=_("Amount of licenses"),
        syntax=univention.admin.syntax.integer,
        required=True,
        may_change=False
    ),
    "provider": univention.admin.property(
        short_description=_("Provider"),
        long_description=_("The provider of the license"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=False
    ),
    "purchasing_reference": univention.admin.property(
        short_description=_("Purchasing reference"),
        long_description=_("The purchasing reference"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=False
    ),
    "utilization_systems": univention.admin.property(
        short_description=_("Utilization systems"),
        long_description=_("The utilization systems"),
        syntax=univention.admin.syntax.string,
        required=False,
        may_change=False
    ),
    "validity_start_date": univention.admin.property(
        short_description=_("Validity start date"),
        long_description=_("The date from which the license is valid"),
        syntax=univention.admin.syntax.date,
        required=True,
        may_change=False
    ),
    "validity_end_date": univention.admin.property(
        short_description=_("Validity end date"),
        long_description=_("The date from which the license is not valid anymore"),
        syntax=univention.admin.syntax.date,
        required=True,
        may_change=False
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
        default="0"
    ),
    "delivery_date": univention.admin.property(
        short_description=_("Delivery date"),
        long_description=_("The delivery date"),
        syntax=univention.admin.syntax.date,
        required=True,
        may_change=False
    ),
    "school": univention.admin.property(
        short_description=_("School"),
        long_description=_("The school"),
        syntax=univention.admin.syntax.string,
        required=True,
        may_change=False
    )
}

layout = [
    Tab(_("General"), _("Basic Settings"), layout=[
        ["code"],
        ["ignored"],
        ["product_id", "quantity"],
        ["provider", "purchasing_reference"],
        ["utilization_systems"],
        ["validity_start_date", "validity_end_date"],
        ["validity_duration", "special_type"],
        ["delivery_date", "school"],
    ])
]

mapping = univention.admin.mapping.mapping()
for udm_name, ldap_name in [
    ("cn", "cn"),
    ("code", "vbmLicenseCode"),
    ("product_id", "vbmProductId"),
    ("quantity", "vbmLicenseQuantity"),
    ("provider", "vbmLicenseProvider"),
    ("purchasing_reference", "vbmPurchasingReference"),
    ("utilization_systems", "vbmUtilizationSystems"),
    ("validity_start_date", "vbmValidityStartDate"),
    ("validity_end_date", "vbmValidityEndDate"),
    ("validity_duration", "vbmValidityDuration"),
    ("special_type", "vbmLicenseSpecialType"),
    ("ignored", "vbmIgnoredForDisplay"),
    ("delivery_date", "vbmDeliveryDate"),
    ("school", "vbmLicenseSchool")
]:
    mapping.register(udm_name, ldap_name, None, univention.admin.mapping.ListToString)


class object(univention.admin.handlers.simpleLdap):

    module = module

    def _ldap_pre_ready(self):
        # The CN is *always* set to the hash256 of the license code
        if self["code"]:
            self["cn"] = sha256(self["code"]).hexdigest()

    def _ldap_pre_create(self):
        # The code, and thus the cn of any license must be unique in the domain
        if self.lo.searchDn(filter_format("(&(objectClass=vbmLicense)(cn=%s))", [self["cn"]])):
            raise univention.admin.uexceptions.valueError(_("A license with that code already exists"))
        super(object, self)._ldap_pre_create()


lookup = object.lookup
lookup_filter = object.lookup_filter
identify = object.identify
