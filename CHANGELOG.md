# Changelog

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
- Das UMC-Modul ***Lizenzierte Medien*** ist nicht nicht abgeschlossen.
  - Die Detailansicht für Medien enthält noch Platzhalterdaten.
- Das UMC-Modul ***Medienlizenzen zuweisen*** ist nicht nicht abgeschlossen.
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
