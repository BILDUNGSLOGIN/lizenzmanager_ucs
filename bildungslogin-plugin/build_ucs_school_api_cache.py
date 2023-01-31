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
import re

logger = logging.getLogger(__name__)
entry_dn_pattern = re.compile(".*dc=.*")

SEARCH_FILTER = ''.join([
    '(|',
    '(&(uid=*)(ucsschoolSchool=*))',
    '(objectClass=bildungsloginAssignment)',
    '(objectClass=bildungsloginLicense)',
    '(objectClass=bildungsloginMetaData)',
    '(objectClass=ucsschoolOrganizationalUnit)(objectClass=ucsschoolGroup)',
    ')',
])

JSON_PATH = '/var/lib/univention-appcenter/apps/ucsschool-apis/data/bildungslogin.json'

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
    type=argparse.FileType('w'),
    help='The path to the cache file. (Default: %(default)s)',
)


def get_assignment_by_license(assignments, license):
    for assignment in assignments:
        if license['entry_dn'] in assignment['entry_dn']:
            return assignment


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
                'bildungsloginValidityDuration': '',
                'bildungsloginUtilizationSystems': '',
                'bildungsloginLicenseSpecialType': '',
                'groups': [],
            })

            if 'bildungsloginValidityDuration' in dict_entry:
                obj['bildungsloginValidityDuration'] = str(
                    dict_entry['bildungsloginValidityDuration'][0])

            if 'bildungsloginUtilizationSystems' in dict_entry:
                obj['bildungsloginUtilizationSystems'] = str(
                    dict_entry['bildungsloginUtilizationSystems'][0])

            if 'bildungsloginValidityStartDate' in dict_entry:
                obj['bildungsloginValidityStartDate'] = str(
                    dict_entry['bildungsloginValidityStartDate'][0])

            if 'bildungsloginValidityEndDate' in dict_entry:
                obj['bildungsloginValidityEndDate'] = str(
                    dict_entry['bildungsloginValidityEndDate'][0])

            if 'bildungsloginLicenseSpecialType' in dict_entry:
                obj['bildungsloginLicenseSpecialType'] = str(
                    dict_entry['bildungsloginLicenseSpecialType'][0])

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
                'bildungsloginMetaDataAuthor': '',
                'bildungsloginPurchasingReference': ''
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

            if 'bildungsloginPurchasingReference' in dict_entry:
                obj['bildungsloginPurchasingReference'] = str(
                    dict_entry['bildungsloginPurchasingReference'][0])

            processed_list['metadata'].append(obj)

    quantity_map = get_assignment_quantity_map(processed_list['assignments'], processed_list['users'])

    for license in processed_list['licenses']:
        if license['bildungsloginLicenseType'] in ['SINGLE', 'VOLUME']:
            if license['entry_dn'] in quantity_map:
                license.update({'quantity_assigned': quantity_map[license['entry_dn']]['count'],
                                'user_strings': quantity_map[license['entry_dn']]['user_strings']})
            else:
                license.update({'quantity_assigned': 0, 'user_strings': []})
        elif license['bildungsloginLicenseType'] == 'WORKGROUP':
            group = False
            assignment = get_assignment_by_license(processed_list['assignments'], license)
            if assignment['bildungsloginAssignmentStatus'] != 'AVAILABLE':
                for _group in processed_list['classes']:
                    if _group['entryUUID'] == assignment['bildungsloginAssignmentAssignee']:
                        group = _group
                        break

                if not group:
                    for _group in processed_list['workgroups']:
                        if _group['entryUUID'] == assignment['bildungsloginAssignmentAssignee']:
                            group = _group
                            break
                license.update({'quantity_assigned': len(group['memberUid']),
                                'user_strings': quantity_map[license['entry_dn']]['user_strings']})
                license['groups'].append(group['entry_dn'])
            else:
                license.update({'quantity_assigned': 0, 'user_strings': []})

        elif license['bildungsloginLicenseType'] == 'SCHOOL':
            assignment = get_assignment_by_license(processed_list['assignments'], license)
            if assignment['bildungsloginAssignmentStatus'] != 'AVAILABLE':
                counter = 0
                for school in processed_list['schools']:
                    if school['entryUUID'] == assignment['bildungsloginAssignmentAssignee']:
                        for user in processed_list['users']:
                            if school['ou'] in user['ucsschoolSchool']:
                                counter += 1
                license.update(
                    {'quantity_assigned': counter, 'user_strings': quantity_map[license['entry_dn']]['user_strings']})
            else:
                license.update({'quantity_assigned': 0, 'user_strings': []})
        else:
            raise RuntimeError("Unknown license type: {}".format(license.license_type))

    return processed_list


def get_assignment_quantity_map(assignments, users):
    dn_map = {}
    for assignment in assignments:
        if assignment['bildungsloginAssignmentStatus'] != 'AVAILABLE':
            license_dn = assignment['entry_dn'].split(',', 1)[1]
            found_user = False

            for user in users:
                if user['entryUUID'] == assignment['bildungsloginAssignmentAssignee']:
                    found_user = user
                    break

                if license_dn in dn_map:
                    dn_map[license_dn]['count'] += 1
                    if found_user:
                        dn_map[license_dn]['user_strings'].append(found_user['givenName'])
                        dn_map[license_dn]['user_strings'].append(found_user['sn'])
                        dn_map[license_dn]['user_strings'].append(found_user['uid'])
                else:
                    if found_user:
                        dn_map.update({
                            license_dn: {
                                'count': 1,
                                'user_strings': [found_user['givenName'], found_user['sn'], found_user['uid']]
                            },
                        })
                    else:
                        dn_map.update({
                            license_dn: {
                                'count': 1,
                                'user_strings': []
                            },
                        })
    return dn_map


def main(cache_file):
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
        ],
    )
    logger.debug('Found {} objects'.format(len(response)))

    filtered_dict = transform_to_dictionary(response)
    logger.debug('After filtering and transformation {} objects remaining'.format(
        sum(len(objs) for objs in filtered_dict.values())))

    logger.debug("Convert to JSON and write to cache file")
    json.dump(filtered_dict, cache_file)

    logger.info("Finished")


if __name__ == '__main__':
    args = PARSER.parse_args()
    logging.basicConfig(level=args.log_level, format='%(levelname)s - %(message)s')
    logger.debug('Parsed arguments: {}'.format(args))
    main(args.cache_file)
