#!/usr/bin/env python
#
# Copyright 2022 Univention GmbH
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
#
"""Create a cache file for UCS@School API.

The script fetches objects from LDAP as found using the 'SEARCH_FILTER', transforms the returned
entries via 'transform_to_dictionary' and writes the result as a JSON string to JSON_PATH (or the
cache file given on the command-line).

Note that you can use '-' as an argument to '--cache-file' to get the result to stdout.

We extensively use doctests in this script as a replacement to unittests. You can run the tests via
'python -m doctest SCRIPTNAME'.
"""
import argparse
import json
import logging
import os
import re

from univention.management.console.config import ucr

logger = logging.getLogger(__name__)
entry_dn_pattern = re.compile(".*dc=.*")

JSON_PATH = '/var/lib/univention-appcenter/apps/ucsschool-apis/data/bildungslogin.json'
JSON_DIR = '/var/lib/univention-appcenter/apps/ucsschool-apis/data/'

PARSER = argparse.ArgumentParser('Create a cache file for the UCS@School API')
PARSER.add_argument(
    '--log-level',
    metavar='LEVEL',
    default='INFO',
    choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
    help='Set the logging level. Must be one of %(choices)s. (Default: %(default)s)',
)
PARSER.add_argument(
    '--cache-file',
    metavar='FILE',
    default=JSON_PATH,
    help='The path to the cache file. (Default: %(default)s)',
)
PARSER.add_argument(
    "--school",
    metavar='SCHOOL',
    help=(
        "School name used to create the folder in which the cache file will be saved."
    ),
)

SCHOOL = PARSER.parse_args().school

if SCHOOL:
    SEARCH_FILTER = ''.join([
        '(|',
        '(&(uid=*)(ucsschoolSchool=' + SCHOOL + ')',
        '(!(shadowExpire=1))' if ucr.get('bildungslogin/use-deactivated-users') != 'true' else '',
        ')',
        '(objectClass=bildungsloginAssignment)',
        '(&(objectClass=bildungsloginLicense)(bildungsloginLicenseSchool=' + SCHOOL + '))',
        '(objectClass=bildungsloginMetaData)',
        '(&(objectClass=ucsschoolOrganizationalUnit)(ou=' + SCHOOL + '))',
        '(&(objectClass=ucsschoolGroup)(ucsschoolRole=*' + SCHOOL + '*))',
        ')',
    ])
else:
    SEARCH_FILTER = ''.join([
        '(|',
        '(&(uid=*)(ucsschoolSchool=*)',
        '(!(shadowExpire=1))' if ucr.get('bildungslogin/use-deactivated-users') != 'true' else '',
        ')',
        '(objectClass=bildungsloginAssignment)',
        '(objectClass=bildungsloginLicense)',
        '(objectClass=bildungsloginMetaData)',
        '(objectClass=ucsschoolOrganizationalUnit)(objectClass=ucsschoolGroup)',
        ')',
    ])


def add_attribute_to_dictionary(dict_entry, obj, key):
    if key in dict_entry:
        obj[key] = str(
            dict_entry[key][0])


