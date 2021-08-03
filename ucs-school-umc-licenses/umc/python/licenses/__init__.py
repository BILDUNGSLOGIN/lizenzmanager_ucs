#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Manage licenses
#
# Copyright 2021 Univention GmbH
#
# http://www.univention.de/
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
# <http://www.gnu.org/licenses/>.


from ucsschool.lib.school_umc_base import SchoolBaseModule
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize, simple_response
from univention.management.console.modules.sanitizers import PatternSanitizer

_ = Translation("ucs-school-umc-licenses").translate

licenses = [
    {
        "licenseId": 0,
        "productId": "xxx-x-xxxxx-xxx-x",
        "productName": "Produkt A",
        "publisher": "Verlag XYZ",
        "licenseCode": "XYZ-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx",
        "licenseType": "Volumenlizenz",
        "countAquired": 25,
        "countAllocated": 15,
        "countExpired": 0,
        "countAllocatable": 10,
        "importDate": "2021-05-12",
    },
    {
        "licenseId": 1,
        "productId": "xxx-x-xxxxx-xxx-x",
        "productName": "Produkt A",
        "publisher": "Verlag ABC",
        "licenseCode": "ABC-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx",
        "licenseType": "Volumenlizenz",
        "countAquired": 5,
        "countAllocated": 0,
        "countExpired": 0,
        "countAllocatable": 5,
        "importDate": "2021-05-12",
    },
    {
        "licenseId": 2,
        "productId": "xxx-x-xxxxx-xxx-x",
        "productName": "Produkt D",
        "publisher": "Verlag KLM",
        "licenseCode": "KLM-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx",
        "licenseType": "Volumenlizenz",
        "countAquired": 5,
        "countAllocated": 0,
        "countExpired": 0,
        "countAllocatable": 5,
        "importDate": "2021-05-12",
    },
    {
        "licenseId": 3,
        "productId": "xxx-x-xxxxx-xxx-x",
        "productName": "Produkt D",
        "publisher": "Verlag KLM",
        "licenseCode": "KLM-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx",
        "licenseType": "Volumenlizenz",
        "countAquired": 5,
        "countAllocated": 5,
        "countExpired": 0,
        "countAllocatable": 0,
        "importDate": "2021-05-12",
    },
    {
        "licenseId": 4,
        "productId": "xxx-x-xxxxx-xxx-x",
        "productName": "Produkt E",
        "publisher": "Verlag KLM",
        "licenseCode": "KLM-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx",
        "licenseType": "Einzellizenz",
        "countAquired": 5,
        "countAllocated": 5,
        "countExpired": 0,
        "countAllocatable": 0,
        "importDate": "2021-05-08",
    },
]


