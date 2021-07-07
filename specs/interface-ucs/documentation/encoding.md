Als Zeichencodierung für alle übertragenen Zeichen wird grundsätzlich
__[UTF-8](https://tools.ietf.org/html/rfc3629)__
verwendet.

Übergebene Parameter (Teile der URL bei GET-Requests, Formular-Parameter bei POST)
werden gemäss (https://tools.ietf.org/html/rfc3986#section-2.1) codiert
("URL-encoding")

Soweit nicht anders definiert, wird als Datenaustauschformat __JSON__ (https://tools.ietf.org/html/rfc7159) verwendet.

Der im konkreten Fall angeforderte bzw. übergebene _Media Type_ wird über die
entsprechenden HTTP-Header signalisiert:

Beispiel:

    `Accept: application/vnd.de.bildungslogin.mediafeed+json`
