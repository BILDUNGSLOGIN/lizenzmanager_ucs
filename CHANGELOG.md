# Changelog

## 2021-09-28

## Hinzugefügt
- Die automatische Suche für das UMC Modul ***Medienlizenz-Übersicht*** und die Nutzerauswahl bei der Zuweisung
von Lizenzen wurde abgeschaltet.
- Das UMC Modul ***Medienlizenz-Übersicht*** berücksichtigt nun die UCR Variable `directory/manager/web/sizelimit`
und erfordert eine Präzisierung der Suchparameter, wenn die Suchergebnisse das Limit übersteigen.

## Geändert
- Das Suchfeld *Klasse* beim Zuweisen von Lizenzen fällt auf die Auswahl *Alle Klassen* zurück, wenn ein leerer
String als Wert eingegeben wird.
- Diverse Text- und Übersetzungsänderungen in den UMC Modulen
- Die Reihenfolge der UMC Module wurde angepasst

## 2021-08-27

## Hinzugefügt
- Validierung der Medienmetadaten.
- Validierung der Lizenzdaten.

### Geändert
- Die Anzeige im UMC-Modul ***Medienlizenzen anzeigen*** wurde beschleunigt.
- In LDAP-Attributen und UDM-Modulen wurde `vbm` zu `bildungslogin` umbenannt.
- Über das UMC-Modul ***Medienlizenzen zuweisen*** lassen sich jetzt Lizenzen zuweisen.
- Die Detailansicht im UMC-Modul ***Lizenzierte Medien*** enthält jetzt Daten zu den Lizenzen, Medien und zugewiesenen Nutzern.
- Das Joinscript `39bildungslogin-plugin-openapi-client.inst` muss nicht mehr doppelt ausgeführt werden.
- Die Suche nach `Produkt ID`, `Lizenz Code` und `Schulen` ist jetzt case insensitive.
- Lizenzen ohne Laufzeitende erzeugen keinen Fehler mehr und werden nicht als verfallen angezeigt.
- Die Deinstallationsskripte wurden verbessert. Zur restlosen Entfernung aller Daten, wird eine Anleitung zur Verfügung gestellt.

### Anmerkung: Umbenennung `vbm` zu `bildungslogin`

Wenn ein bereits installiertes System aktualisiert werden soll, sind die Hinweise im [Getting started](getting_started.md) zu beachten.

Auf dem von uns zur Verfügung gestelltem System sind diese Schritte bereits durchgeführt.
Dort sind keine weiteren Schritte erforderlich.

## 2021-08-20

### Hinzugefügt
- Das Verlagskürzel wird automatisch dem Lizenzcode vorangestellt, sollte dieses Kürzel fehlen.
- Produktmetadaten werden automatisch, für neue Lizenzen, heruntergeladen.
- Produktmetadaten werden regelmässig auf Änderungen überprüft und bei Bedarf aktualisiert.
- Eine Python Bibliotheksfunktion für eine erweiterte Lizenzsuche im UMC-Modul.
- Eine Detailansicht für Lizenzen im UMC-Modul.

### Geändert
- Eine doppelte Endpunktbeschreibung wurde aus der Swagger UI entfernt.
- Ein Fehler in den LDAP-ACL wurde korrigiert, damit Schuladmins Lizenzen verwalten können.
- Die Typisierung von Werten der Lizenz-, Metadaten- und Assignment-Objekte wurde in den UDM-Modulen verbessert.

### Status GUI
- Das UMC-Modul ***Medienlizenzen anzeigen*** ist abgeschlossen und kann getestet werden.
  - Die Suche nach `Produkt ID` und `Lizenz Code` ist noch case sensitive.
- Das UMC-Modul ***Lizenzierte Medien*** ist noch nicht abgeschlossen.
  - Die Detailansicht für Medien enthält noch Platzhalterdaten.
- Das UMC-Modul ***Medienlizenzen zuweisen*** ist noch nicht abgeschlossen.
  - Die Übersichtsseite enthält noch Platzhalterdaten.
  - Es lassen sich noch keine Lizenzen zuweisen.

## 2021-08-13

### Hinzugefügt

- Python Bibliotheksfunktionen um die verfügbaren und verbrauchten Zuweisungen einer Lizenz zu bestimmen.
- Python Bibliotheksfunktionen um Lizenzzuweisungen zu bearbeiten.
- Ein UMC-Modul um lizenzierte Produkte anzuzeigen.

### Geändert

- LDAP-ACL für Lizenz-, Metadaten- und Assignment-Objekte, diese Objekte können nun nur noch von Primary-Systemen, Backup-Systemen und Administratoren aus der LDAP Datenbank gelesen werden.
- Die UMC-Module sind nun in der edukativen Kategorie der UMC, nicht mehr in der administrativen Kategorie.
- LDAP-Schemata wurden angepasst um "case-insensitive" Suchen zu ermöglichen.
- Nur absolute Pfade, für Buch-Cover, werden in den Metadaten gespeichert, sonst wird der Pfad durch einen leeren String ersetzt.

## 2021-08-06

### Hinzugefügt

- UDM-Module um Lizenz-, Metadaten- und Assignment-Objekte im LDAP zu speichern.
- Eine Python Bibliothek zum Lesen, Erstellen und Bearbeiten von  Lizenz-, Metadaten- und Assignment-Objekten.
- Eine API-Schnittstelle um die, einem Benutzer, zugewiesenen Lizenzen abzurufen.
- CLI Programme um Lizenzen und Metadaten zu importieren.
- Ein UMC-Modul um Lizenzen anzuzeigen.
