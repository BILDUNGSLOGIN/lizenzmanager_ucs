# bildungslogin

## Getting started:

[Installation and usage](getting_started.md)


# Debugging

TODO

## Development

### Coverage

#### in host

Create a `.coveragerc` with the following content:

```ini
[run]
branch = False
parallel = True
source = univention.bildungslogin
        univention.udm.modules
        univention.admin.handlers.bildungslogin
[report]
ignore_errors = False
show_missing = True
omit = handlers/ucstest
        syntax.d/*
        hooks.d/*
include = /usr/lib/python2.7/dist-packages/univention/bildungslogin/*
        /usr/lib/python2.7/dist-packages/univention/admin/handlers/bildungslogin/*.py
        /usr/lib/python2.7/dist-packages/univention/udm/modules/bildungslogin_*.py
```

Then run (from the directory where `.coveragerc` is):

```bash
python -m coverage run /usr/bin/pytest -lvvx /usr/share/ucs-test/*_bildungslogin_*/*_*.py && \
  python -m coverage combine && \
  python -m coverage report && \
  python -m coverage html --directory=./htmlcov
```

#### in Docker container

TODO

## Beispiel Lizenzzuweisung

Eine testweise Lizenzzuweisung kann über UDM realisiert werden, solange das UMC Modul zur Lizenzzuweisung noch nicht
verfügbar ist. Dazu holen wir uns die Informationen zu einer Lizenz mittels
`udm bildungslogin/license list --filter code="VHT-7bd46a45-345c-4237-a451-4444736eb011"`
Wenn wir mit den vorherigen Beispieldaten arbeiten sehen wir nun ein Lizenzobjekt mit 25 von 25 verfügbaren Zuweisungen.
Um eine Zuweisung durchzuführen, müssen wir ein Assignment-Objekt der Lizenz editieren. Da hier noch alle verfügbar sind
nehmen wir uns ein beliebiges Objekt, welches in `assignments` referenziert ist und weisen es einem Nutzer zu. Dazu
benötigen wir noch die EntryUUID eines Nutzers, die wir mit dem folgenden Befehl ermitteln können:

```shell
root@dc0:~# univention-ldapsearch -LLL uid=demo_student entryUUID
dn: uid=demo_student,cn=schueler,cn=users,ou=DEMOSCHOOL,dc=realm4,dc=intranet
entryUUID: bc2d0d2a-224f-103b-9f8a-1587660bcd6c
```

Mit diesen Informationen können wir nun eine Zuweisung durchführen:

```shell
root@dc0:~# udm bildungslogin/assignment modify --dn cn=09d1834b-d238-466a-90f2-8c52c4b1cd07,cn=c23df3f1b32e0e78a8a98e7ea2eacd5ad90447be01643d87bb34ceba942e9a39,cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=realm4,dc=intranet --set assignee=bc2d0d2a-224f-103b-9f8a-1587660bcd6c --set time_of_assignment="$(date -I)" --set status=ASSIGNED
Object modified: cn=09d1834b-d238-466a-90f2-8c52c4b1cd07,cn=c23df3f1b32e0e78a8a98e7ea2eacd5ad90447be01643d87bb34ceba942e9a39,cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=realm4,dc=intranet
root@dc0:~# udm bildungslogin/assignment list --filter cn=09d1834b-d238-466a-90f2-8c52c4b1cd07
cn=09d1834b-d238-466a-90f2-8c52c4b1cd07
DN: cn=09d1834b-d238-466a-90f2-8c52c4b1cd07,cn=c23df3f1b32e0e78a8a98e7ea2eacd5ad90447be01643d87bb34ceba942e9a39,cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=realm4,dc=intranet
  assignee: bc2d0d2a-224f-103b-9f8a-1587660bcd6c
  cn: 09d1834b-d238-466a-90f2-8c52c4b1cd07
  status: ASSIGNED
  time_of_assignment: 2021-08-12
```

Wenn man diesen Nutzer nun über die Provisioning API abruft, erkennt man, dass ihm die Lizenz `VHT-7bd46a45-345c-4237-a451-4444736eb011`
zugeordnet ist.

## Beispiel Lizenz löschen

Das Ändern der Lizenzzuweisung im "Provisioned" Status wird unterbunden, da diese bereits im Medienregal eingelöst wurden. Es ist aber möglich eine komplette Lizenz zu löschen, damit werden alle Zuordungen auch entfernt, da diese im LDAP Kind-Objekte sind.

Anzeige aller Informationen und Zuordungen einer Lizenz:
```shell
root@dc0:~# udm bildungslogin/license list --filter code="WES-TEST-CODE-LZL07"
code=WES-TEST-CODE-LZL07
DN: cn=0fb9155c27655c172f2b2149108ed7736da6595eef302c8b160b95ee6112a0f8,cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=vbm,dc=schule-univention,dc=de
```
Löschen einer Lizenz
```shell
root@dc1:~# udm bildungslogin/license remove --dn cn=0fb9155c27655c172f2b2149108ed7736da6595eef302c8b160b95ee6112a0f8,cn=licenses,cn=bildungslogin,cn=vbm,cn=univention,dc=vbm,dc=schule-univention,dc=de
...
```
## Beispiel alle Daten löschen

Zum Aufräumen einer Testumgebung

Alle Lizenzen löschen:
```shell
root@dc0:~# for dn in $(udm bildungslogin/license list | sed -n 's/DN: //p'); do udm bildungslogin/license remove --dn $dn; done
```

