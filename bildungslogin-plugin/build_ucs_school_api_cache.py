#!/usr/bin/python
#import asyncio
import json
import pprint
from datetime import datetime
from typing import List

#from ucsschool.apis.utils import LDAPSettings, LDAPCredentials, LDAPAccess
import univention.admin.uldap as uldap

#from ldap3 import Entry, Server, Connection, SUBTREE


SEARCH_FILTER = '(|(&(uid=*)(ucsschoolSchool=*))(&(objectClass=bildungsloginAssignment)(' \
                'bildungsloginAssignmentAssignee=*))' \
                '(objectClass=bildungsloginLicense)' \
                '(objectClass=ucsschoolOrganizationalUnit)(objectClass=ucsschoolGroup))'

JSON_PATH = '/var/lib/univention-appcenter/apps/ucsschool-apis/data/bildungslogin.json'

#LDAP_BINDDN = 'cn=admin,dc=ucs,dc=test,dc=myschool,dc=bildungslogin,dc=de'
#LDAP_SECRETFILE = '/etc/ldap.secret'

#f = open(LDAP_SECRETFILE,"r")
#LDAP_SECRET = f.read().encode('utf8')


#def transform_to_dictionary(entries: List[Entry]):
def transform_to_dictionary(entries):
    processed_list = {
        'users': [],
        'licenses': [],
        'assignments': [],
        'schools': [],
        'workgroups': [],
        'classes': [],
    }

    for entry in entries:
        #dict_entry = dict(entry['attributes'])
        entry_dn = entry[0]
        dict_entry = entry[1]
        obj = {
            'entryUUID': str(dict_entry['entryUUID'][0]),
            'entry_dn': str(entry_dn),  # str(entry['dn'][0]),
            'objectClass': []
        }

        for object_class in dict_entry['objectClass']:
            obj['objectClass'].append(str(object_class))

        if 'person' in dict_entry['objectClass']:

            obj.update({
                'uid': str(dict_entry['uid'][0]),
                'givenName': str(dict_entry['givenName'][0]),
                'sn': str(dict_entry['sn'][0]),
                'ucsschoolSchool': [],
                'ucsschoolRole': []
            })

            for school in dict_entry['ucsschoolSchool']:
                obj['ucsschoolSchool'].append(str(school))

            for role in dict_entry['ucsschoolRole']:
                obj['ucsschoolRole'].append(str(role))

            processed_list['users'].append(obj)
        elif 'bildungsloginLicense' in dict_entry['objectClass']:
            obj.update({
                'bildungsloginLicenseCode': str(dict_entry['bildungsloginLicenseCode'][0]),
                'bildungsloginLicenseSpecialType': ''
            })

            #if hasattr(entry, 'bildungsloginLicenseSpecialType'):
            if 'bildungsloginLicenseSpecialType' in dict_entry:
                obj['bildungsloginLicenseSpecialType'] = str(
                    dict_entry['bildungsloginLicenseSpecialType'][0])

            processed_list['licenses'].append(obj)
        elif 'bildungsloginAssignment' in dict_entry['objectClass']:
            if 'bildungsloginAssignmentAssignee' in dict_entry:
                obj.update({
                    'bildungsloginAssignmentAssignee':
                    str(dict_entry['bildungsloginAssignmentAssignee'][0]),
                    'bildungsloginAssignmentStatus':
                    str(dict_entry['bildungsloginAssignmentStatus'][0]),
                    #'entry_dn': str(entry_dn)               # str(entry['dn'][0])
                })

                processed_list['assignments'].append(obj)
        elif 'ucsschoolOrganizationalUnit' in dict_entry['objectClass']:

            obj.update({'ou': str(dict_entry['ou'][0])})

            processed_list['schools'].append(obj)
        elif 'ucsschoolGroup' in dict_entry['objectClass']:

            obj.update({
                'cn': str(dict_entry['cn'][0]),
                'ucsschoolRole': str(dict_entry['ucsschoolRole'][0]),
                'memberUid': [],
            })

            #if hasattr(entry, 'memberUid'):
            if 'memberUid' in dict_entry:
                for member in dict_entry['memberUid']:
                    obj['memberUid'].append(str(member))

            #if 'workgroup' in str(dict_entry['ucsschoolRole']):
            if 'workgroup' in dict_entry['ucsschoolRole'][0]:
                processed_list['workgroups'].append(obj)
            #elif 'school_class' in str(dict_entry['ucsschoolRole']):
            elif 'school_class' in dict_entry['ucsschoolRole'][0]:
                processed_list['classes'].append(obj)

    return processed_list


#async def main(json_path=JSON_PATH):
def main(json_path=JSON_PATH):
    #ldap_settings = LDAPSettings()
    #ldap_credentials = LDAPCredentials(ldap_settings)
    #ldap_access = LDAPAccess(ldap_settings, ldap_credentials)

    #server = Server('localhost')
    #ldap_access = Connection(server,
    #                            user=LDAP_BINDDN,
    #                            password=LDAP_SECRET,
    #                            raise_exceptions=False)
    #ldap_access.bind()
    ldap_access, ldap_position = uldap.getAdminConnection()
    print(str(datetime.now()) + " - start search")
    response = ldap_access.search(
        #search_base = 'dc=ucs,dc=test,dc=myschool,dc=bildungslogin,dc=de',
        filter=SEARCH_FILTER,
        scope='sub',
        attr=[
            'entryUUID', 'objectClass', 'uid', 'givenName', 'ou', 'cn', 'ucsschoolRole', 'sn',
            'ucsschoolSchool', 'bildungsloginLicenseCode', 'bildungsloginLicenseSpecialType',
            'memberUid', 'bildungsloginAssignmentAssignee', 'bildungsloginAssignmentStatus'
        ])
    print(str(datetime.now()) + " - start filtering")

    #print pprint.pformat(response,indent=3,width=160)

    filtered_dict = transform_to_dictionary(response)
    print(str(datetime.now()) + " - start converting to json")
    json_string = json.dumps(filtered_dict)
    print(str(datetime.now()) + " - writing cache file")
    f = open(JSON_PATH, 'w')
    f.write(json_string)
    f.close()
    #ldap_access.unbind()
    print(str(datetime.now()) + " - finished")


if __name__ == '__main__':
    #asyncio.run(main())
    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(main())
    main()