class Instance(SchoolBaseModule):
    @sanitize(pattern=PatternSanitizer(default=".*"))
    def query(self, request):
        """Searches for licenses
        requests.options = {
                school
                timeFrom
                timeTo
                onlyAllocatableLicenses
                publisher
                licenseType
                userPattern
                productId
                product
                licenseCode
                pattern
        }
        """
        MODULE.info("licenses.query: options: %s" % str(request.options))
        pattern = request.options.get("pattern")
        fields = ["productId", "productName", "publisher", "licenseCode"]
        only_allocatable_licenses = request.options.get("onlyAllocatableLicenses")
        publisher = request.options.get("publisher")
        license_type = request.options.get("licenseType")
        time_from = request.options.get("timeFrom")
        time_to = request.options.get("timeTo")

        result = [
            lic
            for lic in licenses
            if (
                any(pattern.match(lic[field]) for field in fields)
                and (True if not only_allocatable_licenses else lic["countAllocatable"] > 0)
                and (True if publisher == "__all__" else lic["publisher"] == publisher)
                and (True if license_type == "__all__" else lic["licenseType"] == license_type)
                and (True if not time_from else lic["importDate"] >= time_from)
                and (True if not time_to else lic["importDate"] <= time_to)
            )
        ]

        MODULE.info("licenses.query: results: %s" % str(result))
        self.finished(request.id, result)

    @simple_response
    def get(self, licenseId):
        MODULE.info("licenses.get: licenseId: %s" % str(licenseId))
        if licenseId == 0:
            users = [
                {"dn": "dn1", "username": "max", "status": "allocated", "allocationDate": "2021-02-13"},
                {
                    "dn": "dn2",
                    "username": "bobby",
                    "status": "allocated",
                    "allocationDate": "2021-03-13",
                },
                {
                    "dn": "dn3",
                    "username": "daniel",
                    "status": "provisioned",
                    "allocationDate": "2021-02-08",
                },
            ]
        else:
            users = [
                {"dn": "dn4", "username": "xena", "status": "allocated", "allocationDate": "2021-02-13"},
                {
                    "dn": "dn5",
                    "username": "arnold",
                    "status": "allocated",
                    "allocationDate": "2021-03-13",
                },
                {
                    "dn": "dn6",
                    "username": "danny",
                    "status": "provisioned",
                    "allocationDate": "2021-02-08",
                },
            ]
        result = {
            "licenseId": 0,
            "productId": "xxx-x-xxxxx-xxx-x",
            "productName": "Produkt A",
            "publisher": "Verlag XYZ",
            "licenseCode": "XYZ-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx",
            "licenseType": "Volumenlizenz",
            "countAquired": 25,
            "countAllocated": 15,
            "countExpired": 0,
            "countAllocatable": 10,
            "importDate": "2021-05-12",
            "author": "Author ABC",
            "platform": "All",
            "reference": "reference",
            "specialLicense": "Demo license",
            "usage": "http://schule.de",
            "validityStart": "2021-05-12",
            "validityEnd": "2021-05-12",
            "validitySpan": "12",
            "ignore": True,
            #  'cover': '',
            "cover": "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",  # noqa: E501
            "users": users,
        }
        MODULE.info("licenses.get: result: %s" % str(result))
        return result

    @simple_response
    def publishers(self):
        MODULE.info("licenses.publishers")
        result = [
            {"id": "Verlag XYZ", "label": "Verlag XYZ"},
            {"id": "Verlag ABC", "label": "Verlag ABC"},
            {"id": "Verlag KLM", "label": "Verlag KLM"},
        ]
        MODULE.info("licenses.publishers: results: %s" % str(result))
        return result

    @simple_response
    def license_types(self):
        MODULE.info("licenses.license_types")
        result = [
            {"id": "Volumenlizenz", "label": _("Volumenlizenz")},
            {"id": "Einzellizenz", "label": _("Einzellizenz")},
        ]
        MODULE.info("licenses.license_types: results: %s" % str(result))
        return result

    @simple_response
    def set_ignore(self, license_id, ignore):
        MODULE.info(
            "licenses.set_ignore: license_id: %s ignore: %s"
            % (
                license_id,
                ignore,
            )
        )
        return True

    @simple_response
    def remove_from_users(self, user_dns):
        MODULE.info("licenses.set_ignore: user_dns: %s" % (user_dns,))
        return True

    def users_query(self, request):
        """Searches for users
        requests.options = {
                class
                workgroup
                pattern
        }
        """
        MODULE.info("licenses.query: options: %s" % str(request.options))
        result = [
            {
                "userId": 0,
                "username": "bmusterm",
                "firstname": "Bernd",
                "lastname": "Mustermann",
                "class": "5C",
                "workgroup": "Singen",
            },
            {
                "userId": 1,
                "username": "amusterf",
                "firstname": "Anna",
                "lastname": "Musterfrau",
                "class": "4A",
                "workgroup": "Fußball",
            },
            {
                "userId": 2,
                "username": "imusterm",
                "firstname": "Immanuel",
                "lastname": "Mustermann",
                "class": "5B",
                "workgroup": "Fußball",
            },
            {
                "userId": 3,
                "username": "lmusterf",
                "firstname": "Linda",
                "lastname": "Musterfrau",
                "class": "5C",
                "workgroup": "Singen",
            },
        ]

        MODULE.info("licenses.query: results: %s" % str(result))
        self.finished(request.id, result)
