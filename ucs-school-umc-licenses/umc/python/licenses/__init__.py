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
from univention.admin.syntax import iso8601Date
from univention.bildungslogin.handlers import AssignmentHandler, LicenseHandler, MetaDataHandler
from univention.bildungslogin.utils import LicenseType
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import (
    BooleanSanitizer,
    LDAPSearchSanitizer,
    ListSanitizer,
    StringSanitizer,
)

_ = Translation("ucs-school-umc-licenses").translate


class Instance(SchoolBaseModule):
    @sanitize(
        isAdvancedSearch=BooleanSanitizer(required=True),
        school=StringSanitizer(required=True),
        timeFrom=LDAPSearchSanitizer(add_asterisks=False),
        timeTo=LDAPSearchSanitizer(add_asterisks=False),
        onlyAvailableLicenses=BooleanSanitizer(),
        publisher=LDAPSearchSanitizer(add_asterisks=False),
        licenseType=LDAPSearchSanitizer(add_asterisks=False),
        userPattern=LDAPSearchSanitizer(),
        productId=LDAPSearchSanitizer(),
        product=LDAPSearchSanitizer(),
        licenseCode=LDAPSearchSanitizer(),
        pattern=LDAPSearchSanitizer(),
    )
    @LDAP_Connection(USER_WRITE)
    def licenses_query(self, request, ldap_user_write=None):
        """Searches for licenses
        requests.options = {
            isAdvancedSearch -- boolean
            school -- str (schoolId)
            timeFrom -- str (ISO 8601 date string)
            timeTo -- str (ISO 8601 date string)
            onlyAllocatableLicenses -- boolean
            publisher -- str
            licenseType -- str
            userPattern -- str
            productId -- str
            product -- str
            licenseCode -- str
            pattern -- str
        }
        """
        MODULE.error("licenses.licenses_query: options: %s" % str(request.options))
        lh = LicenseHandler(ldap_user_write)
        time_from = request.options.get("timeFrom")
        time_from = iso8601Date.to_datetime(time_from) if time_from else None
        time_to = request.options.get("timeTo")
        time_to = iso8601Date.to_datetime(time_to) if time_to else None
        result = lh.search_for_licenses(
            is_advanced_search=request.options.get("isAdvancedSearch"),
            school=request.options.get("school"),
            time_from=time_from,
            time_to=time_to,
            only_available_licenses=request.options.get("onlyAvailableLicenses"),
            publisher=request.options.get("publisher"),
            license_type=request.options.get("licenseType"),
            user_pattern=request.options.get("userPattern"),
            product_id=request.options.get("productId"),
            product=request.options.get("product"),
            license_code=request.options.get("licenseCode"),
            pattern=request.options.get("pattern"),
        )
        for res in result:
            res["importDate"] = iso8601Date.from_datetime(res["importDate"])
        MODULE.info("licenses.licenses_query: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        #  school=StringSanitizer(required=True),
        licenseCode=StringSanitizer(required=True),
    )
    @LDAP_Connection(USER_WRITE)
    def licenses_get(self, request, ldap_user_write=None):
        """Get single license + meta data + assigned users
        requests.options = {
            #  school -- schoolId
            licenseCode -- str
        }
        """
        MODULE.info("licenses.get: options: %s" % str(request.options))
        # TODO should the school be incorperated in getting the license?
        # school = request.options.get("school")
        license_code = request.options.get("licenseCode")
        lh = LicenseHandler(ldap_user_write)
        license = lh.from_udm_obj(lh.get_udm_license_by_code(license_code))
        assigned_users = lh.get_assigned_users(license)
        for assigned_user in assigned_users:
            assigned_user["dateOfAssignment"] = iso8601Date.from_datetime(
                assigned_user["dateOfAssignment"]
            )
        meta_data = lh.get_meta_data_for_license(license)
        result = {
            "countAquired": lh.get_total_number_of_assignments(license),
            "countAssigned": lh.get_number_of_provisioned_and_assigned_assignments(license),
            "countAvailable": lh.get_number_of_available_assignments(license),
            "countExpired": lh.get_number_of_expired_assignments(license),
            "ignore": license.ignored_for_display,
            "importDate": iso8601Date.from_datetime(license.delivery_date),
            "licenseCode": license.license_code,
            "licenseTypeLabel": LicenseType.label(license.license_type),
            "productId": license.product_id,
            "reference": license.purchasing_reference,
            "specialLicense": license.license_special_type,
            "usage": license.utilization_systems,
            "validityStart": iso8601Date.from_datetime(license.validity_start_date),
            "validityEnd": iso8601Date.from_datetime(license.validity_end_date),
            "validitySpan": license.validity_duration,
            "author": meta_data.author,
            "cover": meta_data.cover or meta_data.cover_small,
            "productName": meta_data.title,
            "publisher": meta_data.publisher,
            "users": assigned_users,
        }
        MODULE.info("licenses.get: result: %s" % str(result))
        self.finished(request.id, result)

    @LDAP_Connection(USER_WRITE)
    def publishers(self, request, ldap_user_write=None):
        MODULE.info("licenses.publishers: options: %s" % str(request.options))
        mh = MetaDataHandler(ldap_user_write)
        result = [{"id": p, "label": p} for p in mh.get_all_publishers()]
        MODULE.info("licenses.publishers: result: %s" % str(result))
        self.finished(request.id, result)

    @LDAP_Connection(USER_WRITE)
    def license_types(self, request, ldap_user_write=None):
        MODULE.info("licenses.license_types: options: %s" % str(request.options))
        result = LicenseHandler.get_license_types()
        MODULE.info("licenses.license_types: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        licenseCode=StringSanitizer(required=True),
        ignore=BooleanSanitizer(required=True),
    )
    @LDAP_Connection(USER_WRITE)
    def set_ignore(self, request, ldap_user_write=None):
        """Set 'ignored' attribute of a license
        requests.options = {
            licenseCode -- str
            ignore -- boolean
        }
        """
        MODULE.info("licenses.set_ignore: options: %s" % str(request.options))
        license_code = request.options.get("licenseCode")
        ignore = request.options.get("ignore")
        lh = LicenseHandler(ldap_user_write)
        success = lh.set_license_ignore(license_code, ignore)
        result = {
            "errorMessage": ""
            if success
            else _("The 'Ignore' status can't be changed because the license has assigned users.")
        }
        MODULE.info("licenses.set_ignore: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        licenseCode=StringSanitizer(required=True),
        usernames=ListSanitizer(required=True),
    )
    @LDAP_Connection(USER_WRITE)
    def remove_from_users(self, request, ldap_user_write=None):
        """Remove ASSIGNED users from the license
        requests.options = {
            licenseCode -- str
            usernames -- List[str]
        }
        """
        MODULE.info("licenses.remove_from_users: options: %s" % str(request.options))
        license_code = request.options.get("licenseCode")
        usernames = request.options.get("usernames")
        ah = AssignmentHandler(ldap_user_write)
        failed_assignments = ah.remove_assignment_from_users(license_code, usernames)
        result = {
            "failedAssignments": [{"username": fa[0], "error": fa[1]} for fa in failed_assignments]
        }
        MODULE.info("licenses.remove_from_users: result: %s" % str(result))
        self.finished(request.id, result)

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

        MODULE.info("licenses.query: result: %s" % str(result))
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
                        "latestDeliveryDate": iso8601Date.from_datetime(
                            max(license.props.delivery_date for license in licenses)
                        ),
                    }
                )
        MODULE.info("licenses.products.query: result: %s" % str(result))
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

        MODULE.info("licenses..products.get: result: %s" % str(result))
        self.finished(request.id, result)