def transform_to_dictionary(entries):
    """Transform the given LDAP objects to the format needed by UCS@School API.

    >>> transform_to_dictionary([])
    {'users': [], 'licenses': [], 'assignments': [], 'schools': [], 'workgroups': [], 'classes': []}

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['person'],
    ...     'entryUUID': ['bar'],
    ...     'uid': ['a_uid'],
    ...     'givenName': ['a_givenName'],
    ...     'sn': ['a_sn'],
    ...     'ucsschoolSchool': [],
    ...     'ucsschoolRole': [],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [{
    ...     'entryUUID': 'bar',
    ...     'entry_dn': 'foo',
    ...     'objectClass': ['person'],
    ...     'uid': 'a_uid',
    ...     'givenName': 'a_givenName',
    ...     'sn': 'a_sn',
    ...     'ucsschoolSchool': [],
    ...     'ucsschoolRole': [],
    ...   }],
    ...   'licenses': [],
    ...   'assignments': [],
    ...   'schools': [],
    ...   'workgroups': [],
    ...   'classes': []}
    >>> result == expected
    True

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['bildungsloginLicense'],
    ...     'entryUUID': ['bar'],
    ...     'bildungsloginLicenseCode': ['a_bildungsloginLicenseCode'],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [{
    ...     'entryUUID': 'bar',
    ...     'entry_dn': 'foo',
    ...     'objectClass': ['bildungsloginLicense'],
    ...     'bildungsloginLicenseCode': 'a_bildungsloginLicenseCode',
    ...     'bildungsloginLicenseSpecialType': '',
    ...     },
    ...   ],
    ...   'assignments': [],
    ...   'schools': [],
    ...   'workgroups': [],
    ...   'classes': [],
    ... }
    >>> result == expected
    True

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['bildungsloginLicense'],
    ...     'entryUUID': ['bar'],
    ...     'bildungsloginLicenseCode': ['a_bildungsloginLicenseCode'],
    ...     'bildungsloginLicenseSpecialType': ['a_bildungsloginLicenseSpecialType'],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [
    ...     {'entryUUID': 'bar',
    ...      'entry_dn': 'foo',
    ...      'objectClass': ['bildungsloginLicense'],
    ...      'bildungsloginLicenseCode': 'a_bildungsloginLicenseCode',
    ...      'bildungsloginLicenseSpecialType': 'a_bildungsloginLicenseSpecialType',
    ...     },
    ...   ],
    ...   'assignments': [],
    ...   'schools': [],
    ...   'workgroups': [],
    ...   'classes': [],
    ... }
    >>> result == expected
    True

    >>> transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['bildungsloginAssignment'],
    ...     'entryUUID': ['bar'],
    ...     'bildungsloginLicenseCode': ['a_bildungsloginLicenseCode'],
    ...     'bildungsloginLicenseSpecialType': ['a_bildungsloginLicenseSpecialType'],
    ...    }),
    ... ])
    {'users': [], 'licenses': [], 'assignments': [], 'schools': [], 'workgroups': [], 'classes': []}

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['bildungsloginAssignment'],
    ...     'entryUUID': ['bar'],
    ...     'bildungsloginAssignmentAssignee': ['an_assignee'],
    ...     'bildungsloginAssignmentStatus': ['a_status'],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [],
    ...   'assignments': [
    ...     {'entryUUID': 'bar',
    ...      'entry_dn': 'foo',
    ...      'objectClass': ['bildungsloginAssignment'],
    ...      'bildungsloginAssignmentAssignee': 'an_assignee',
    ...      'bildungsloginAssignmentStatus': 'a_status',
    ...     },
    ...   ],
    ...   'schools': [],
    ...   'workgroups': [],
    ...   'classes': [],
    ... }
    >>> result == expected
    True

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['ucsschoolOrganizationalUnit'],
    ...     'entryUUID': ['bar'],
    ...     'ou': ['a_ou'],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [],
    ...   'assignments': [],
    ...   'schools': [
    ...     {'entryUUID': 'bar',
    ...      'entry_dn': 'foo',
    ...      'objectClass': ['ucsschoolOrganizationalUnit'],
    ...      'ou': 'a_ou',
    ...     },
    ...   ],
    ...   'workgroups': [],
    ...   'classes': [],
    ... }
    >>> result == expected
    True

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['ucsschoolGroup'],
    ...     'entryUUID': ['bar'],
    ...     'cn': ['a_cn'],
    ...     'ucsschoolRole': ['a_role'],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [],
    ...   'assignments': [],
    ...   'schools': [],
    ...   'workgroups': [],
    ...   'classes': [],
    ... }
    >>> result == expected
    True

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['ucsschoolGroup'],
    ...     'entryUUID': ['bar'],
    ...     'cn': ['a_cn'],
    ...     'ucsschoolRole': ['workgroup'],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [],
    ...   'assignments': [],
    ...   'schools': [],
    ...   'workgroups': [
    ...     {'entryUUID': 'bar',
    ...      'entry_dn': 'foo',
    ...      'objectClass': ['ucsschoolGroup'],
    ...      'cn': 'a_cn',
    ...      'ucsschoolRole': 'workgroup',
    ...      'memberUid': [],
    ...     },
    ...   ],
    ...   'classes': [],
    ... }
    >>> result == expected
    True

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['ucsschoolGroup'],
    ...     'entryUUID': ['bar'],
    ...     'cn': ['a_cn'],
    ...     'ucsschoolRole': ['school_class'],
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [],
    ...   'assignments': [],
    ...   'schools': [],
    ...   'workgroups': [],
    ...   'classes': [
    ...     {'entryUUID': 'bar',
    ...      'entry_dn': 'foo',
    ...      'objectClass': ['ucsschoolGroup'],
    ...      'cn': 'a_cn',
    ...      'ucsschoolRole': 'school_class',
    ...      'memberUid': [],
    ...     },
    ...   ],
    ... }
    >>> result == expected
    True

    >>> result = transform_to_dictionary([
    ...   ('foo',
    ...    {'objectClass': ['ucsschoolGroup'],
    ...     'entryUUID': ['bar'],
    ...     'cn': ['a_cn'],
    ...     'ucsschoolRole': ['school_class'],
    ...     'memberUid': ['member01', 'member02']
    ...    }),
    ... ])
    >>> expected = {
    ...   'users': [],
    ...   'licenses': [],
    ...   'assignments': [],
    ...   'schools': [],
    ...   'workgroups': [],
    ...   'classes': [
    ...     {'entryUUID': 'bar',
    ...      'entry_dn': 'foo',
    ...      'objectClass': ['ucsschoolGroup'],
    ...      'cn': 'a_cn',
    ...      'ucsschoolRole': 'school_class',
    ...      'memberUid': ['member01', 'member02'],
    ...     },
    ...   ],
    ... }
    >>> result == expected
    True
    """
    processed_list = {
        'users': [],
        'licenses': [],
        'assignments': [],
        'schools': [],
        'workgroups': [],
        'classes': [],
        'metadata': [],
    }

    for (entry_dn, dict_entry) in entries:
        obj = {
            'entryUUID': str(dict_entry['entryUUID'][0]),
            'entry_dn': str(entry_dn),
            'objectClass': [str(_class) for _class in dict_entry['objectClass']],
        }

        if not entry_dn_pattern.match(obj['entry_dn']):
            logger.warning("Corrupted DN by object %r with entry dn: %r", dict_entry['entryUUID'], entry_dn)

        if 'person' in dict_entry['objectClass']:
            if 'ucsschoolRole' not in dict_entry:
                logger.warning('Ignored user %s.', dict_entry['uid'][0])
                continue

            obj.update({
                'uid': str(dict_entry['uid'][0]),
                'givenName': "" if 'givenName' not in dict_entry else str(dict_entry['givenName'][0]),
                'sn': str(dict_entry['sn'][0]),
                'ucsschoolSchool': [str(school) for school in dict_entry['ucsschoolSchool']],
                'ucsschoolRole': [str(role) for role in dict_entry['ucsschoolRole']]
            })
            processed_list['users'].append(obj)

        elif 'bildungsloginLicense' in dict_entry['objectClass']:
            obj.update({
                'bildungsloginLicenseCode': str(dict_entry['bildungsloginLicenseCode'][0]),
                'bildungsloginProductId': str(dict_entry['bildungsloginProductId'][0]),
                'bildungsloginLicenseType': str(dict_entry['bildungsloginLicenseType'][0]),
                'bildungsloginLicenseSchool': str(dict_entry['bildungsloginLicenseSchool'][0]),
                'bildungsloginIgnoredForDisplay': str(dict_entry['bildungsloginIgnoredForDisplay'][0]),
                'bildungsloginLicenseQuantity': str(dict_entry['bildungsloginLicenseQuantity'][0]),
                'bildungsloginDeliveryDate': str(dict_entry['bildungsloginDeliveryDate'][0]),
                'bildungsloginLicenseProvider': str(dict_entry['bildungsloginLicenseProvider'][0]),
                'bildungsloginValidityDuration': '',
                'bildungsloginUtilizationSystems': '',
                'bildungsloginLicenseSpecialType': '',
                'bildungsloginUsageStatus': '',
                'bildungsloginExpiryDate': '',
                'bildungsloginValidityStatus': '',
                'groups': [],
                'user_strings': [],
                'quantity_assigned': 0,
            })

            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginValidityDuration')
            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginUtilizationSystems')
            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginValidityStartDate')
            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginValidityEndDate')
            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginLicenseSpecialType')

            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginUsageStatus')
            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginExpiryDate')
            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginValidityStatus')
            add_attribute_to_dictionary(dict_entry, obj, 'bildungsloginPurchasingReference')

            processed_list['licenses'].append(obj)
        elif 'bildungsloginAssignment' in dict_entry['objectClass']:
            obj.update({
                'bildungsloginAssignmentStatus':
                    str(dict_entry['bildungsloginAssignmentStatus'][0]),
                'bildungsloginAssignmentTimeOfAssignment': ''
            })

            if 'bildungsloginAssignmentTimeOfAssignment' in dict_entry:
                obj['bildungsloginAssignmentTimeOfAssignment'] = str(
                    dict_entry['bildungsloginAssignmentTimeOfAssignment'][0])

            if 'bildungsloginAssignmentAssignee' in dict_entry:
                obj.update({
                    'bildungsloginAssignmentAssignee':
                        str(dict_entry['bildungsloginAssignmentAssignee'][0]),
                })

            processed_list['assignments'].append(obj)
        elif 'ucsschoolOrganizationalUnit' in dict_entry['objectClass']:

            obj.update({'ou': str(dict_entry['ou'][0])})

            processed_list['schools'].append(obj)
        elif 'ucsschoolGroup' in dict_entry['objectClass']:

            obj.update({
                'cn': str(dict_entry['cn'][0]),
                'ucsschoolRole': str(dict_entry['ucsschoolRole'][0]),
                'memberUid': [str(member) for member in dict_entry.get('memberUid', [])],
            })

            if 'workgroup' in dict_entry['ucsschoolRole'][0]:
                processed_list['workgroups'].append(obj)
            elif 'school_class' in dict_entry['ucsschoolRole'][0]:
                processed_list['classes'].append(obj)
        elif 'bildungsloginMetaData' in dict_entry['objectClass']:
            obj.update({
                'bildungsloginProductId': str(dict_entry['bildungsloginProductId'][0]),
                'bildungsloginMetaDataTitle': str(dict_entry['bildungsloginMetaDataTitle'][0]),
                'bildungsloginMetaDataPublisher': str(dict_entry['bildungsloginMetaDataPublisher'][0]),
                'bildungsloginMetaDataCoverSmall': '',
                'bildungsloginMetaDataCover': '',
                'bildungsloginMetaDataDescription': '',
                'bildungsloginMetaDataAuthor': ''
            })

            if 'bildungsloginMetaDataDescription' in dict_entry:
                obj['bildungsloginMetaDataDescription'] = str(
                    dict_entry['bildungsloginMetaDataDescription'][0])

            if 'bildungsloginMetaDataAuthor' in dict_entry:
                obj['bildungsloginMetaDataAuthor'] = str(
                    dict_entry['bildungsloginMetaDataAuthor'][0])

            if 'bildungsloginMetaDataCoverSmall' in dict_entry:
                obj['bildungsloginMetaDataCoverSmall'] = str(
                    dict_entry['bildungsloginMetaDataCoverSmall'][0])

            if 'bildungsloginMetaDataCover' in dict_entry:
                obj['bildungsloginMetaDataCover'] = str(
                    dict_entry['bildungsloginMetaDataCover'][0])

            processed_list['metadata'].append(obj)

    assignments_map = get_assignment_map(processed_list['assignments'])
    processed_list['licenses'].sort(key=lambda license: license['bildungsloginDeliveryDate'], reverse=True)
    licenses = processed_list['licenses']
    users = processed_list['users']
    groups = processed_list['classes'] + processed_list['workgroups']
    schools = processed_list['schools']

    for _license in licenses:
        if _license['entry_dn'] in assignments_map:
            assignments = assignments_map[_license['entry_dn']]
            for assignment in assignments:
                if assignment['bildungsloginAssignmentStatus'] != 'AVAILABLE':
                    if _license['bildungsloginLicenseType'] in ['SINGLE', 'VOLUME']:
                        user = False
                        for _user in users:
                            if _user['entryUUID'] == assignment['bildungsloginAssignmentAssignee']:
                                user = _user
                                break
                        if user:
                            add_user_to_license(_license, user)
                        else:
                            _license['quantity_assigned'] += 1

                    elif _license['bildungsloginLicenseType'] == 'WORKGROUP':
                        for group in groups:
                            if group['entryUUID'] == assignment['bildungsloginAssignmentAssignee']:
                                for user in users:
                                    if user['uid'] in group['memberUid']:
                                        add_user_to_license(_license, user)
                                        _license['groups'].append(group['entry_dn'])
                                break
                    elif _license['bildungsloginLicenseType'] == 'SCHOOL':
                        for school in schools:
                            if school['entryUUID'] == assignment['bildungsloginAssignmentAssignee']:
                                for user in users:
                                    if school['ou'] in user['ucsschoolSchool']:
                                        add_user_to_license(_license, user)
                    else:
                        raise RuntimeError("Unknown license type: {}".format(_license['bildungsloginLicenseType']))

    return processed_list


