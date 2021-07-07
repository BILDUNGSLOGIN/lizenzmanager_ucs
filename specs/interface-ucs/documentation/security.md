Der Datenaustausch erfolgt ausschließlich über HTTP und
**[Transport Layer Security (TLS) Protocol Version 1.2](https://tools.ietf.org/html/rfc5246)** oder höher.
Damit ist implizit eine Authentifizierung des _providers_ gegenüber dem _consumer_ gegeben.

Eine Authentifizierung des Consumers gegenüber dem Provider erfolgt mit einem 
OAuth2 Cient AccessToken (ohne Nutzerbezug). 
Ein Token ohne Nutzerbezung kann unter Verwendung der _client credentials_ erzeugt werden. 
Der Prozess dazu ist unter [IBS Client AccessToken](https://confluence.t-systems-mms.eu/display/bilo/IBS+Client+AccessToken) beshrieben.