**Riedel, 06.05.2021** 
initiale Version

**Riedel, 01.06.2021** 
* Variationen aus der Medien-Definition entfernt ([schemas/media.schema.json](schemas/media.schema.json))
* Erweiterung um Abfrage nach Zeitstempel (Resource `/media/feed`)
* Anpassung Resourcenpfad für Media-Queries
* Vereinheitlichung diverser Bezeichner

**Riedel, 08.06.2021** 
* Ergebnis-Typ für Feed-Request geändert (Rückgabe der Medien-IDs anstelle der kompletten Mediendaten, siehe [schemas/mediafeed-result.schema.json](schemas/mediafeed-result.schema.json))
* Authentifizierung von BASIC auf OAuth client tokens geändert