assignments_map = {}


def get_assignment_map(assignments):
    if len(assignments_map) > 0:
        return assignments_map
    else:
        for assignment in assignments:
            license_dn = assignment['entry_dn'].split(',', 1)[1]
            if license_dn in assignments_map:
                assignments_map[license_dn].append(assignment)
            else:
                assignments_map.update({license_dn: [assignment]})
    return assignments_map


def add_user_to_license(_license, user):
    roles = []
    for role in user['ucsschoolRole']:
        roles.append(role.split(':', 1)[0])

    if _license['bildungsloginLicenseSpecialType'] != 'Lehrkraft' or (
            _license['bildungsloginLicenseSpecialType'] == 'Lehrkraft' and 'teacher' in roles):
        _license['quantity_assigned'] += 1
        _license['user_strings'].append(user['givenName'])
        _license['user_strings'].append(user['sn'])
        _license['user_strings'].append(user['uid'])


def get_products_from_licenses(dictionary):
    metadata = []

    for _metadata in dictionary.get('metadata', []):
        if any(_metadata.get('bildungsloginProductId') == license.get('bildungsloginProductId') for license in
               dictionary.get('licenses', [])):
            metadata.append(_metadata)

    return metadata


def filter_dictionary_by_school(dictionary, school):
    processed_list = {
        'users': [],
        'schools': [],
        'assignments': [],
        'licenses': [],
        'workgroups': [],
        'classes': [],
        'metadata': dictionary.get('metadata', []),
    }

    for _user in dictionary.get('users', []):
        if school in _user.get('ucsschoolSchool'):
            processed_list['users'].append(_user)

    for _school in dictionary.get('schools', []):
        if school == _school.get('ou'):
            processed_list['schools'].append(_school)

    for _assignment in dictionary.get('assignments', []):
        processed_list['assignments'].append(_assignment)

    for _license in dictionary.get('licenses', []):
        if school == _license.get('bildungsloginLicenseSchool'):
            processed_list['licenses'].append(_license)

    for _workgroup in dictionary.get('workgroups', []):
        processed_list['workgroups'].append(_workgroup)

    for _class in dictionary.get('classes', []):
        if str(_class.get('entry_dn')).find(school) >= 0:
            processed_list['classes'].append(_class)

    return processed_list


