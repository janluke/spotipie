"""
A Web app to run in localhost to obtain a token either using the authorization code flow or the
implicit grant flow. This app was designed to be called in a secondary thread or process by the main
application. It returns the obtained token through a message queue.

The simplest way to implement this app was to just open the "authorization URL" and return the
callback URL to the main app. But I like to complicate things. So, for the only purpose to greet the
user with its own username (e.g. "Hello, MusicLover67!"), this app creates its own OAuth2 session
and Spotify client.
"""
import logging
import secrets
from queue import Queue
from typing import Optional

from flask import Flask, redirect, render_template, request, session, url_for

from spotipie.auth import AuthorizationCodeSession, ImplicitGrantSession
from spotipie.auth.sessions import Flow
from spotipie.client import Spotify
from spotipie.utils import pretty

logger = logging.getLogger(__name__)

app = Flask(__name__)


def start_authorization_app(port: int, message_queue: Queue,
                            client_id: str, client_secret: Optional[str] = None,
                            scope: str = None,
                            client_app_name: Optional[str] = None,
                            test: bool = False, **kwargs):
    """

    Args:
        port:
        message_queue:
            the queue the app will use to output
        client_id:
        client_secret:
        scope:
        client_app_name:
        test:
        **kwargs:

    Returns:

    """
    app.port = port
    app.secret_key = secrets.token_bytes(32)   # HTTPS
    app.client_app_name = client_app_name
    app.message_queue = (message_queue or Queue()) if test else message_queue
    app.redirect_uri = 'http://localhost:%d/callback' % port

    if client_secret:
        app.flow = Flow.AUTHORIZATION_CODE
        app.oauth2 = AuthorizationCodeSession(client_id, client_secret, app.redirect_uri, scope)
    else:
        app.flow = Flow.IMPLICIT_GRANT
        app.oauth2 = ImplicitGrantSession(client_id, app.redirect_uri, scope)

    app.spotify = Spotify(app.oauth2)

    app.run('localhost', port=port, use_reloader=test, **kwargs)
    logger.debug('App stopped!')


def _shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.route('/authorize')
def authorize():
    session.clear()
    auth_url, state = app.oauth2.authorization_url()
    return redirect(auth_url)


@app.route('/callback')
def callback():
    if app.flow == Flow.AUTHORIZATION_CODE:
        return redirect(url_for('handle_response', **request.args))
    else:
        # implicit grant case: the access-token is in the fragment part of the url (which is not
        # sent to the server); javascript will do the redirect including the arguments in the
        # fragment as query argument
        return render_template('callback.html', redirect_url=url_for('handle_response'))


@app.route('/handle-response')
def handle_response():
    oauth2 = app.oauth2
    message_queue = app.message_queue

    args = request.args
    logger.debug('Callback args: ' + pretty(args))

    if 'error' in args:
        message_queue.put(dict(error=args['error']))
        error = args['error']
        if error == 'access_denied':
            return render_template('access_denied.html', app_name=app.client_app_name)
        return render_template('error.html', error=error)

    # Reconstruct the callback url replacing http with https
    # (oauth2.fetch_token() doesn't like http)
    sep = '?' if app.flow == Flow.AUTHORIZATION_CODE else '#'
    callback_url = ('https://localhost:{port}/callback{sep}{args}'.format(
        port=app.port, sep=sep, args=request.query_string.decode('utf-8')))

    logger.debug('Reconstructed callback URL: ' + callback_url)

    try:
        if app.flow == Flow.AUTHORIZATION_CODE:
            token = oauth2.fetch_token(callback_url).to_dict()
        else:
            token = oauth2.read_token_from_callback_url(callback_url).to_dict()

        logger.debug('Token: ' + pretty(token))

        app.spotify.current_user()  # check everything works
    except Exception as exc:
        message_queue.put(dict(error=str(exc), callback_url=callback_url))
        return render_template('error.html', error=str(exc))

    session['token'] = token
    message_queue.put(token)
    return redirect('success')


@app.route('/success')
def success():
    if 'token' in session:
        try:
            user = app.spotify.current_user()
            return render_template('success.html', user=user, app_name=app.client_app_name)
        except Exception as exc:
            return render_template('error.html', header='Unexpected error', error=str(exc))

    return render_template('error.html',
                           error='(access forbidden) You have not granted any authorization yet!')


@app.route('/shutdown', methods=['POST'])
def shutdown():
    _shutdown_server()
    return 'Shutdown'


if __name__ == '__main__':
    from queue import Queue
    from spotipie.auth import Credentials

    logging.basicConfig(level=logging.DEBUG)

    client_id, client_secret, _ = Credentials.from_environment()
    start_authorization_app(port=1234, message_queue=Queue(),
                            scope='user-library-read', client_id=client_id,
                            client_secret=client_secret, client_app_name='SpotiTube',
                            debug=True, test=True)
