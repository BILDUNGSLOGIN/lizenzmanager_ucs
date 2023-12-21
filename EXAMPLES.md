# Tests und Verifizierungen

## Lizenzen importieren

Mit dem Tool `bildungslogin-license-import` lassen sich Lizenzen importieren.

### Beispiel Lizenz

Das folgende Beispiel zeigt den Inhalt einer json-Datei für valide Lizenzdatensätze, aber mit frei erfundene Lizenzcodes. Eine entsprechende JSON-Datei kann dazu verwendet werden, in schulischen Testsystemen die internen Funktionen des Lizenzmanagers (ohne Medienzugriff in den Verlagssystemen) zu testen, ohne dass dafür echte Lizenzcodes benötigt werden. (Achtung: Bei aktivierter Lizenzstatus-API werden solche Dummy-Lizenzen mit 1-2 Tagen Zeitversatz nach der Zuweisung den Gültigkeitsstatus „ungültig“ erhalten und können dann nicht mehr zugewiesen werden.)

```json
[
  {
    "lizenzcode": "WES-DEMO-CODE-0000",
    "product_id": "urn:bilo:medium:WEB-14-124227",
    "lizenzanzahl": 60,
    "lizenzgeber": "WES",
    "kaufreferenz": "Lizenzmanager-Testcode",
    "nutzungssysteme": "Testcode ohne Medienzugriff",
    "gueltigkeitsbeginn": "",
    "gueltigkeitsende": "",
    "gueltigkeitsdauer": "Schuljahreslizenz",
    "sonderlizenz": ""
  },
  {
    "lizenzcode": "CCB-DEMO-CODE-0000",
    "product_id": "urn:bilo:medium:610081",
    "lizenzanzahl": 60,
    "lizenzgeber": "CCB",
    "kaufreferenz": "Lizenzmanager-Testcode",
    "nutzungssysteme": "Testcode ohne Medienzugriff",
    "gueltigkeitsbeginn": "",
    "gueltigkeitsende": "",
    "gueltigkeitsdauer": "397 Tage",
    "sonderlizenz": ""
  }
]
```

### Beispiel Import

Ein Import wird wie folgt durchgeführt:

`bildungslogin-license-import --license-file $PFAD_ZUR_LIZENZ --school $SCHUL_KÜRZEL`

## Metadaten importieren

Der Metadatenimport erfolgt automatisch.
Bei Bedarf kann er jedoch manuell über das CLI Tool `bildungslogin-media-import` ausgeführt werden.
Für den automatischen Import müssen die Zugangsdaten konfiguriert werden.

### Konfiguration

In die Datei `/etc/bildungslogin/config.ini` müssen die Zugangsdaten für die Metadaten API eingetragen werden.
Alternativ können diese dem CLI Tool auch direkt übergeben werden (`bildungslogin-media-import --help`).

### Manueller import

Ein Metadatenimport für eine Produkt ID kann nun wie folgt gestartet werden:

`bildungslogin-media-import --config-file /etc/bildungslogin/config.ini urn:bilo:medium:COR-9783060658336`

## Verwendung der Provisioning API

Mit dem Usernamen `bildungslogin-api-user` und dem Passwort kann die API genutzt werden.

Der Zugriff erfolgt in zwei Schritten:

1) Authorization

Der Token kann folgendermaßen geholt werden:

```bash
curl -X 'POST'   'https://FQDN/ucsschool/apis/auth/token' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=bildungslogin-api-user&password=v3r7s3cr3t'
```

Die Antwort ist:

```json
{
  "access_token":"eyJ0eXAiOiJKV1...",
  "token_type":"bearer"
}
```

2) Provisionierung von Nutzerdaten

Die Daten des Users `demo_student` können mit folgendem Befehl abgerufen werden:

```bash
curl -X 'GET' \
  'https://FQDN/ucsschool/apis/bildungslogin/v1/user/demo_student' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1...'
```

Zur interaktiven Erforschung der API findet sich eine Swagger UI sich unter https://FQDN/ucsschool/apis/docs.


### Beispiel Lizenzzuweisung via CLI

Um eine Zuweisung durchzuführen, müssen wir ein Assignment-Objekt der Lizenz editieren. Nach einem initialen Lizenzimport sind noch alle "assignments" verfügbar. Daher nehmen wir uns ein beliebiges Objekt, welches in `assignments` referenziert ist und weisen es einem Nutzer zu. Dies geschieht mittels der EntryUUID eines Nutzers, die wir mit dem folgenden Befehl ermitteln können:

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

Zum Aufräumen einer Testumgebung (Achtung: dies löscht sämtliche Lizenzen aller Schulen des Systems!)

Alle Lizenzen löschen:

```shell
root@dc0:~# for dn in $(udm bildungslogin/license list | sed -n 's/DN: //p'); do udm bildungslogin/license remove --dn $dn; done
```
