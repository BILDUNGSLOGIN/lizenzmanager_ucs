# Changelog

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
