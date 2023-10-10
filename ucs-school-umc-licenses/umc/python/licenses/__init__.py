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
import os
import random
import string
from datetime import datetime
from typing import Dict, List, Optional, Union
from subprocess import Popen
from .xlsxwriter import Workbook
import io
import base64

import psutil
from ucsschool.lib.school_umc_base import SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import USER_WRITE, USER_READ, LDAP_Connection
from univention.admin.syntax import iso8601Date
from univention.bildungslogin.handlers import (
    AssignmentHandler,
    BiloCreateError,
    LicenseHandler,
    ObjectType
)
from univention.bildungslogin.models import LicenseType, Role, Status
from univention.bildungslogin.license_import import import_license, load_license_file
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.error import UMC_Error
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import sanitize, allow_get_request
from univention.management.console.modules.sanitizers import (
    BooleanSanitizer,
    LDAPSearchSanitizer,
    ListSanitizer,
    StringSanitizer,
)
from univention.udm.exceptions import SearchLimitReached
from .cache import LdapRepository
from .constants import JSON_PATH, JSON_DIR, CACHE_BUILD_SCRIPT
from six.moves.urllib_parse import quote

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

    def __init__(self, *args, **kwargs):
        super(Instance, self).__init__(*args, **kwargs)
        self.repository = LdapRepository()

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
        self.repository.update(request.options.get("school"))
        try:
            sizelimit = int(ucr.get("directory/manager/web/sizelimit", 2000))
        except ValueError:
            sizelimit = None

        time_from = request.options.get("timeFrom")
        time_from = iso8601Date.to_datetime(time_from) if time_from else None
        time_to = request.options.get("timeTo")
        time_to = iso8601Date.to_datetime(time_to) if time_to else None

        expiry_from = request.options.get("expiryDateFrom")
        expiry_from = iso8601Date.to_datetime(expiry_from) if expiry_from else None
        expiry_to = request.options.get("expiryDateTo")
        expiry_to = iso8601Date.to_datetime(expiry_to) if expiry_to else None

        school_class = request.options.get("class", None)
        if not school_class:
            school_class = request.options.get("workgroup", None)
        try:
            licenses = self.repository.filter_licenses(
                is_advanced_search=request.options.get("isAdvancedSearch"),
                school=request.options.get("school"),
                time_from=time_from,
                time_to=time_to,
                only_available_licenses=request.options.get(
                    "onlyAvailableLicenses"),
                publisher=request.options.get("publisher"),
                license_types=request.options.get("licenseType"),
                user_pattern=request.options.get("userPattern"),
                product_id=request.options.get("productId"),
                product=request.options.get("product"),
                license_code=request.options.get("licenseCode"),
                pattern=request.options.get("pattern"),
                restrict_to_this_product_id=request.options.get(
                    "allocationProductId"),
                sizelimit=sizelimit,
                school_class=school_class,
                valid_status=request.options.get("validStatus"),
                usage_status=request.options.get("usageStatus"),
                expiry_date_from=expiry_from,
                expiry_date_to=expiry_to
            )
        except SearchLimitReached:
            raise UMC_Error(
                _("Hint"
                  "The number of licenses to be displayed is over {} and thus exceeds the set maximum value."
                  "You can use the filter/search parameters to limit the selection."
                  "Alternatively, the maximum number for the display can be adjusted by an administrator with "
                  "the UCR variable directory/manager/web/sizelimit."
                  ).format(sizelimit)
            )
        result = []
        for _license in licenses:
            metadata = _license.medium
            result.append({
                "licenseCode": _license.bildungsloginLicenseCode,
                "productId": _license.bildungsloginProductId,
                "productName": metadata.bildungsloginMetaDataTitle if metadata else '',
                "publisher": _license.publisher,
                "licenseTypeLabel": LicenseType.label(_license.bildungsloginLicenseType),
                "for": _license.bildungsloginLicenseSpecialType,
                "importDate": iso8601Date.from_datetime(_license.bildungsloginDeliveryDate),
                "validityStart": iso8601Date.from_datetime(
                    _license.bildungsloginValidityStartDate) if _license.bildungsloginValidityStartDate else None,
                "validityEnd": iso8601Date.from_datetime(
                    _license.bildungsloginValidityEndDate) if _license.bildungsloginValidityEndDate else None,
                "countAquired": undefined_if_none(_license.quantity, zero_as_none=True),
                "countAssigned": undefined_if_none(_license.quantity_assigned),
                "countAvailable": str(undefined_if_none(None if _license.quantity == 0 else _license.quantity_available)),
                "countExpired": undefined_if_none(_license.quantity_expired),
                "usageStatus": _license.bildungsloginUsageStatus,
                "expiryDate": optional_date2str(_license.bildungsloginExpiryDate),
                "validityStatus": _license.bildungsloginValidityStatus,
            })

        self.finished(request.id, result)

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
    def licenses_to_excel(self, request, ldap_user_write=None):
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
        self.repository.update(request.options.get("school"))
        try:
            sizelimit = int(ucr.get("directory/manager/web/sizelimit", 2000))
        except ValueError:
            sizelimit = None

        time_from = request.options.get("timeFrom")
        time_from = iso8601Date.to_datetime(time_from) if time_from else None
        time_to = request.options.get("timeTo")
        time_to = iso8601Date.to_datetime(time_to) if time_to else None

        school_class = request.options.get("class", None)
        if not school_class:
            school_class = request.options.get("workgroup", None)
        try:
            licenses = self.repository.filter_licenses(
                is_advanced_search=request.options.get("isAdvancedSearch"),
                school=request.options.get("school"),
                time_from=time_from,
                time_to=time_to,
                only_available_licenses=request.options.get(
                    "onlyAvailableLicenses"),
                publisher=request.options.get("publisher"),
                license_types=request.options.get("licenseType"),
                user_pattern=request.options.get("userPattern"),
                product_id=request.options.get("productId"),
                product=request.options.get("product"),
                license_code=request.options.get("licenseCode"),
                pattern=request.options.get("pattern"),
                restrict_to_this_product_id=request.options.get(
                    "allocationProductId"),
                sizelimit=sizelimit,
                school_class=school_class)
        except SearchLimitReached:
            raise UMC_Error(
                _("Hint"
                  "The number of licenses to be displayed is over {} and thus exceeds the set maximum value."
                  "You can use the filter/search parameters to limit the selection."
                  "Alternatively, the maximum number for the display can be adjusted by an administrator with "
                  "the UCR variable directory/manager/web/sizelimit."
                  ).format(sizelimit)
            )
        result = []
        for _license in licenses:
            metadata = _license.medium

            if _license.bildungsloginValidityStatus == '1':
                validity_status = _('valid')
            elif _license.bildungsloginValidityStatus == '0':
                validity_status = _('invalid')
            else:
                validity_status = _('unknown')

            if _license.bildungsloginUsageStatus == '1':
                usage_status = _('activated')
            elif _license.bildungsloginUsageStatus == '0':
                usage_status = _('not activated')
            else:
                usage_status = _('unknown')

            result.append([
                _license.bildungsloginLicenseCode,
                _license.bildungsloginProductId,
                metadata.bildungsloginMetaDataTitle if metadata else '',
                _license.publisher,
                LicenseType.label(_license.bildungsloginLicenseType),
                _license.bildungsloginLicenseSpecialType,
                iso8601Date.from_datetime(_license.bildungsloginDeliveryDate),
                iso8601Date.from_datetime(
                    _license.bildungsloginValidityStartDate) if _license.bildungsloginValidityStartDate else None,
                iso8601Date.from_datetime(
                    _license.bildungsloginValidityEndDate) if _license.bildungsloginValidityEndDate else None,
                undefined_if_none(_license.quantity, zero_as_none=True),
                undefined_if_none(_license.quantity_assigned),
                undefined_if_none(_license.quantity_available),
                undefined_if_none(_license.quantity_expired),
                validity_status,
                usage_status,
                optional_date2str(_license.bildungsloginExpiryDate)
            ])

        filename = 'bildungsloginLicense_' + ''.join(
            random.choice(string.ascii_letters) for _ in range(0, 20)) + '.xlsx'
        workbook = Workbook('/tmp/' + filename)
        worksheet = workbook.add_worksheet()

        columns = [_('License code'), _('Medium ID'), _('Medium'), _('Publisher'), _('License type'),
                   _('Special License type'),
                   _('Delivery Date'), _('Validity start'), _('Redemption period'), _('Number of licenses'),
                   _('Number of assigned licenses'),
                   _('Number of available licenses'), _('Number of expired licenses'), _('Validity status'),
                   _('Usage status'), _('Expiry date')]

        header_format = workbook.add_format({'bold': True})
        result.insert(0, columns)
        worksheet.set_column(0, len(columns) - 1, 25)

        for row_num, row in enumerate(result):
            for col_num, data in enumerate(row):
                if (row_num == 0):
                    worksheet.write(row_num, col_num, data, header_format)
                else:
                    worksheet.write(row_num, col_num, data)
        workbook.close()

        self.finished(request.id, {'URL': '/univention/command/licenses/download_export?export=%s' % (
            quote(filename),)})

    @allow_get_request
    @sanitize(export=StringSanitizer(required=True))
    def download_export(self, request):
        with open('/tmp/' + request.options.get("export"), 'rb') as fd:
            self.finished(request.id, fd.read(), mimetype="application/excel")
        os.remove('/tmp/' + request.options.get("export"))

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
        self.repository.update(request.options.get("school"))
        license_code = request.options.get("licenseCode")
        license = self.repository.get_license_by_code(license_code)
        assigned_users = self.repository.get_assigned_users_by_license(license)
        for assigned_user in assigned_users:
            assigned_user["dateOfAssignment"] = iso8601Date.from_datetime(
                assigned_user["dateOfAssignment"]
            )
        meta_data = license.medium
        result = {
            "countAquired": undefined_if_none(license.quantity, zero_as_none=True),
            "countAssigned": license.quantity_assigned,
            "countAvailable": undefined_if_none(license.quantity_available),
            "countExpired": undefined_if_none(license.quantity_expired),
            "ignore": license.bildungsloginIgnoredForDisplay,
            "importDate": iso8601Date.from_datetime(license.bildungsloginDeliveryDate),
            "licenseCode": license.bildungsloginLicenseCode,
            "licenseTypeLabel": LicenseType.label(license.bildungsloginLicenseType),
            "productId": meta_data.bildungsloginProductId if meta_data else '',
            "reference": license.bildungsloginPurchasingReference,
            "specialLicense": license.bildungsloginLicenseSpecialType,
            "usage": license.bildungsloginUtilizationSystems,
            "validityStart": optional_date2str(license.bildungsloginValidityStartDate),
            "validityEnd": optional_date2str(license.bildungsloginValidityEndDate),
            "validitySpan": license.bildungsloginValidityDuration,
            "author": meta_data.bildungsloginMetaDataAuthor if meta_data else '',
            "cover": meta_data.bildungsloginMetaDataCover or meta_data.bildungsloginMetaDataCoverSmall if meta_data else '',
            "productName": meta_data.bildungsloginMetaDataTitle if meta_data else '',
            "publisher": meta_data.bildungsloginMetaDataPublisher if meta_data else '',
            "users": assigned_users,
            "licenseType": license.bildungsloginLicenseType,
            "usageStatus": license.bildungsloginUsageStatus,
            "expiryDate": optional_date2str(license.bildungsloginExpiryDate),
            "validityStatus": license.bildungsloginValidityStatus,
        }
        MODULE.info("licenses.get: result: %s" % str(result))
        self.finished(request.id, result)

    @LDAP_Connection(USER_WRITE)
    def publishers(self, request, ldap_user_write=None):
        self.repository.update(request.options.get("school"))
        MODULE.info("licenses.publishers: options: %s" % str(request.options))
        result = [{"id": publisher, "label": publisher} for publisher in self.repository.get_publishers()]
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
        if success:
            self.repository.set_license_ignored(license_code, ignore)
        result = {
            "errorMessage": ""
            if success
            else _(
                "The 'Ignore' state cannot be changed because users are already assigned to the license."
            )
        }
        MODULE.info("licenses.set_ignore: result: %s" % str(result))
        self.finished(request.id, result)

    def _remove_from_objects(self, ldap_user_write, license_code, object_type, object_names):
        """ Generic function for "remove_from_*" endpoints """
        ah = AssignmentHandler(ldap_user_write)
        failed_assignments = ah.remove_assignment_from_objects(license_code,
                                                               object_type,
                                                               object_names)

        object_names = filter(lambda object_name: object_name not in failed_assignments, object_names)
        self.repository.remove_assignments(license_code, object_type, object_names)
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
        object_names = request.options.get("usernames")

        # Theoretically, we could reduce the user list here. Even if this would yield correct results,
        # neither the user nor the backend caching code can cope with the difference:
        # users_requested != users_assigned (but it is SUCCESS). So do this from the frontend,
        # and then pass down only user lists where these user counts do not differ.
        # leftover_users = self._not_assigned_users(ldap_user_write,
        #            request.options.get('usernames'),
        #            request.options.get('licenseCodes'))
        # if len(object_names) != len(leftover_users):
        #    MODULE.info("licenses.assign_to_users: reduced user list from %d to %d users" % (len(object_names),len(leftover_users)))
        #    object_names = leftover_users

        result = ah.assign_objects_to_licenses(request.options.get("licenseCodes"),
                                               ObjectType.USER,
                                               object_names)

        object_names = filter(lambda object_name: object_name not in result['failedAssignmentsObjects'], object_names)

        if len(object_names) > 0 and not result['notEnoughLicenses']:
            self.repository.add_assignments(request.options.get("licenseCodes"),
                                            ObjectType.USER,
                                            request.options.get("usernames"))
        MODULE.info("licenses.assign_to_users: result: %s" % str(result))
        self.finished(request.id, result)

    @sanitize(licenseCodes=ListSanitizer(required=True),
              usernames=ListSanitizer(required=True))
    @LDAP_Connection(USER_READ)
    def not_assigned_users(self, request, ldap_user_read=None):
        """ Return a list of users who do NOT have any of
            the requested license codes
        """
        MODULE.info("licenses.not_assigned_users: options: %s" % str(request.options))
        # Relocate the work into an internal function, so it can be called directly
        # from 'assign_to_users' above
        result = self._not_assigned_users(ldap_user_read, request.options.get('usernames'),
                                          request.options.get('licenseCodes'))
        MODULE.info("licenses.not_assigned_users: result: %s" % str(result))
        self.finished(request.id, result)

    def _not_assigned_users(self, lo, usernames, licenseCodes):
        """ Internal worker for 'not_assigned_users' """

        assigned_users = set()

        for licenseCode in licenseCodes:
            license = self.repository.get_license_by_code(licenseCode)
            # Work around possibly inconsistent cache
            if license is None:
                continue
            userlist = self.repository.get_assigned_users_by_license(license)
            for user in userlist:
                username = user.get('username')
                assigned_users.add(username)

        result = []
        for username in usernames:
            if username not in assigned_users:
                result += [username, ]

        return result

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

        if len(result['failedAssignments']) == 0 and not result['notEnoughLicenses']:
            self.repository.add_assignments(request.options.get("licenseCodes"),
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
        if len(result['failedAssignments']) == 0 and not result['notEnoughLicenses']:
            self.repository.add_assignments(request.options.get("licenseCodes"),
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

        if len(result['failedAssignments']) == 0 and not result['notEnoughLicenses']:
            self.repository.add_assignments(request.options.get("licenseCodes"),
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
        self.repository.update(request.options.get("school"))
        MODULE.info("licenses.query: options: %s" % str(request.options))
        school = request.options.get("school")
        pattern = request.options.get("pattern")
        workgroup = request.options.get("workgroup")
        school_class = request.options.get("class")

        users = self.repository.filter_users(pattern, school, workgroup, school_class)
        school_obj = self.repository.get_school(school)

        prefix = school + "-"
        result = []
        for user in users:
            result.append({
                "firstname": user.givenName,
                "lastname": user.sn,
                "username": user.userId,
                "role": Role.label(user.ucsschoolRole),
                "class": ", ".join(
                    [
                        _cls.cn[len(prefix):] if _cls.cn.startswith(prefix) else _cls.cn
                        for _cls in self.repository.get_classes(school_obj, user)
                    ]
                ),
                "workgroup": ", ".join(
                    wg.cn[len(prefix):] if wg.cn.startswith(prefix) else wg.cn
                    for wg in self.repository.get_workgroups(school_obj, user)
                ),
            })

        MODULE.info("licenses.query: result: %s" % str(result))
        self.finished(request.id, result)

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
            showOnlyAvailable: bool [optional]
        }
        """
        self.repository.update(request.options.get("school"))
        MODULE.info("licenses.products.query: options: %s" % str(request.options))
        result = []

        school = request.options.get("school")
        pattern = request.options.get("pattern")
        license_types = request.options.get("licenseType", None)

        user_count = None

        if license_types is not None and "WORKGROUP" in license_types:
            workgroup_name = request.options.get("groupName", None)

            if workgroup_name is not None:
                group = self.repository.get_workgroup_by_name(workgroup_name)

                if group:
                    user_count = len(group.memberUid)
        meta_data_objs = self.repository.filter_metadata(pattern)
        for meta_datum_obj in meta_data_objs:
            licenses = self.repository.filter_licenses(meta_datum_obj.bildungsloginProductId, school, license_types)

            if licenses:
                non_ignored_licenses = [license for license in licenses if not license.bildungsloginIgnoredForDisplay]

                sum_quantity = 0
                for license in non_ignored_licenses:
                    sum_quantity += license.quantity

                sum_num_assigned = 0
                for license in non_ignored_licenses:
                    sum_num_assigned += license.quantity_assigned

                sum_num_expired = 0
                sum_num_available = 0
                for license in non_ignored_licenses:
                    if license.is_expired:
                        sum_num_expired += license.quantity_expired
                    else:
                        sum_num_available += license.quantity_available

                # count info about licenses
                number_of_licenses = len(non_ignored_licenses)
                number_of_assigned_licenses = \
                    sum(1 for l in non_ignored_licenses if l.quantity_assigned > 0)
                number_of_expired_licenses = sum(1 for license in non_ignored_licenses if license.is_expired)
                # Counting of assignments depends on the license type: _get_total_number_of_assignments() encapsulates the logic.
                number_of_available_licenses = \
                    sum(1 for license in non_ignored_licenses if license.is_available)
                # Caller (grid query) can now request products with 'all' or 'only available' licenses
                if 'showOnlyAvailable' in request.options and request.options['showOnlyAvailable']:
                    if number_of_available_licenses < 1:
                        continue

                latest_delivery_date = max(lic_udm.bildungsloginDeliveryDate for lic_udm in licenses)
                result.append(
                    {
                        "productId": meta_datum_obj.bildungsloginProductId,
                        "title": meta_datum_obj.bildungsloginMetaDataTitle,
                        "publisher": meta_datum_obj.bildungsloginMetaDataPublisher,
                        "cover": meta_datum_obj.bildungsloginMetaDataCoverSmall or meta_datum_obj.bildungsloginMetaDataCover,
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
        pattern=LDAPSearchSanitizer(),
        licenseType=ListSanitizer(sanitizer=LDAPSearchSanitizer(add_asterisks=False))
    )
    @LDAP_Connection(USER_WRITE)
    def products_to_excel(self, request, ldap_user_write=None):
        """Searches for products
        requests.options = {
            school:  str
            pattern: str
            licenseType: List
            showOnlyAvailable: bool [optional]
        }
        """
        self.repository.update(request.options.get("school"))
        result = []

        school = request.options.get("school")
        pattern = request.options.get("pattern")
        license_types = request.options.get("licenseType", None)
        meta_data_objs = self.repository.filter_metadata(pattern)

        for meta_datum_obj in meta_data_objs:
            licenses = self.repository.filter_licenses(meta_datum_obj.bildungsloginProductId, school, license_types)

            if licenses:
                non_ignored_licenses = [license for license in licenses if not license.bildungsloginIgnoredForDisplay]

                sum_quantity = 0
                for license in non_ignored_licenses:
                    sum_quantity += license.quantity

                sum_num_assigned = 0
                for license in non_ignored_licenses:
                    sum_num_assigned += license.quantity_assigned

                sum_num_expired = 0
                sum_num_available = 0
                for license in non_ignored_licenses:
                    if license.is_expired:
                        sum_num_expired += license.quantity_expired
                    else:
                        sum_num_available += license.quantity_available

                # count info about licenses
                number_of_licenses = len(non_ignored_licenses)
                number_of_assigned_licenses = \
                    sum(1 for l in non_ignored_licenses if l.quantity_assigned > 0)
                number_of_expired_licenses = sum(1 for license in non_ignored_licenses if license.is_expired)
                # Counting of assignments depends on the license type: _get_total_number_of_assignments() encapsulates the logic.
                number_of_available_licenses = \
                    sum(1 for license in non_ignored_licenses if license.is_available)
                # Caller (grid query) can now request products with 'all' or 'only available' licenses
                if 'showOnlyAvailable' in request.options and request.options['showOnlyAvailable']:
                    if number_of_available_licenses < 1:
                        continue

                latest_delivery_date = max(lic_udm.bildungsloginDeliveryDate for lic_udm in licenses)
                result.append(
                    [
                        meta_datum_obj.bildungsloginProductId,
                        meta_datum_obj.bildungsloginMetaDataTitle,
                        meta_datum_obj.bildungsloginMetaDataPublisher,
                        undefined_if_none(sum_quantity),
                        sum_num_assigned,
                        undefined_if_none(sum_num_expired),
                        undefined_if_none(sum_num_available),
                        iso8601Date.from_datetime(latest_delivery_date),
                        number_of_licenses,
                        number_of_assigned_licenses,
                        number_of_expired_licenses,
                        number_of_available_licenses
                    ]
                )

        filename = 'bildungsloginProducts_' + ''.join(
            random.choice(string.ascii_letters) for _ in range(0, 20)) + '.xlsx'
        workbook = Workbook('/tmp/' + filename)
        worksheet = workbook.add_worksheet()

        columns = [_('Medium ID'), _('Medium'), _('Publisher'), _('Maximal number of users'), _('Assigned'),
                   _('Expired'),
                   _('Available'),
                   _('Import date'), _('Number of Licenses'), _('Number of assigned licenses'),
                   _('Number of expired licenses'),
                   _('Number of available licenses')]

        header_format = workbook.add_format({'bold': True})
        result.insert(0, columns)
        worksheet.set_column(0, len(columns) - 1, 25)

        for row_num, row in enumerate(result):
            for col_num, data in enumerate(row):
                if (row_num == 0):
                    worksheet.write(row_num, col_num, data, header_format)
                else:
                    worksheet.write(row_num, col_num, data)
        workbook.close()

        self.finished(request.id, {'URL': '/univention/command/licenses/download_export?export=%s' % (
            quote(filename),)})

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
        self.repository.update(request.options.get("school"))
        school = request.options.get("school")
        product_id = request.options.get("productId")
        licenses = self.repository.get_licenses_by_product_id(product_id, school)
        meta_data = self.repository.get_metadata_by_product_id(product_id)
        license_js_objs = [
            {
                "licenseCode": license.bildungsloginLicenseCode,
                "productId": meta_data.bildungsloginProductId,
                "productName": meta_data.bildungsloginMetaDataTitle,
                "publisher": license.publisher,
                "licenseTypeLabel": LicenseType.label(license.bildungsloginLicenseType),
                "validityStart": optional_date2str(license.bildungsloginValidityStartDate),
                "validityEnd": optional_date2str(license.bildungsloginValidityEndDate),
                "validitySpan": str(
                    license.bildungsloginValidityDuration) if license.bildungsloginValidityDuration else "",
                "ignore": _("Yes") if license.bildungsloginIgnoredForDisplay else _("No"),
                "countAquired":
                    str(undefined_if_none(None if license.quantity == 0 else license.quantity)),
                "countAssigned": str(license.quantity_assigned),
                "countAvailable":
                    str(undefined_if_none(None if license.quantity == 0 else license.quantity_available)),
                "countExpired":
                    str(undefined_if_none(license.quantity_expired)),
                "importDate": iso8601Date.from_datetime(license.bildungsloginDeliveryDate),
            }
            for license in licenses
        ]  # type: List[Dict[str, str]]
        # meta_data_udm = mh.get_meta_data_by_product_id(product_id)
        # meta_data = mh.from_udm_obj(meta_data_udm)
        result = {
            "title": meta_data.bildungsloginMetaDataTitle,
            "productId": meta_data.bildungsloginProductId,
            "publisher": meta_data.bildungsloginMetaDataPublisher,
            "author": meta_data.bildungsloginMetaDataAuthor,
            "description": meta_data.bildungsloginMetaDataDescription,
            "cover": meta_data.bildungsloginMetaDataCover or meta_data.bildungsloginMetaDataCoverSmall,
            "licenses": license_js_objs,
        }
        MODULE.info("licenses.products.get: result: %s" % str(result))
        self.finished(request.id, result)

    pickup_regex = r"^\s*[A-Z]{3}-[\S]{3,251}\s*$"

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

    @sanitize(school=SchoolSanitizer(required=True), pattern=StringSanitizer(default=""))
    @LDAP_Connection()
    def classes(self, request, ldap_user_read=None):
        """Returns a list of all classes of the given school"""
        self.repository.update(request.options.get("school"))
        school = request.options["school"]
        _classes = self.repository.get_classes_by_school(school)
        school_classes = []
        for school_class in _classes:
            school_classes.append({
                'id': school_class.entry_dn,
                'label': school_class.name
            })

        self.finished(
            request.id,
            school_classes
        )

    @sanitize(school=SchoolSanitizer(required=True), pattern=StringSanitizer(default=""))
    @LDAP_Connection()
    def workgroups(self, request, ldap_user_read=None):
        """Returns a list of all working groups of the given school"""
        self.repository.update(request.options.get("school"))
        school = request.options["school"]
        _workgroups = self.repository.get_workgroups_by_school(school)
        workgroups = []

        for workgroup in _workgroups:
            workgroups.append({'id': workgroup.entry_dn, 'label': workgroup.name})

        self.finished(
            request.id,
            workgroups
        )

    def _cache_is_running(self):
        for process in psutil.process_iter():
            try:
                if CACHE_BUILD_SCRIPT in process.cmdline():
                    return True
            except psutil.NoSuchProcess:
                pass
        return False

    def cache_rebuild(self, request):
        school = request.options.get("school")
        if not self._cache_is_running():
            Popen(['python ' + CACHE_BUILD_SCRIPT + " --school " + school], shell=True, stdout=None)
            self.finished(
                request.id,
                {'status': 1}
            )
        else:
            self.finished(
                request.id,
                {'status': 2}
            )

    @sanitize(school=SchoolSanitizer(required=True))
    def cache_status(self, request):
        self.repository.update(request.options.get("school"))
        self.finished(
            request.id,
            {
                'time': self.repository.cache_date(),
                'status': self._cache_is_running()
            }
        )

    @sanitize(school=SchoolSanitizer(required=True), licenseCodes=ListSanitizer(required=True))
    @LDAP_Connection(USER_WRITE)
    def licenses_delete(self, request, ldap_user_write):
        self.repository.update(request.options.get("school"))

        license_codes = request.options.get("licenseCodes")
        lh = LicenseHandler(ldap_user_write)
        lh.delete_license(license_codes)
        self.repository.delete_licenses(license_codes)

        for license_code in license_codes:
            MODULE.info('Deleted license: ' + license_code)

        self.finished(request.id, {
            'result': 'success'
        })

    def cache_rebuild_debug(self, request):
        if not self._cache_is_running() and ucr.get('bildungslogin/debug') == 'true':
            Popen(['python ' + CACHE_BUILD_SCRIPT], shell=True, stdout=None)
            self.finished(
                request.id,
                {'status': 1}
            )
        else:
            self.finished(
                request.id,
                {'status': 2}
            )
