# Überblick und Vorbereitung

Bildungslogin.de bietet ein zentrales Medienregal, über das sich viele verschiedene digitale Anwendungen deutscher Bildungsmedienverlage nutzen lassen. Mit dieser Implementierung wird der Aufbau und die Anbindung eines Lizenzmanagers auf Basis von Univention Corporate Server (UCS) mit Single-Sign-On für das Angebot von bildungslogin.de ermöglicht.

UCS und die Erweiterung UCS@school stellen für Schulträger und Bildungsministerien schulische Infrastruktur vornehmlich als Identity and Accessmanagement (IAM) bereit. Die dort bereits vorhandenen Benutzerkonten sollen für die Nutzung von bildungslogin.de verwendet werden können, inkl. Zuweisung und Übertragung von Lizenzen, sodass zum einen eine doppelte Pflege entfällt und zum anderen Lehrkräfte und SuS direkt aus der schulischen IT-Infrastruktur heraus mit ihren gewohnten Zugangsdaten auch bildungslogin.de nutzen können.

Die Implementierung ist aktuell mit `UCS@school 4.4 v9` möglich.

## Abstimmung mit bildungslogin.de

Für den Betrieb sind einige Information notwendig. Die folgenden **fettgedruckten** Parameter bitte mitteilen, daraufhin werden Parameter und Zugangsdaten für die Nutzung der Bildungslogin-API bereitgestellt.

### Parameter mitteilen

