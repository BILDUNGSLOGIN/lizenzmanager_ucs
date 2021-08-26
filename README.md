# vbm-dev

## Quellen:

Projektordner mit dem Kunden: https://projects.univention.de/owncloud/f/14912

Guter Gesamtüberblick geht aus dem CR Dokument hervor: https://projects.univention.de/owncloud/f/14912

[Dokuwiki](https://hutten.knut.univention.de/dokuwiki/kunden:service-center_bildungslogin_bei_der_vbm_service_gmbh)

## Kundenkonto:

Service-Center BILDUNGSLOGIN bei der VBM Service GmbH (172906)

## Build pipline:

The packages are build using a gitlab pipeline. The pipeline is executed for any package which had changes to `debian/changelog`

## Packages:

The packages are build for release `4.4` with scope `bildungslogin`. The repository can be added by adding the following to `/etc/apt/sources.list`
```
deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-bildungslogin/all/
deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-bildungslogin/$(ARCH)/
```

## Jenkins:

A [Jenkins Job](https://jenkins.knut.univention.de:8181/job/Customers/job/172906_vbm/job/VBM%20-%20Development%20QA%20Test/) will deploy a school environment with scope `bildungslogin` and run the tests. The [configuration files](https://git.knut.univention.de/univention/prof-services/jenkins-cfgs/-/tree/master/vbm-project) are in a separate repository.

## Getting started:

[Installation and usage](getting_started.md)

## Release:

- [Changelog](CHANGELOG.md) aktualisieren.
- [getting started](getting_started.md) prüfen und gegebenenfalls aktualisieren.
- Nach Möglichkeit Update vom letzten Release zum aktuellen Stand prüfen.
- Release von `omar`
  - `announce_ucs_customer_scope --skip-tag -c 172906 -r 4.4-0 -s bildungslogin`
  - `sudo update_customer_mirror.sh 172906`

# Debuging

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
