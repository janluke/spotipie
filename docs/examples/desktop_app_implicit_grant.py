from spotipie import (
    Credentials,
    Spotify,
    ImplicitGrantSession
)
from spotipie.auth import get_user_authorization
from spotipie.utils import get_default_http_adapter, pretty

# Load OAuth2 credentials from environment variables:
# {prefix}_CLIENT_ID, {prefix}_CLIENT_SECRET, {prefix}_REDIRECT_URI,
# The default prefix is SPOTIPIE.
client_id, _, redirect_uri = Credentials.from_environment(prefix='SPOTIFY')

# Create a session following the Authorization Code flow.
scope = ['user-library-read']  # adapt this to your requirements
session = ImplicitGrantSession(client_id, redirect_uri, scope=scope)

# [Optional] Mount an HTTPAdapter to implement retrying behavior and/or caching.
# You can use get_default_http_adapter() for a reasonable default
session.mount('https://', get_default_http_adapter())

# Authorize through the local flask app
# NOTE:
# - you need to install the optional dependency: ``pip install spotipie[auth-app]``
# - you need to whitelist ``http://localhost:{port}/callback`` in your Spotify App
get_user_authorization(session, app_name='YourAppName', port=1234)

# [ALTERNATIVE] If you installed spotipie without the optional authorization app
# from spotipie.auth import prompt_for_user_authorization
# prompt_for_user_authorization(session)

# Wrap the session
spotify = Spotify(session)

# Use the client
print(pretty(spotify.current_user()))
