# bildungslogin plugin

This package contains a plugin for the ucsschool-apis app. It creates a REST API resource for `bildungslogin.de` to retrieve user data from.

## pyproject.toml

The configuration file of this python project and its entry point. A modern alternative to the setup.py workflow.
This project uses [**poetry**](https://python-poetry.org/docs/) as the build backend and project management tool.

## poetry.lock

An artefact for the build tool **poetry** that locks versions of dependencies for reproducible installations.

## bildungslogin_plugin/

The python package containing the plugin code.

## tests/ [optional]

This directory contains tests for this specific plugin

## Quickstart: test data creation

Create test license data:

```json
[
  {
    "lizenzcode": "VHT-7bd46a45-345c-4237-a451-4444736eb011",
    "product_id": "urn:bilo:medium:A0023#48-85-TZ",
    "lizenzanzahl": 25,
    "lizenzgeber": "VHT",
    "kaufreferenz": "2014-04-11T03:28:16 -02:00 4572022",
    "nutzungssysteme": "Antolin",
    "gueltigkeitsbeginn": "15-08-2021",
    "gueltigkeitsende": "14-08-2022",
    "gueltigkeitsdauer": "365",
    "sonderlizenz": "Lehrer"
  },
  ...
  ]
```

Import the licenses:

```bash
bildungslogin-license-import --license-file licenses.json --school DEMOSCHOOL
```

Execute in Python:

```python
from univention.bildungslogin.handlers import AssignmentHandler
from univention.admin.uldap import getAdminConnection

lo, po = getAdminConnection()
ah = AssignmentHandler(lo)
ah.assign_to_license(username="demo_student", license_code="VHT-7bd46a45-345c-4237-a451-4444736eb011")

# INFO: Modified 'vbm/assignment' object 'cn=2ab27fc7-28df-4960-bbf8-88cd8876be7c,cn=c23df3f1b32e0e78a8a98e7ea2eacd5ad90447be01643d87bb34ceba942e9a39,cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=uni,dc=dtr'
```

Result:

```bash
$ univention-ldapsearch -LLL cn=2ab27fc7-28df-4960-bbf8-88cd8876be7c
dn: cn=2ab27fc7-28df-4960-bbf8-88cd8876be7c,cn=c23df3f1b32e0e78a8a98e7ea2eacd5ad90447be01643d87bb34ceba942e9a39,cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=uni,dc=dtr
objectClass: top
objectClass: univentionObject
objectClass: vbmAssignment
univentionObjectType: vbm/assignment
cn: 2ab27fc7-28df-4960-bbf8-88cd8876be7c
vbmAssignmentStatus: ASSIGNED
vbmAssignmentAssignee: demo_student
vbmAssignmentTimeOfAssignment: 2021-08-04
```
