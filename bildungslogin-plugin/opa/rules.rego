package bildungslogin_plugin

default user = false

user {
	actor.username == "bildungslogin-api-user"
}

# Helper to get the token payload.
token = {"payload": payload} {
	[header, payload, signature] := io.jwt.decode(input.token)
}
actor := token.payload.sub
