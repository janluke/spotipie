"""
Modified from
https://requests-oauthlib.readthedocs.io/en/latest/examples/real_world_example_with_refresh.html
"""
import webbrowser
from pprint import pformat

from flask import (
    Flask,
    redirect,
    request,
    session,
    url_for
)
from flask.json import jsonify
from spotipie import (
    AuthorizationCodeSession,
    Credentials,
    Spotify
)

app = Flask(__name__)

client_id, client_secret, redirect_uri = Credentials.from_environment()
scope = ['user-library-read']


def get_spotify_session(state=None, token=None, **kwargs):
    return AuthorizationCodeSession(
        client_id, client_secret, redirect_uri,
        scope=scope, state=state, token=token, **kwargs)


def get_spotify_api_client(token) -> Spotify:
    return Spotify(get_spotify_session(token=token))


@app.route("/")
def demo():
    """Step 1: User Authorization.

    Redirect the user/resource owner to the OAuth provider (i.e. Google)
    using an URL with a few key OAuth parameters.
    """
    oauth2_session = get_spotify_session()
    authorization_url, state = oauth2_session.authorization_url()

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state
    return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.
@app.route("/callback", methods=["GET"])
def callback():
    """ Step 3: Retrieving an access token.

    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """
    oauth2_session = get_spotify_session(state=session['oauth_state'])
    token = oauth2_session.fetch_token(request.url).to_dict()

    # We use the session as a simple DB for this example.
    session['spotify_token'] = token

    return redirect(url_for('.menu'))


@app.route("/menu", methods=["GET"])
def menu():
    """"""
    return """
    <h1>Congratulations, you have obtained an OAuth 2 token!</h1>
    <h2>What would you like to do next?</h2>
    <ul>
        <li><a href="/profile"> Get account profile</a></li>
        <li><a href="/user-tracks"> Get user's favorite tracks</a></li>
    </ul>

    <pre>
    %s
    </pre>
    """ % pformat(session['spotify_token'], indent=4)


@app.route("/profile", methods=["GET"])
def profile():
    """Fetching a protected resource using an OAuth 2 token.
    """
    spotify = get_spotify_api_client(session['spotify_token'])
    return jsonify(spotify.current_user())


@app.route("/user-tracks", methods=["GET"])
def user_tracks():
    spotify = get_spotify_api_client(session['spotify_token'])
    return jsonify(spotify.user_saved_tracks())


if __name__ == "__main__":
    import os

    # This allows us to use a plain HTTP callback
    # DON'T USE THIS IN PRODUCTION
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"

    app.secret_key = os.urandom(24)
    webbrowser.open('http://localhost:1234/')
    app.run(debug=True, port=1234)
