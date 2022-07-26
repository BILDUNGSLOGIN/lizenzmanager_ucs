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

from typing import Callable, Dict, List, Optional, Union

from ldap.dn import is_dn
from ldap.filter import escape_filter_chars
from ldap.filter import filter_format

from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.user import User
from ucsschool.lib.school_umc_base import SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import USER_WRITE, LDAP_Connection
from univention.admin.syntax import iso8601Date
from univention.bildungslogin.handlers import (
    AssignmentHandler,
    BiloCreateError,
    LicenseHandler,
    MetaDataHandler, ObjectType
)
from univention.bildungslogin.models import License, LicenseType, Role
from univention.bildungslogin.utils import ldap_escape
from univention.bildungslogin.license_import import import_license, load_license_file
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.error import UMC_Error
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import (
    BooleanSanitizer,
    LDAPSearchSanitizer,
    ListSanitizer,
    StringSanitizer,
)
from univention.udm import UDM
from univention.udm.exceptions import SearchLimitReached

_ = Translation("ucs-school-umc-licenses").translate


def undefined_if_none(value, zero_as_none=False):  # type: (Optional[int], bool) -> Union[unicode, int]
    """
    Return "undefined" if the input value is None
    If zero_as_none is set to True, returns "undefined" if value == 0
    """
    if value is None or zero_as_none and value == 0:
        return _("undefined")
    return value


def optional_date2str(date):
    if date:
        return iso8601Date.from_datetime(date)
    return ""


