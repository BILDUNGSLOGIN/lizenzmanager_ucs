#!/usr/bin/env python
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

logger = logging.getLogger(__name__)

SEARCH_FILTER = ''.join([
    '(|',
    '(&(uid=*)(ucsschoolSchool=*))',
    '(&(objectClass=bildungsloginAssignment)(bildungsloginAssignmentAssignee=*))',
    '(objectClass=bildungsloginLicense)',
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
    }

    for entry in entries:
        entry_dn = entry[0]
        dict_entry = entry[1]
        obj = {
            'entryUUID': str(dict_entry['entryUUID'][0]),
            'entry_dn': str(entry_dn),
            'objectClass': [str(_class) for _class in dict_entry['objectClass']],
        }

        if 'person' in dict_entry['objectClass']:

            obj.update({
                'uid': str(dict_entry['uid'][0]),
                'givenName': str(dict_entry['givenName'][0]),
                'sn': str(dict_entry['sn'][0]),
                'ucsschoolSchool': [str(school) for school in dict_entry['ucsschoolSchool']],
                'ucsschoolRole': [str(role) for role in dict_entry['ucsschoolRole']]
            })
            processed_list['users'].append(obj)

        elif 'bildungsloginLicense' in dict_entry['objectClass']:
            obj.update({
                'bildungsloginLicenseCode': str(dict_entry['bildungsloginLicenseCode'][0]),
                'bildungsloginLicenseSpecialType': ''
            })

            if 'bildungsloginLicenseSpecialType' in dict_entry:
                obj['bildungsloginLicenseSpecialType'] = str(
                    dict_entry['bildungsloginLicenseSpecialType'][0])

            processed_list['licenses'].append(obj)
        elif ('bildungsloginAssignment' in dict_entry['objectClass']
              and 'bildungsloginAssignmentAssignee' in dict_entry):
            obj.update({
                'bildungsloginAssignmentAssignee':
                str(dict_entry['bildungsloginAssignmentAssignee'][0]),
                'bildungsloginAssignmentStatus':
                str(dict_entry['bildungsloginAssignmentStatus'][0]),
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

    return processed_list


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
    logging.basicConfig(level=args.log_level, format='%(message)s')
    logger.debug('Parsed arguments: {}'.format(args))
    main(args.cache_file)
