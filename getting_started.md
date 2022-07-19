# Überblick und Vorbereitung

Bildungslogin.de bietet ein zentrales Medienregal, über das sich viele verschiedene digitale Anwendungen deutscher Bildungsmedienverlage nutzen lassen. Mit dieser Implementierung wird der Aufbau und die Anbindung eines Lizenzmanagers auf Basis von Univention Corporate Server (UCS) mit Single-Sign-On für das Angebot von bildungslogin.de ermöglicht.

UCS und die Erweiterung UCS@school stellen für Schulträger und Bildungsministerien schulische Infrastruktur vornehmlich als Identity and Accessmanagement (IAM) bereit. Die dort bereits vorhandenen Benutzerkonten sollen für die Nutzung von bildungslogin.de verwendet werden können, inkl. Zuweisung und Übertragung von Lizenzen, sodass zum einen eine doppelte Pflege entfällt und zum anderen Lehrkräfte und SuS direkt aus der schulischen IT-Infrastruktur heraus mit ihren gewohnten Zugangsdaten auch bildungslogin.de nutzen können.

Die Implementierung ist aktuell mit `UCS@school 4.4 v9` kompatibel.

## Abstimmung mit bildungslogin.de

Für den Betrieb des Plugins ist eine Abstimmung mit dem [Bildungslogin](https://www.bildungslogin.de/) notwendig. Sämtliche benötigten Parameter werden durch ein Onboarding erörtert.

## Voraussetzungen / Parameter

Das Modul muss intstalliert sein und SSO seitens extern funktionieren. Auch muss die UCS@School- API extern erreichbar sein. Hier eine Zusammenfassung:

# Installation

## Voraussetzungen

### 1. Single-Sign-On und Portal

- Für SSO wird der `OpenID Connect Provider` benötigt. Die Installation und Konfiguration ist im [UCS Handbuch](https://docs.software-univention.de/handbuch-4.4.html#domain:oidc) beschrieben.
- Für die gesicherte und verschlüsselte Datenübertragung kann [Let’s Encrypt aus dem App Center](https://www.univention.de/produkte/univention-app-center/app-katalog/letsencrypt/) verwendet werden.
- Ein Blick in den Hilfe-Artikel ist hilfreich, wenn das [Portal und SSO umkonfiguriert](https://help.univention.com/t/reconfigure-ucs-single-sign-on/16161) wird.

### 2. UCS@School- Komponenten installieren

1. Als erstes muss UCS@school installiert sein: Melden Sie sich an der UCS Management Konsole an, öffnen Sie den App Center und Installieren Sie die [UCS@school app](https://www.univention.de/produkte/univention-app-center/app-katalog/ucsschool/).
2. Anschließend muss die UCS@school APIs app installiert werden. Dies können Sie auf der Kommandozeile mit root- Berechtigungen wie folgt erledigen:
 `univention-app install ucsschool-apis=0.1.0` oder `univention-app install ucsschool-apis=0.1.0 --username <GUI-Admin-Benutzername>`**Achtung:** Aufgrund interner Abhängigkeiten ist es aktuell notwendig, dass die Version 0.1.0, und nicht die aktuellste Version installiert wird!

Überprüfen Sie dass alle Skripte erfolgreich durchlaufen wurden: GUI-> Domain -> Domain join: alle erfolgreich?
## Lizenzmanagermodul- Installation

### 1. Pakete installieren

Zur Konfiguration des UDM REST API Clients wird eine Java Runtime in den Docker Container installiert. Dafür muss dieser auf den deutschen Debian Mirror zugreifen. Ausgehende HTTP-Verbindungen - zumindest zur IP `141.76.2.4` (`ftp.de.debian.org`) - müssen dafür während der Installation erlaubt sein.

**ACHTUNG**: auf Primary und Backup nodes (DC Master und DC Backup) installiert das Joinscript `68udm-bildungslogin.inst` des Pakets `udm-bildungslogin` LDAP-Indices. Dafür wird der LDAP Server temporär angehalten. Bei großen Installationen kann dies eine Weile dauern.

Zur Installation führen Sie folgende Schritte aus:
- Einrichten des Repositories (Details erhalten Sie beim Onboarding)
- `apt install bildungslogin-plugin python-bildungslogin udm-bildungslogin ucs-school-umc-licenses` 

Beschreibung der Pakete:
- `python-bildungslogin` (Programmbibliothek und CLI Lizenzimport)
- `udm-bildungslogin` (UDM Module)
- `ucs-school-umc-licenses` (UMC Modul)
- `bildungslogin-plugin` (Provisionierungs REST API Plugin für die `ucsschool-apis` App.)

Ebenso ist ein API- Benutzer mit der ID **bildungslogin-api-user** eingerichtet.

## Verifizierung der Installation

### 1. Prüfen des `memberOf` overlays

Die UMC-Module setzen das LDAP-overlay `memberOf` voraus.
Ob das LDAP-overlay aktiviert ist lässt sich über die Systemdiagnose oder `ucr get ldap/overlay/memberof` prüfen.
Sollte es nicht aktiviert sein, sind die nötigen Schritte, zur Aktivierung, in folgendem Artikel beschrieben: [memberOf attribute: Group memberships of user and computer objects](https://help.univention.com/t/memberof-attribute-group-memberships-of-user-and-computer-objects/6439)

### 2. Einstellung der `sizelimit` UCR Variable

Einige der neuen UMC Module nutzen ein Limit um zu bestimmen, wie viele Ergebnisse sie maximal anzeigen, bevor sie eine
Einschränkung durch Suchparameter verlangen. Dieses Limit kann durch die UCR Variable `directory/manager/web/sizelimit`
gesetzt werden und ist standardmäßig auf 2000 eingestellt. Aktuell enmpfiehlt es sich dieses Limit für das Lizenzmanagement
auf 500 zu setzen. Dies kann mit dem Befehl `ucr set directory/manager/web/sizelimit=500` erreicht werden.

## Installationsprobleme

Probleme bei der Installation können häufig durch das erneute Ausführen der Join Skripte behoben werden:

```bash
univention-run-join-scripts --run-scripts --force 68udm-bildungslogin.inst
univention-run-join-scripts --run-scripts --force 69bildungslogin-plugin-openapi-client.inst
univention-run-join-scripts --run-scripts --force 70bildungslogin-plugin.inst
```

## Konfiguration

Wenn alles erfolgreich konfiguriert wurde, sind die beiden Joinskripte `69bildungslogin-plugin-openapi-client.inst` und `70bildungslogin-plugin.inst` ohne Fehler durchgelaufen (siehe Logfile: `/var/log/univention/join.log`).

### 1. Setup der Provisioning API

Zur Verwendung der Provisioning API ist beim Installationsprozess bereits ein Benutzer erstellt worden. Dieser muss nun noch aktiviert, und ein Passwort gesetzt werden.

Der Nutzer inkl. Passwort muss dann dem BILDUNGSLOGIN mitgeteilt werden, damit dieser die API abfragen kann:

```bash
udm users/user modify \
  --dn "uid=bildungslogin-api-user,cn=users,$(ucr get ldap/base)" \
  --set disabled=0 \
  --set password="<geheimes passwort hier einsetzen>"
```

### 2. Anbindungsdetails zum BILDUNGSLOGIN konfigurieren
Die Datei /etc/bildungslogin/config.ini enthält notwendige Daten, um sich mit dem BILDUNGSLOGIN zu verbinden. Sie erhalten diese beim Onboarding:

**Auth**
- **clientId**: ID für den Bezug von AccessTokens zur Nutzung der Bildungslogin-API, für `  `.
- **clientSecret**: Secret für den Bezug von AccessTokens zur Nutzung der Bildungslogin-API.
- **Scope**: Verwendetes Scope für die Anbindung

**APIEndpoint**
- **AuthServer**: Der Authentifizierungsserver des BILDUNGSLOGINs, welcher Token ausstellt
- **ResourceServer**:  Der API- Endpunkt des BILDUNGSLOGIN, um einen Lizenz- bzw. Medienabruf durchzuführen

### 3. Portal-Eintrag hinzufügen

Auf der Portalseite wird eine Kachel mit den folgenden Werten eingerichtet, um direkt vom UCS@School- System auf das Medienregal zugreifen zu können. Den Wert von <idp_name> erhalten Sie zusammen mit den Anbindungsdetails (2.) beim Onboarding. Details siehe auch [UCS Handbuch](https://docs.software-univention.de/handbuch-4.4.html#central:portal).

**Relevante Konfiguration:**
- Logo: 
- Link (Test): https://www.bildungslogin-test.de/app/#/sso/bilob?idp_hint=<idp_name>
- Link (Produktion): https://www.bildungslogin.de/app/#/sso/bilob?idp_hint=<idp_name>

Den **idp_name** erhalten Sie vom Bildungslogin beim Onboarding.

# Benutzung 

## Univention Management Console

In der UMC werden drei neue Module unter `Unterricht` angezeigt

- **Lizensierte Medien** LizensierteMedien im BILDUNGSLOGIN-Lizenzmanager anzeigen und durchsuchen
- **Medienlizenz- Übersicht** 
Medien-Lizenzen im BILDUNGSLOGIN-Lizenzmanager anzeigen, suchen, entziehen
- **Medienlizenzen zuweisen** 
Medien-Lizenzen im BILDUNGSLOGIN-Lizenzmanager zuweisen
- **Medienlizenzen importieren** Medien-Lizenzen in den BILDUNGSLOGIN-Lizenzmanager importieren
- **Klassenlisten** Generieren von Listen für Klassen und Arbeitsgruppen

## Univention Directory Manager
Über das bildungslogin-udm- Modul können u.a. die untenstehenden Vorgänge auf der Kommandozeile vorgenommen werden. Eine Auflistung sämtlicher Kommandos der Methoden des "bildungslogin"- UDM-Moduls findet man mit dem Help- Befehl, also:
- `udm bildungslogin/assignments help`
- `udm bildungslogin/license help`
- `udm bildungslogin/metadata help`

Beispiele:
- Lizenzen importieren: `bildungslogin-license-import --license-file ./sample_license.json --school "DEMOSCHOOL"`
- Auflisten aller Lizenzen: `udm bildungslogin/license list`
- Auflisten der Lizenzen mit einem bestimmten Lizenzcode: `udm bildungslogin/license list --filter code=CCB-DEMO-CODE-0000`
- Löschen einer spezifischen Lizenz (benötigt die DN): `udm bildungslogin/license remove --dn <DN Der Lizenz, z.B. vom obigen Abruf>`
- Anzeige aller zugewiesenen Lizenzen: `udm bildungslogin/assignment list --filter status=ASSIGNED`

## Bekannte Einschränkungen und Probleme

**Die Konfiguration enthält Zugänge für die Testumgebung**

Problemumgehung: Die Datei `/etc/bildungslogin/config.ini` muss für den Produktivbetrieb angepasst werden. Einzelheiten erhalten Sie beim Onboarding:

**Der Cronjob zum Medien-Abruf ergibt einen Fehler `ValueError: No JSON object could be decoded`**

Problemumgehung: Die für initiale Tests enthaltenen Dummy-Codes werden keine Mediendaten bereitgestellt. Nach dem Einspielen von richtigen Codes wird der Fehler behoben sein.

**Der Single-Sign-On Login läuft ab und die UMC ist in einer Ladeschleife**

Problemumgehung: Das klingt nach dem bekannten [Bug 52888](https://forge.univention.org/bugzilla/show_bug.cgi?id=52888). Als Lösung bitte die erlaubte Zeitdifferenz der SAML Gültigkeit bei der Authentifizierung auf 12 Stunden setzen, wodurch der Login an einem Arbeitstag nicht mehr vorzeitig abläuft.

```bash
ucr set umc/saml/grace_time=43200
```

## Performance
Wenn Sie eine große Anzahl von Lizenzen importieren (mehrere Tausend) kann der Importvorgang mehrere Minuten dauern.

## Logging
- UDM- Modul- Log: `/var/log/univention/management-console-module-licenses.log`
- UCSSchools-API- Log (nicht exklusiv): `/var/log/univention/ucsschool-apis/http.log`
- Log des Medienupdates: `/var/log/univention/bildungslogin-media-update.log`

## APIs
Für den Abruf der Lizenzzuweisungen muss die API des Moduls für den BiLo- Broker erreichbar sein.

**Basis- URL des UCS- Systems**
- `https://<FQDN des Schulservers>/ucsschool/apis/`

**Eingehende Aufrufe**
- POST: `auth/token`
- GET: `bildungslogin/v1/user/`

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