class Instance(SchoolBaseModule):
    @sanitize(
        isAdvancedSearch=BooleanSanitizer(required=True),
        school=SchoolSanitizer(required=True),
        onlyAvailableLicenses=BooleanSanitizer(required=True),
        timeFrom=StringSanitizer(regex_pattern=iso8601Date.regex, allow_none=True, default=None),
        timeTo=StringSanitizer(regex_pattern=iso8601Date.regex, allow_none=True, default=None),
        publisher=LDAPSearchSanitizer(add_asterisks=False, default=""),
        licenseType=ListSanitizer(sanitizer=LDAPSearchSanitizer(add_asterisks=False)),
        userPattern=LDAPSearchSanitizer(default=""),
        productId=LDAPSearchSanitizer(default=""),
        product=LDAPSearchSanitizer(default=""),
        licenseCode=LDAPSearchSanitizer(default=""),
        pattern=LDAPSearchSanitizer(default=""),
        allocationProductId=LDAPSearchSanitizer(add_asterisks=False, default=""),
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
            licenseType -- list
            userPattern -- str
            productId -- str
            product -- str
            licenseCode -- str
            pattern -- str
            class -- str
        }
        """
        MODULE.error("licenses.licenses_query: options: %s" % str(request.options))
        sizelimit = int(ucr.get("directory/manager/web/sizelimit", 2000))
        lh = LicenseHandler(ldap_user_write)
        time_from = request.options.get("timeFrom")
        time_from = iso8601Date.to_datetime(time_from) if time_from else None
        time_to = request.options.get("timeTo")
        time_to = iso8601Date.to_datetime(time_to) if time_to else None
        klass = request.options.get("class", None)
        if not klass:
            klass = request.options.get("workgroup", None)
        try:
            result = lh.search_for_licenses(
                is_advanced_search=request.options.get("isAdvancedSearch"),
                school=request.options.get("school"),
                time_from=time_from,
                time_to=time_to,
                only_available_licenses=request.options.get("onlyAvailableLicenses"),
                publisher=request.options.get("publisher"),
                license_types=request.options.get("licenseType"),
                user_pattern=request.options.get("userPattern"),
                product_id=request.options.get("productId"),
                product=request.options.get("product"),
                license_code=request.options.get("licenseCode"),
                pattern=request.options.get("pattern"),
                restrict_to_this_product_id=request.options.get("allocationProductId"),
                sizelimit=sizelimit,
                klass=klass,
            )
        except SearchLimitReached:
            raise UMC_Error(
                _(  "Hint"
                    "The number of licenses to be displayed is over {} and thus exceeds the set maximum value."
                    "You can use the filter/search parameters to limit the selection."
                    "Alternatively, the maximum number for the display can be adjusted by an administrator with "
                    "the UCR variable directory/manager/web/sizelimit."
                ).format(sizelimit)
            )
        for res in result:
            res["importDate"] = iso8601Date.from_datetime(res["importDate"])
            res["validityStart"] = iso8601Date.from_datetime(res["validityStart"]) if res.get("validityStart") else None
            res["validityEnd"] = iso8601Date.from_datetime(res["validityEnd"]) if res.get("validityEnd") else None
            res["countAquired"] = undefined_if_none(res["countAquired"], zero_as_none=True)
            res["countAvailable"] = undefined_if_none(res["countAvailable"])
            res["countExpired"] = undefined_if_none(res["countExpired"])

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
        license = lh.get_license_by_code(license_code)
        assigned_users = lh.get_assigned_users(license)
        for assigned_user in assigned_users:
            assigned_user["dateOfAssignment"] = iso8601Date.from_datetime(
                assigned_user["dateOfAssignment"]
            )
        meta_data = lh.get_meta_data_for_license(license)
        result = {
            "countAquired": undefined_if_none(license.license_quantity, zero_as_none=True),
            "countAssigned": lh.get_number_of_assigned_users(license),
            "countAvailable": undefined_if_none(lh.get_number_of_available_users(license)),
            "countExpired": undefined_if_none(lh.get_number_of_expired_unassigned_users(license)),
            "ignore": license.ignored_for_display,
            "importDate": iso8601Date.from_datetime(license.delivery_date),
            "licenseCode": license.license_code,
            "licenseTypeLabel": LicenseType.label(license.license_type),
            "productId": license.product_id,
            "reference": license.purchasing_reference,
            "specialLicense": license.license_special_type,
            "usage": license.utilization_systems,
            "validityStart": optional_date2str(license.validity_start_date),
            "validityEnd": optional_date2str(license.validity_end_date),
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
        result = [{"id": md.publisher, "label": md.publisher} for md in mh.get_all()]
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
            else _(
                "The 'Ignore' state cannot be changed because users are already assigned to the license."
            )
        }
        MODULE.info("licenses.set_ignore: result: %s" % str(result))
        self.finished(request.id, result)

    @staticmethod
    def _remove_from_objects(ldap_user_write, license_code, object_type, object_names):
        """ Generic function for "remove_from_*" endpoints """
        ah = AssignmentHandler(ldap_user_write)
        failed_assignments = ah.remove_assignment_from_objects(license_code,
                                                               object_type,
                                                               object_names)
        return {
            "failedAssignments": [
                {"username": fa[0], "error": fa[1]}
                for fa in failed_assignments
            ]
        }

    @sanitize(licenseCode=StringSanitizer(required=True),
              usernames=ListSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def remove_from_users(self, request, ldap_user_write=None):
        """
        Remove ASSIGNED users from the license
        requests.options = {
            licenseCode -- str
            usernames -- List[str]
        }
        """
        MODULE.info("licenses.remove_from_users: options: %s" % str(request.options))
        result = self._remove_from_objects(ldap_user_write,
                                           request.options.get("licenseCode"),
                                           ObjectType.USER,
                                           request.options.get("usernames"))
        MODULE.info("licenses.remove_from_users: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCode=StringSanitizer(required=True),
              group=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def remove_from_group(self, request, ldap_user_write=None):
        """
        Remove ASSIGNED group from the license
        requests.options = {
            licenseCode -- str
            group -- str
        }
        """
        MODULE.info("licenses.remove_from_group: options: %s" % str(request.options))
        result = self._remove_from_objects(ldap_user_write,
                                           request.options.get("licenseCode"),
                                           ObjectType.GROUP,
                                           [request.options.get("group")])
        MODULE.info("licenses.remove_from_group: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCode=StringSanitizer(required=True),
              school=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def remove_from_school(self, request, ldap_user_write=None):
        """
        Remove ASSIGNED school from the license
        requests.options = {
            licenseCode -- str
            school -- str
        }
        """
        MODULE.info("licenses.remove_from_school: options: %s" % str(request.options))
        result = self._remove_from_objects(ldap_user_write,
                                           request.options.get("licenseCode"),
                                           ObjectType.SCHOOL,
                                           [request.options.get("school")])
        MODULE.info("licenses.remove_from_school: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              usernames=ListSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_users(self, request, ldap_user_write=None):
        """Assign licenses to users
        requests.options = {
            licenseCodes -- List[str]
            usernames -- List[str]
        }
        """
        MODULE.info("licenses.assign_to_users: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.USER,
                                               request.options.get("usernames"))
        MODULE.info("licenses.assign_to_users: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              school=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_school(self, request, ldap_user_write=None):
        """Assign licenses to a school
        requests.options = {
            licenseCodes -- List[str]
            school -- str
        }
        """
        MODULE.info("licenses.assign_to_school: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.SCHOOL,
                                               [request.options.get("school")])
        MODULE.info("licenses.assign_to_school: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              schoolClass=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_class(self, request, ldap_user_write=None):
        """Assign licenses to a class
        requests.options = {
            licenseCodes -- List[str]
            schoolClass -- str
        }
        """
        MODULE.info("licenses.assign_to_class: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.GROUP,
                                               [request.options.get("schoolClass")])
        MODULE.info("licenses.assign_to_class: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              workgroup=StringSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def assign_to_workgroup(self, request, ldap_user_write=None):
        """Assign licenses to a workgroup
        requests.options = {
            licenseCodes -- List[str]
            workgroup -- str
        }
        """
        MODULE.info("licenses.assign_to_workgroup: options: %s" % str(request.options))
        ah = AssignmentHandler(ldap_user_write)
        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.GROUP,
                                               [request.options.get("workgroup")])
        MODULE.info("licenses.assign_to_workgroup: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        **{
            "school": SchoolSanitizer(required=True),
            "class": StringSanitizer(required=True),
            "workgroup": StringSanitizer(required=True),
            "pattern": LDAPSearchSanitizer(
                required=True,
            ),
        }
    )
    @LDAP_Connection(USER_WRITE)
    def users_query(self, request, ldap_user_write=None):
        """Searches for users
        requests.options = {
            school
            class
            workgroup
            pattern
        }
        """
        MODULE.info("licenses.query: options: %s" % str(request.options))
        udm = UDM(ldap_user_write).version(1)
        users_mod = udm.get("users/user")
        school = request.options.get("school")
        pattern = request.options.get("pattern")
        workgroup = request.options.get("workgroup")
        parts = [
            "(school={})".format(escape_filter_chars(school)),
            "(|(firstname={0})(lastname={0})(username={0}))".format(pattern),
        ]
        if workgroup != "__all__":
            parts.append("(memberOf={})".format(escape_filter_chars(workgroup)))
        klass = request.options.get("class")
        if klass != "__all__":
            if is_dn(klass):
                parts.append("(memberOf={})".format(escape_filter_chars(klass)))
            else:
                klass = LDAPSearchSanitizer().sanitize("p", {"p": klass})
                filter_s = "(name={school}-{klass})".format(
                    school=escape_filter_chars(school), klass=ldap_escape(klass)
                )
                class_dns = [cls.dn for cls in SchoolClass.get_all(ldap_user_write, school, filter_s)]
                if class_dns:
                    parts.append(
                        "(|{})".format(
                            "".join(["(memberOf={})".format(class_dn) for class_dn in class_dns])
                        )
                    )
                else:
                    MODULE.info("licenses.query: result: %s" % str([]))
                    self.finished(request.id, [])
        users_filter = "(&{})".format("".join(parts))
        users = users_mod.search(users_filter)
        workgroups = {wg.dn: wg.name for wg in WorkGroup.get_all(ldap_user_write, school)}
        prefix = school + "-"
        result = [
            {
                "firstname": user.props.firstname,
                "lastname": user.props.lastname,
                "username": user.props.username,
                "role": Role.label(user.props.ucsschoolRole),
                "class": ", ".join(
                    [
                        _cls[len(prefix):] if _cls.startswith(prefix) else _cls
                        for _cls in User.from_udm_obj(
                        user._orig_udm_object, school, ldap_user_write
                    ).school_classes.get(school, [])
                    ]
                ),
                "workgroup": ", ".join(
                    wg[len(prefix):] if wg.startswith(prefix) else wg
                    for wg in [workgroups[g] for g in user.props.groups if g in workgroups]
                ),
            }
            for user in users
        ]
        MODULE.info("licenses.query: result: %s" % str(result))
        self.finished(request.id, result)

    # def get_user_count_workgroup(self):

    @staticmethod
    def _sum_values_for_licenses(licenses, getter):
        # type: (List[License], Callable[[License], Optional[int]]) -> Optional[int]
        """
        Tries to sum all values returned by the getter
        If one of the values is None -> returns None
        """
        output = 0
        for license in licenses:
            value = getter(license)
            if value is None:
                return None
            output += value
        return output

    @sanitize(
        school=SchoolSanitizer(required=True),
        pattern=LDAPSearchSanitizer(),
        licenseType=ListSanitizer(sanitizer=LDAPSearchSanitizer(add_asterisks=False))
    )
    @LDAP_Connection(USER_WRITE)
    def products_query(self, request, ldap_user_write=None):
        """Searches for products
        requests.options = {
            school:  str
            pattern: str
            licenseType: List
        }
        """
        MODULE.info("licenses.products.query: options: %s" % str(request.options))
        result = []
        mh = MetaDataHandler(ldap_user_write)
        lh = LicenseHandler(ldap_user_write)
        school = request.options.get("school")
        pattern = request.options.get("pattern")
        license_types = request.options.get("licenseType", None)
        user_count = None
        if license_types is not None and "WORKGROUP" in license_types:
            workgroup_name = request.options.get("groupName", None)
            if workgroup_name is not None:
                udm = UDM(ldap_user_write).version(1)
                group_mod = udm.get("groups/group")
                group_filter = filter_format("(name=%s)", [workgroup_name])
                groups = group_mod.search(group_filter)
                if len(groups) == 1:
                    user_count = len(groups[0].props.users.objs)
        filter_s = "(|(product_id={0})(title={0})(publisher={0}))".format(pattern)
        meta_data_objs = mh.get_all(filter_s)
        for meta_datum_obj in meta_data_objs:
            licenses_udm = mh.get_udm_licenses_by_product_id(meta_datum_obj.product_id, school, license_types)
            if licenses_udm:
                non_ignored_lics_udm = [lic_udm for lic_udm in licenses_udm if not lic_udm.props.ignored]
                non_ignored_licenses = [lh.from_udm_obj(l) for l in non_ignored_lics_udm]

                # count info about users
                sum_quantity = self._sum_values_for_licenses(
                    non_ignored_licenses, lambda x: None if x.license_quantity == 0 else x.license_quantity)
                sum_num_assigned = self._sum_values_for_licenses(
                    non_ignored_licenses, lh.get_number_of_assigned_users)
                sum_num_expired = self._sum_values_for_licenses(
                    non_ignored_licenses, lh.get_number_of_expired_unassigned_users)
                sum_num_available = self._sum_values_for_licenses(
                    non_ignored_licenses, lh.get_number_of_available_users)

                # count info about licenses
                number_of_licenses = len(non_ignored_licenses)
                number_of_assigned_licenses =  \
                    sum(1 for l in non_ignored_licenses if l.num_assigned > 0)
                number_of_expired_licenses = sum(1 for l in non_ignored_licenses if l.is_expired)
                number_of_available_licenses = \
                    sum(1 for l in non_ignored_licenses if l.num_assigned == 0 and not l.is_expired)
                if number_of_available_licenses < 1:
                    continue

                latest_delivery_date = max(lic_udm.props.delivery_date for lic_udm in licenses_udm)
                result.append(
                    {
                        "productId": meta_datum_obj.product_id,
                        "title": meta_datum_obj.title,
                        "publisher": meta_datum_obj.publisher,
                        "cover": meta_datum_obj.cover_small or meta_datum_obj.cover,
                        "countAquired": undefined_if_none(sum_quantity),
                        "countAssigned": sum_num_assigned,
                        "countExpired": undefined_if_none(sum_num_expired),
                        "countAvailable": undefined_if_none(sum_num_available),
                        "latestDeliveryDate": iso8601Date.from_datetime(latest_delivery_date),
                        "countLicenses": number_of_licenses,
                        "countLicensesAssigned": number_of_assigned_licenses,
                        "countLicensesExpired": number_of_expired_licenses,
                        "countLicensesAvailable": number_of_available_licenses,
                        "user_count": user_count
                    }
                )
        MODULE.info("licenses.products.query: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(
        school=SchoolSanitizer(required=True),
        productId=StringSanitizer(required=True),
    )
    @LDAP_Connection(USER_WRITE)
    def products_get(self, request, ldap_user_write=None):
        """Get a product
        requests.options = {
            school
            productId
        }
        """
        MODULE.info("licenses.products.get: options: %s" % str(request.options))
        school = request.options.get("school")
        product_id = request.options.get("productId")
        mh = MetaDataHandler(ldap_user_write)
        lh = LicenseHandler(ldap_user_write)
        licenses_udm = mh.get_udm_licenses_by_product_id(product_id, school)
        licenses = [lh.from_udm_obj(license) for license in licenses_udm]  # type: List[License]
        meta_data_udm = mh.get_meta_data_by_product_id(product_id)
        meta_data = mh.from_udm_obj(meta_data_udm)
        license_js_objs = [
            {
                "licenseCode": license.license_code,
                "productId": meta_data.product_id,
                "productName": meta_data.title,
                "publisher": meta_data.publisher,
                "licenseTypeLabel": LicenseType.label(license.license_type),
                "validityStart": optional_date2str(license.validity_start_date),
                "validityEnd": optional_date2str(license.validity_end_date),
                "validitySpan": str(license.validity_duration) if license.validity_duration else "",
                "ignore": _("Yes") if license.ignored_for_display else _("No"),
                "countAquired":
                    str(undefined_if_none(None if license.license_quantity == 0 else license.license_quantity)),
                "countAssigned": str(lh.get_number_of_assigned_users(license)),
                "countAvailable":
                    str(undefined_if_none(lh.get_number_of_available_users(license))),
                "countExpired":
                    str(undefined_if_none(lh.get_number_of_expired_unassigned_users(license))),
                "importDate": iso8601Date.from_datetime(license.delivery_date),
            }
            for license in licenses
        ]  # type: List[Dict[str, str]]
       # meta_data_udm = mh.get_meta_data_by_product_id(product_id)
       # meta_data = mh.from_udm_obj(meta_data_udm)
        result = {
            "title": meta_data.title,
            "productId": meta_data.product_id,
            "publisher": meta_data.publisher,
            "author": meta_data.author,
            "description": meta_data.description,
            "cover": meta_data.cover or meta_data.cover_small,
            "licenses": license_js_objs,
        }
        MODULE.info("licenses.products.get: result: %s" % str(result))
        self.finished(request.id, result)

    pickup_regex = r"^\s*[a-zA-Z0-9]{3}-[a-zA-Z0-9]{3}-[a-zA-Z0-9]{3}-[a-zA-Z0-9]{3}\s*$"

    @staticmethod
    def _import_licenses(license_handler, license_file, school):
        # type: (LicenseHandler, str, str) -> None
        """
        Read retrieved licenses package and tries to import all of them into LDAP.
        Raises a BiloCreateError if at least one of the licenses wasn't imported.
        """
        errors = []
        for license in load_license_file(license_file, school):
            try:
                import_license(license_handler, license)
            except BiloCreateError as error:
                errors.append(error.message)
        if errors:
            error_message = "The following licenses were not imported: \n"
            error_message += "\n".join("  - {}".format(error) for error in errors)
            raise BiloCreateError(error_message)

    @sanitize(pickUpNumber=StringSanitizer(regex_pattern=pickup_regex))
    @LDAP_Connection(USER_WRITE)
    def get_license(self, request, ldap_user_write=None):
        """Import a license
        requests.options = {
            school
            pickup_number
        }
        """
        MODULE.info("licenses.import.get: options: %s" % str(request.options))
        pickup_number = "".join(request.options.get("pickUpNumber").rstrip().lstrip())
        school = request.options.get("school")
        license_handler = LicenseHandler(ldap_user_write)

        # Retrieve the requested license package
        license_file, licenses = license_handler.retrieve_license_data(pickup_number)

        # Import the retrieved license package and its metadata into LDAP
        self._import_licenses(license_handler, license_file, school)

        result = {
            "pickup": pickup_number,
            "school": school,
            "licenses": licenses
        }
        MODULE.info("licenses.import.get: result: %s" % str(result))
        self.finished(request.id, result)
