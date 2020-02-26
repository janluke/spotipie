__all__ = ['get_user_authorization', 'prompt_for_user_authorization']

import logging
import time
import webbrowser
from queue import Empty, Queue
from threading import Thread
from typing import Optional, Union

import requests

from spotipie.auth import (
    AuthorizationCodeSession,
    Flow,
    ImplicitGrantSession,
    OAuth2Token
)
from spotipie.exceptions import (
    AccessDenied,
    AuthorizationException,
    AuthorizationTimeout
)
from spotipie.utils import pretty

UserOAuth2Session = Union[AuthorizationCodeSession, ImplicitGrantSession]
logger = logging.getLogger(__name__)


def _open_in_browser(url):
    try:
        webbrowser.open(url)
        print("Successfully opened the browser!")
    except Exception as exc:
        print("Couldn't open the web browser automatically: %s\n", str(exc))
        print("Please, open the following link in your browser: %s" % url)


def get_user_authorization(session: UserOAuth2Session,
                           app_name: Optional[str] = None,
                           port: int = 1234, timeout: int = 120) -> 'OAuth2Token':
    """
    Asks the user to authorize the authorize your app. The authorization flow depends
    on the type of session to pass. As a side effect, the obtained token is stored
    in the session.

    This function launches a flask app listening to ``http://localhost:{port}/callback``
    in a new thread, which once the authorization is completed, sends the received token
    to the main thread through a messaging queue; in this way, this function does not require
    the user to manually copy and paste the callback URL into your app.

    **IMPORTANT:** to use this function

    - you need to install optional dependencies through: ``pip install spotipie[auth-app]``
    - you need to whitelist ``http://localhost:{port}/callback`` in your app callback URLs.

    Args:
        session:
            OAuth2 session to authorize
        app_name:
            name of your application (used in the "success.html" page)
        port:
            TCP port the server listen to
        timeout:
            shutdown the server app after this time (in seconds)

    Returns:
        OAuth2Token

    See Also:

    """
    from spotipie.auth._app import start_authorization_app

    messaging_queue: Queue = Queue()
    app_url = 'http://localhost:%d' % port
    server_thread = Thread(
        target=start_authorization_app,
        daemon=True,
        kwargs=dict(
            port=port, message_queue=messaging_queue,
            scope=session.scope,
            client_id=session.client_id,
            client_secret=getattr(session, 'client_secret', None),
            client_app_name=app_name, debug=False)
    )
    server_thread.start()

    _open_in_browser(app_url + '/authorize')

    try:
        token = messaging_queue.get(block=True, timeout=timeout)
    except Empty:
        raise AuthorizationTimeout(timeout)
    finally:
        # delay the app shutdown a little bit so that it can reply to all the requests needed
        # to display a web page (html + css)
        time.sleep(1)
        requests.post(app_url + '/shutdown')
        server_thread.join()

    logger.debug('Token: ' + pretty(token))

    if 'error' in token:
        if token['error'] == 'access_denied':
            raise AccessDenied
        raise AuthorizationException('Error during app authorization: ' + token['error'])

    session.token = token
    return session.token


def prompt_for_user_authorization(session: UserOAuth2Session) -> 'OAuth2Token':
    """
    Useful for command-line apps, when you don't want to use :func:`get_user_authorization`.
    Asks the user to authorize your app through the terminal. It requires the user to
    manually copy and paste the callback URL into the terminal.
    """
    auth_url, _ = session.authorization_url()
    print(f"""
    We need your authorization to continue. The authorization uses the OAuth2
    protocol. We are going to open the Spotify authorization page in your browser:

    {auth_url}

    Once you authorize your app, Spotify will redirect you to localhost and
    the redirection URL will contain the authorization token. You need to copy
    that URL and paste it here.
    """)
    input('Press Enter to continue...')
    _open_in_browser(auth_url)
    callback_url = input('Copy the callback URL here: ')
    if callback_url.startswith('http:'):
        callback_url = 'https' + callback_url[4:]
    if session.FLOW == Flow.AUTHORIZATION_CODE:
        token = session.fetch_token(callback_url)
    else:
        token = session.read_token_from_callback_url(callback_url)

    logger.debug('Token: ' + pretty(token))
    return token


if __name__ == '__main__':
    from spotipie.auth import AuthorizationCodeSession, Credentials

    credentials = Credentials.from_environment()
    session = AuthorizationCodeSession(*credentials, scope='user-library-read')
    # token = prompt_for_user_authorization(session)
    token = get_user_authorization(session, 'PippoApp')
    print('Token:', token)