- **Name der Schule**: Wird für die Anzeige auf der Login-Seite des Bildungslogin verwendet.
- **Logo-URL**: Bild-URL des Schul-Logos (optional).
- **SSO DiscoveryUrl**: Basis-URL zum Ermitteln der SSO OIDC-Konfiguration, z.B. `https://ucs-sso.<domain.name>/.well-known/openid-configuration`.
- **SSO clientId**: Zugangsdaten für die SSO-Anbindung, siehe [UCS Handbuch](https://docs.software-univention.de/handbuch-4.4.html#domain:oidc).
- **SSO clientSecret**: Zugangsdaten für die SSO-Anbindung.
- **API baseUrl**: Basis-URL (Host, Port, Pfad) der REST-API des UCS-Systems. Diese URL muss im Internet erreichbar sein, z.B. `https://<schule-fqdn.domain.name>/ucsschool/apis/`
  - Hinweis: Über die gleiche Basis-URL werden alle Resourcen verfügbar gemacht: Die Authentication URL (`https://<schule-fqdn.domain.name>/ucsschool/apis/auth/token`) und die Provisionierungs URL (`https://<schule-fqdn.domain.name>/ucsschool/apis/bildungslogin/v1/user`).
- **API adminUsername**: Benutzer für die Nutzung der REST-API, z.B.: `bildungslogin-api-user`.
- **API adminPassword**: Passwort für die Nutzung der REST-API, siehe Setup der Provisioning API.

### Parameter und Zugangsdaten konfigurieren

- **ucs-id**: eindeutiger Schlüssel für dieses UCS-System, der Zugriff erfolgt in der produktiven Umgebung über `https://www.bildungslogin.de/app/#/sso/<ucs-id>`.
- **clientId**: ID für den Bezug von AccessTokens zur Nutzung der Bildungslogin-API, für `/etc/bildungslogin/config.ini`.
- **clientSecret**: Secret für den Bezug von AccessTokens zur Nutzung der Bildungslogin-API.

## Bekannte Probleme im MVP

**Die Konfiguration enthält Zugänge für die Testumgebung**

Problemumgehung: Die Datei `/etc/bildungslogin/config.ini` bitte anpassen für die Produktiven-Zugänge:

```bash
Scope = N753V49
ResourceServer = https://www.bildungslogin.de/api
```

**Der Cronjob zum Medien-Abruf ergibt einen Fehler `ValueError: No JSON object could be decoded`**

Problemumgehung: Für die Dummy-Codes werden keine Mediendaten bereitgestellt. Nach dem Einspielen von richtigen Codes wird der Fehler behoben sein.

**Der Single-Sign-On Login läuft ab und die UMC ist in einer Ladeschleife**

Problemumgehung: Das klingt nach dem bekannten [Bug 52888](https://forge.univention.org/bugzilla/show_bug.cgi?id=52888). Als Lösung bitte die erlaubte Zeitdifferenz der SAML Gültigkeit bei der Authentifizierung auf 12 Stunden setzen, wodurch der Login an einem Arbeitstag nicht mehr vorzeitig abläuft.

```bash
ucr set umc/saml/grace_time=43200
```

## Single-Sign-On und Portal

- Für SSO wird die `OpenID Connect Provider` benötigt. Die Installation und Konfiguration ist im [UCS Handbuch](https://docs.software-univention.de/handbuch-4.4.html#domain:oidc) beschrieben.
- Für die gesicherte und verschlüsselte Datenübertragung kann [Let’s Encrypt aus dem App Center](https://www.univention.de/produkte/univention-app-center/app-katalog/letsencrypt/) verwendet werden.
- Ein Blick in den Hilfe-Artikel ist hilfreich, wenn das [Portal und SSO umkonfiguriert](https://help.univention.com/t/reconfigure-ucs-single-sign-on/16161) wird.

# Installation

Informationen zur Deinstallation sind in einem separaten Kapitel weiter unten.

## 1. Apps installieren

1. Als erstes muss UCS@school installiert sein.
2. Anschließend muss die UCS@school APIs app installiert werden: `univention-app install ucsschool-apis`

## 2. Pakete installieren

Die Pakete können händisch gebaut werden.

Zur Konfiguration des UDM REST API Clients wird eine Java Runtime in den Docker Container installiert. Dafür muss dieser auf den deutschen Debian Mirror zugreifen. Ausgehende HTTP-Verbindungen zur IP `141.76.2.4` (`ftp.de.debian.org`) müssen dafür während der Installation erlaubt sein.

Nun können die Pakete installiert werden.

**ACHTUNG**: auf Primary und Backup nodes (DC Master und DC Backup) installiert das Joinscript `68udm-bildungslogin.inst` des Pakets `udm-bildungslogin` LDAP-Indices. Dafür wird der LDAP Server temporär angehalten. Bei großen Installationen kann dies eine Weile dauern.


Nach der Installation der Apps stehen die folgende Pakete bereit:
- `python-bildungslogin` (Programmbibliothek und CLI Lizenzimport)
- `udm-bildungslogin` (UDM Module)
- `ucs-school-umc-licenses` (UMC Modul)
- `bildungslogin-plugin` (Provisionierungs REST API Plugin für die `ucsschool-apis` App.)

## 3. Prüfen des `memberOf` overlays

Die UMC-Module setzen das LDAP-overlay `memberOf` voraus.
Ob das LDAP-overlay aktiviert ist lässt sich über die Systemdiagnose oder `ucr get ldap/overlay/memberof` prüfen.
Sollte es nicht aktiviert sein, sind die nötigen Schritte, zur Aktivierung, in folgendem Artikel beschrieben: [memberOf attribute: Group memberships of user and computer objects](https://help.univention.com/t/memberof-attribute-group-memberships-of-user-and-computer-objects/6439)

## 4. Einstellung der `sizelimit` UCR Variable

Einige der neuen UMC Module nutzen ein Limit um zu bestimmen, wie viele Ergebnisse sie maximal anzeigen, bevor sie eine
Einschränkung durch Suchparameter verlangen. Dieses Limit kann durch die UCR Variable `directory/manager/web/sizelimit`
gesetzt werden und ist standardmäßig auf 2000 eingestellt. Aktuell enmpfiehlt es sich dieses Limit für das Lizenzmanagement
auf 500 zu setzen. Dies kann mit dem Befehl `ucr set directory/manager/web/sizelimit=500` erreicht werden.

### Installationsprobleme

Probleme bei der Installation können häufig durch das erneute Ausführen der Join Skripte behoben werden:

```bash
univention-run-join-scripts --run-scripts --force 68udm-bildungslogin.inst
univention-run-join-scripts --run-scripts --force 69bildungslogin-plugin-openapi-client.inst
univention-run-join-scripts --run-scripts --force 70bildungslogin-plugin.inst
```

### Setup der Provisioning API

Wenn alles erfolgreich konfiguriert wurde, sind die beiden Joinskripte `69bildungslogin-plugin-openapi-client.inst` und `70bildungslogin-plugin.inst` ohne Fehler durchgelaufen (siehe Logfile: `/var/log/univention/join.log`).
Zur Verwendung der Provisioning API muss dann nur noch der für die Verbindung zu benutzende User aktiviert werden.

```bash
udm users/user modify \
  --dn "uid=bildungslogin-api-user,cn=users,$(ucr get ldap/base)" \
  --set disabled=0 \
  --set password="v3r7s3cr3t"
```

# Verwendung der Provisioning API

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

# Lizenzen importieren

Mit dem Tool `bildungslogin-license-import` lassen sich Lizenzen importieren.

## Beispiel Lizenz

Die json-Datei mit Dummy-Codes enhält gültige Lizenzdatensätze, aber mit frei erfundene Lizenzcodes. Sie dient dazu, in schulischen Testsystemen die internen Funktionen des Lizenzmanagers (ohne Medienzugriff in den Verlagssystemen) zu testen, ohne dass dafür echte Lizenzcodes benötigt werden. Die Datei wird zusammen mit den Paketen des ucs-Lizenzmanagers und einer Anleitung an die Pilotschulen ausgeliefert.

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

## Beispiel Import

Ein Import wird wie folgt durchgeführt:

`bildungslogin-license-import --license-file $PFAD_ZUR_LIZENZ --school $SCHUL_KÜRZEL`

# Metadaten importieren

Der Metadatenimport erfolgt automatisch.
Bei Bedarf kann er jedoch manuell über das CLI Tool `bildungslogin-media-import` ausgeführt werden.
Für den automatischen Import müssen die Zugangsdaten konfiguriert werden.

## Konfiguration

In die Datei `/etc/bildungslogin/config.ini` müssen die Zugangsdaten für die Metadaten API eingetragen werden.
Alternativ können diese dem CLI Tool auch direkt übergeben werden (`bildungslogin-media-import --help`).

## Manueller import

Ein Metadatenimport für eine Produkt ID kann nun wie folgt gestartet werden:

`bildungslogin-media-import --config-file /etc/bildungslogin/config.ini urn:bilo:medium:COR-9783060658336`

# Univention Management Console

In der UMC werden drei neue Module unter `Unterricht` angezeigt

- **Medienlizenzen anzeigen** Medien-Lizenzen im BILDUNGSLOGIN-Lizenzmanager anzeigen und durchsuchen
- **Medienlizenzen zuweisen** Medien-Lizenzen im BILDUNGSLOGIN-Lizenzmanager zuweisen oder entziehen
- **Lizenzierte Medien** Lizenzierte Medien im BILDUNGSLOGIN-Lizenzmanager anzeigen und durchsuchen

## Bekannte Einschränkungen
Die Lizenzen sollten, per Default, primär nach dem Lieferungsdatum und sekundär nach der Anzahl der verfügbaren Lizenzen sortiert werden.
Im Moment können wir keine Sekundär Sortierung unterstützen.

# Deinstallation
Die Implementierung erfolgt als MVP und lässt sich ohne Rückstände nach erfolgreichem Test entfernen.

## Schulserver

Auf Schulservern sind nur die UMC Module zur Lizenzverwaltung und ihre Abhängigkeiten installiert.
Sie können folgendermaßen restlos entfernt werden:

```bash
apt purge udm-bildungslogin-encoders python-bildungslogin ucs-school-umc-licenses
```

Zur Kontrolle ob noch andere Pakete installiert sind, kann folgendes ausgeführt werden:

```bash
dpkg -l | grep -E 'bildungslogin|umc-licenses'
```

## Primary (DC Master) und Backup Server

Auf dem Primary (DC Master) bzw. Backup Servern sind die UDM Modulpakete, LDAP Schema und die Provisionierungs API installiert.
Außerdem liegen auf ihnen die LDAP Daten.

### Pakete und Metadaten-Cache

Die Paketdeinstallation entfernt neben allen Programmdateien optional auch die Konfigurationsdateien, sowie den Metadatencache - nicht jedoch die Lizenzdaten.

Alle installierten Pakete können wir folgt angezeigt werden:

```bash
dpkg -l | grep -E 'bildungslogin|umc-licenses'
```

Zur Deinstallation unter Beibehaltung der Konfigurationsdateien `apt remove ...` verwenden.
Um die Konfigurationsdateien ebenfalls zu löschen `apt purge ...` ausführen:

```bash
apt purge bildungslogin-plugin bildungslogin-plugin-openapi-client python-bildungslogin ucs-school-umc-licenses udm-bildungslogin udm-bildungslogin-encoders
```

Die Unjoin Skripte sollten automatisch ausgeführt worden sein.
Falls nicht, können sie gestartet werden mit:

```bash
univention-run-join-scripts
```

### Lizenz-Daten

Um zusätzlich alle Lizenz-LDAP-Objekte zu löschen, kann der gesamte LDAP-Container für das Lizenzmanagement gelöscht werden:

```bash
ldapdelete -D "uid=Administrator,cn=users,$(ucr get ldap/base)" -H "ldap://$(ucr get ldap/master)" -W -x -r "cn=vbm,cn=univention,$(ucr get ldap/base)"
```

Dieser Befehl löscht ebenfalls die Lizenzzuweisungen und Lizenzmetadaten aus dem LDAP.

Der folgende Befehl sollte keine Objekte mehr finden (`such object (32)`):

```bash
univention-ldapsearch -LLL -b "cn=vbm,cn=univention,$(ucr get ldap/base)" dn
```

### LDAP Schemata und ACLs

Sind **alle** LDAP Objekte (Lizenzen, Zuweisungen und Metadaten) entfernt worden auf die sich die LDAP Schemata und ACLs beziehen, dürfen auch diese entfernt werden.

Wenn bei diesem Schritt etwas schiefgeht, startet u.U. der LDAP-Server nicht mehr, bis das Problem behoben wurde.
Wegen dieses Risokos und weil LDAP-Schemata und ACLs weder Platz noch Performance kosten, werden sie üblicherweise nicht gelöscht.

Folgendermaßen können LDAP ACLs und Schemata gelöscht werden:

```bash
. /usr/share/univention-lib/ldap.sh
ucs_unregisterLDAPExtension --acl 64bildungslogin-metadata
ucs_unregisterLDAPExtension --acl 64bildungslogin-license
ucs_unregisterLDAPExtension --schema bildungslogin
ucr commit /etc/ldap/slapd.conf
service slapd restart
```