def store_school_cache_file(dictionary, school):
    if any(s.get('ou') == school for s in dictionary.get('schools', [])):
        tmp_school_folder = JSON_DIR + 'schools/' + school
        tmp_school_filepath = tmp_school_folder + '/cache.json'
        tmp_school_dict = dictionary
        tmp_school_dict['metadata'] = get_products_from_licenses(dictionary)

        assignments_map = get_assignment_map(tmp_school_dict['assignments'])

        tmp_school_dict['assignments'] = []
        for license in tmp_school_dict['licenses']:
            tmp_school_dict['assignments'] += assignments_map[license['entry_dn']]

        if not os.path.isdir(tmp_school_folder):
            os.makedirs(tmp_school_folder)

        if os.path.isfile(tmp_school_filepath):
            os.unlink(tmp_school_filepath)

        tmp_school_file = open(tmp_school_filepath, 'w')
        json.dump(tmp_school_dict, tmp_school_file)
        tmp_school_file.close()
        del tmp_school_folder, tmp_school_dict, tmp_school_filepath, tmp_school_file


def store_api_cache(filtered_dict, cache_file):
    needed_attributes = ['entryUUID',
                         'objectClass',
                         'entry_dn',
                         'uid',
                         'givenName',
                         'ou',
                         'cn',
                         'ucsschoolRole',
                         'sn',
                         'ucsschoolSchool',
                         'bildungsloginLicenseCode',
                         'bildungsloginLicenseSpecialType',
                         'memberUid',
                         'bildungsloginAssignmentAssignee',
                         'bildungsloginAssignmentStatus']

    for license in filtered_dict['licenses']:
        new_license = {}
        for key, value in license.iteritems():
            if key in needed_attributes:
                new_license.update({key: value})
        filtered_dict['licenses'][filtered_dict['licenses'].index(license)] = new_license
        del license

    del filtered_dict['metadata']

    tmp_filepath = cache_file + '~'
    tmp_file = open(tmp_filepath, 'w')
    json.dump(filtered_dict, tmp_file)
    tmp_file.close()

    if os.path.isfile(cache_file):
        os.unlink(cache_file)
    os.rename(tmp_filepath, cache_file)


