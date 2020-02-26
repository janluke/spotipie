from spotipie import (
    Credentials,
    Spotify,
    ClientCredentialsSession
)

# Load OAuth2 credentials from environment variables:
# {prefix}_CLIENT_ID, {prefix}_CLIENT_SECRET, {prefix}_REDIRECT_URI,
# The default prefix is SPOTIPIE.
client_id, client_secret, redirect_uri = Credentials.from_environment(prefix='SPOTIFY')

# Create a session and fetch a token
session = ClientCredentialsSession(client_id, client_secret, redirect_uri)
session.fetch_token()

# Wrap the session
spotify = Spotify(session)

# Use the client
print(spotify.track('3Fcfwhm8oRrBvBZ8KGhtea'))
