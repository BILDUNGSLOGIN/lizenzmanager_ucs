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
from ucsschool.lib.school_umc_ldap_connection import USER_WRITE, LDAP_Connection
from univention.bildungslogin.handlers import LicenseHandler, MetaDataHandler
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize, simple_response
from univention.management.console.modules.sanitizers import LDAPSearchSanitizer, StringSanitizer

_ = Translation("ucs-school-umc-licenses").translate


class Instance(SchoolBaseModule):

    #  @sanitize(pattern=PatternSanitizer(default=".*")) # TODO
    @LDAP_Connection(USER_WRITE)
    def query(self, request, ldap_user_write=None):
        """Searches for licenses
        requests.options = {
                        school -- schoolId
                        timeFrom -- ISO 8601 date string
                        timeTo -- ISO 8601 date string
                        onlyAllocatableLicenses -- boolean
                        publisher -- string
                        licenseType -- string
                        userPattern -- string TODO use PatternSanitizer
                        productId -- string
                        product -- string
                        licenseCode -- string
                        pattern -- string TODO use PatternSanitizer
        }
        """
        MODULE.info("licenses.query: options: %s" % str(request.options))
        lh = LicenseHandler(ldap_user_write)
        result = lh.search_for_licenses(
            school=request.options.get("school"),
            time_from=request.options.get("timeFrom"),
            time_to=request.options.get("timeTo"),
            only_available_licenses=request.options.get("onlyAvailableLicenses"),
            publisher=request.options.get("publisher"),
            license_type=request.options.get("licenseType"),
            user_pattern=request.options.get("userPattern"),
            product_id=request.options.get("productId"),
            product=request.options.get("product"),
            license_code=request.options.get("licenseCode"),
            pattern=request.options.get("pattern"),
        )
        MODULE.info("licenses.query: results: %s" % str(result))
        self.finished(request.id, result)

    # TODO real backend call
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
            "cover": "https://edit.org/images/cat/book-covers-big-2019101610.jpg",
            "users": users,
        }
        MODULE.info("licenses.get: result: %s" % str(result))
        return result

    # TODO real backend call
    @simple_response
    def publishers(self):
        MODULE.info("licenses.publishers")
        result = [
            #  {"id": "Verlag XYZ", "label": "Verlag XYZ"},
            #  {"id": "Verlag ABC", "label": "Verlag ABC"},
            #  {"id": "Verlag KLM", "label": "Verlag KLM"},
        ]
        MODULE.info("licenses.publishers: results: %s" % str(result))
        return result

    # TODO real backend call
    @simple_response
    def license_types(self):
        MODULE.info("licenses.license_types")
        result = [
            #  {"id": "Volumenlizenz", "label": _("Volumenlizenz")},
            #  {"id": "Einzellizenz", "label": _("Einzellizenz")},
        ]
        MODULE.info("licenses.license_types: results: %s" % str(result))
        return result

    # TODO real backend call
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

    # TODO real backend call
    @simple_response
    def remove_from_users(self, user_dns):
        MODULE.info("licenses.set_ignore: user_dns: %s" % (user_dns,))
        return True

    # TODO real backend call
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

    @sanitize(
        school=StringSanitizer(required=True),
        pattern=LDAPSearchSanitizer(),
    )
    @LDAP_Connection(USER_WRITE)
    def products_query(self, request, ldap_user_write=None):
        """Searches for products
        requests.options = {
            school:  str
            pattern: str
        }
        """
        MODULE.info("licenses.products.query: options: %s" % str(request.options))
        result = []
        mh = MetaDataHandler(ldap_user_write)
        school = request.options.get("school")
        pattern = request.options.get("pattern")
        filter_s = "(|(product_id={0})(title={0})(publisher={0}))".format(pattern)
        meta_data_objs = mh.get_all(filter_s)
        for meta_datum_obj in meta_data_objs:
            licenses = mh.get_udm_licenses_by_product_id(meta_datum_obj.product_id)
            licenses = [license for license in licenses if license.props.school == school]
            if licenses:
                result.append(
                    {
                        "productId": meta_datum_obj.product_id,
                        "title": meta_datum_obj.title,
                        "publisher": meta_datum_obj.publisher,
                        "cover": meta_datum_obj.cover_small or meta_datum_obj.cover,
                        "countAquired": mh.get_total_number_of_assignments(meta_datum_obj, school),
                        "countAssigned": mh.get_number_of_provisioned_and_assigned_assignments(
                            meta_datum_obj, school
                        ),
                        "countExpired": mh.get_number_of_expired_assignments(meta_datum_obj, school),
                        "countAvailable": mh.get_number_of_available_assignments(meta_datum_obj, school),
                        "latestDeliveryDate": max([license.props.delivery_date for license in licenses]),
                    }
                )
        MODULE.info("licenses.products.query: results: %s" % str(result))
        self.finished(request.id, result)

    @LDAP_Connection(USER_WRITE)
    def products_get(self, request, ldap_user_write=None):
        """Get a product
        requests.options = {
            school
            productId
        }
        """
        MODULE.info("licenses.products.get: options: %s" % str(request.options))
        result = {
            "publisher": "Verlag A",
            "platform": "Platform",
            "productId": "xxx-yyy",
            "productName": "Produkt A",
            "cover": "https://upload.wikimedia.org/wikipedia/commons/0/0f/Eiffel_Tower_Vertical.JPG",
            "author": "Authro A",
            "licenses": [
                {
                    "licenseCode": "KLM-xxx-yyy",
                    "licenseType": "Volumenlizenz",
                    "validityStart": "2021-08-08",
                    "validityEnd": "2021-08-09",
                    "validitySpan": "1",
                    "ignore": "Nein",
                    "countAquired": 25,
                    "countAssigned": 12,
                    "countExpired": 2,
                    "countAvailable": 12,
                    "importDate": "2021-08-08",
                },
                {
                    "licenseCode": "KLM-xxx-zzz",
                    "licenseType": "Volumenlizenz",
                    "validityStart": "2021-08-08",
                    "validityEnd": "2021-08-09",
                    "validitySpan": "1",
                    "ignore": "Ja",
                    "countAquired": 25,
                    "countAssigned": 12,
                    "countExpired": 2,
                    "countAvailable": 12,
                    "importDate": "2021-08-08",
                },
            ],
        }

        MODULE.info("licenses..products.get: results: %s" % str(result))
        self.finished(request.id, result)