def main(cache_file, school):
    """Start the main routine of the script.

    Fetch the LDAP objects, transform and filter them as needed and write the JSON objects to the
    given cache_file.
    """
    import univention.admin.uldap as uldap
    ldap_access, ldap_position = uldap.getAdminConnection()

    logger.info('Start searching objects in LDAP')
    response = ldap_access.search(
        filter=SEARCH_FILTER,
        scope='sub',
        attr=[
            'entryUUID',
            'objectClass',
            'uid',
            'givenName',
            'ou',
            'cn',
            'ucsschoolRole',
            'sn',
            'ucsschoolSchool',
            'bildungsloginLicenseCode',
            'bildungsloginLicenseSpecialType',
            'memberUid',
            'bildungsloginAssignmentAssignee',
            'bildungsloginAssignmentStatus',
            'bildungsloginProductId',
            'bildungsloginMetaDataTitle',
            'bildungsloginMetaDataPublisher',
            'bildungsloginMetaDataCover',
            'bildungsloginMetaDataCoverSmall',
            'bildungsloginMetaDataDescription',
            'bildungsloginMetaDataAuthor',
            'bildungsloginLicenseType',
            'bildungsloginLicenseSchool',
            'bildungsloginIgnoredForDisplay',
            'bildungsloginDeliveryDate',
            'bildungsloginLicenseQuantity',
            'bildungsloginValidityStartDate',
            'bildungsloginValidityEndDate',
            'bildungsloginValidityDuration',
            'bildungsloginUtilizationSystems',
            'bildungsloginPurchasingReference',
            'bildungsloginAssignmentTimeOfAssignment',
            'bildungsloginLicenseProvider',
            'bildungsloginUsageStatus',
            'bildungsloginExpiryDate',
            'bildungsloginValidityStatus'
        ],
    )
    logger.debug('Found {} objects'.format(len(response)))

    dictionary = transform_to_dictionary(response)
    logger.debug('After filtering and transformation {} objects remaining'.format(
        sum(len(objs) for objs in dictionary.values())))

    logger.debug("Convert to JSON and write to cache file")

    if school:
        store_school_cache_file(dictionary, school)
        for (dirpath, dirnames, filenames) in os.walk(JSON_DIR + 'schools/' + school + '/'):
            for filename in filenames:
                regex = re.compile('license-.*json')
                if regex.match(filename):
                    os.unlink(dirpath + filename)
            break

    else:
        for _school in dictionary.get('schools', []):
            store_school_cache_file(
                filter_dictionary_by_school(dictionary, _school.get('ou')),
                _school.get('ou')
            )
            for (dirpath, dirnames, filenames) in os.walk(JSON_DIR + 'schools/' + _school.get('ou') + '/'):
                for filename in filenames:
                    regex = re.compile('license-.*json')
                    if regex.match(filename):
                        os.unlink(dirpath + filename)
                break

        store_api_cache(dictionary, cache_file)

    for (dirpath, dirnames, filenames) in os.walk(JSON_DIR):
        for filename in filenames:
            regex = re.compile('license-.*json')
            if regex.match(filename):
                os.unlink(dirpath + filename)
        break

    logger.info("Finished")


if __name__ == '__main__':
    args = PARSER.parse_args()
    logging.basicConfig(level=args.log_level, format='%(levelname)s - %(message)s')
    logger.debug('Parsed arguments: {}'.format(args))
    main(args.cache_file, args.school)
