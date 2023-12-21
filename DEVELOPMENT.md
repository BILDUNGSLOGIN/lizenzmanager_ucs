# Architecture
The bildungslogin- module is made up of the following main components:
- a udm- module with currently three methods: bildungslogin/assignments, bildungslogin/licenses, bildungslogin/metadata
- a GUI- part for the UCS@School- UMC
- a server API for the BILDUNGSLOGIN to query assigned licenses
- a schema- extension to store licenses, metadata and assignments in the LDAP

## Schema- Extension
The gross of the license- handling is done in the ldap under the module- storage `cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,$LDAP_BASE`

Directly underneath this DN, the actual licenses are stored. Under the licenses, the actual assignments are then stored:
- for single- and volume licenses with one assignment entry per available license
- for group- licenses with only one single assignment entry

The assignment entry is then amended with the EntryUUID of the assigned unit, which is either
- for single- and volume licenses the **EntryUUID of the User** or
- for group- licenses with the **EntryUUID of the Group**

Hence the tree looks as follows:
```
LICENSE_MODULE_BASE
|
 -- licenses
   |
    -- assignments --> EntryUUID of Assignee (or Group)
```

## Logging

- The UMC- Module logs to `/var/log/univention/management-console-module-licenses.log`, the HTTP-API Log for UCSScrools also logs to `/var/log/univention/ucsschool-apis/http.log`
- there is a specific logfile for the mediaupdate- actions: `/var/log/univention/bildungslogin-media-update.log`

## Further Development

Die Entwicklung des UCS- Lizenzmanagers wird von BILDUNGSLOGIN getrieben. Gewünschte Anpassungen sollten dort angesprochen werden:  [Kontakt](https://info.bildungslogin.de/kontakt).
