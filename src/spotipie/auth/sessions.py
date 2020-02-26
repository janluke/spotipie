"""
This module contains a ``Session`` class for each OAuth2 flow.
These classes are wrappers for a :class:`requests_oauthlib.OAuth2Session`.

The hierarchy of the session classes is the following:

- :class:`BaseOAuth2Session`
    - :class:`ImplicitGrantSession`
    - :class:`RefreshableOAuth2Session`
        - :class:`ClientCredentialsSession`
        - :class:`AuthorizationCodeSession`

``ClientCredentialsSession`` and ``AuthorizationCodeSession`` are refreshable sessions, meaning that
once the access token expires, a new one can be obtained automatically.
So, if you make a request and your token is expired, a new token is automatically obtained
and the request is carried out without problems.

On the other hand, an ``ImplicitGrantSession`` is not "refreshable", at least not in the same sense.
When the token expires, the authorization URL must be opened in the browser. Despite that, the user
should not need to type anything since the app was already authorized.
Still, an interaction with the browser is needed: the new token cannot be obtained totally "behind
the scene" (in Python) as in the case of the other two flows. That's why ``ImplicitGrantSession``
has not the auto-refresh feature. Nonetheless, you can still register a listener to the
"token_expired" event to handle that.
"""
__all__ = [
    'BaseOAuth2Session', 'RefreshableOAuth2Session', 'AuthorizationCodeSession',
    'ImplicitGrantSession', 'ClientCredentialsSession'
]

import abc
import logging
import os
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlparse

import requests
from attr import attrs
from oauthlib.oauth2 import BackendApplicationClient, MobileApplicationClient
from requests_oauthlib import OAuth2Session

from spotipie.auth._token import OAuth2Token, TokenType
from spotipie.auth.events import (
    SessionEvent,
    TokenExpiredEvent,
    TokenUpdatedEvent
)
from spotipie.exceptions import AccessDenied, AuthorizationException
from spotipie.utils import normalize_scope

logger = logging.getLogger(__name__)

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
REFRESH_URL = TOKEN_URL

Callback = Callable[[SessionEvent], Any]


@attrs(frozen=True, auto_attribs=True)
class Credentials:
    client_id: str
    client_secret: Optional[str]
    redirect_uri: str

    @staticmethod
    def from_environment(prefix: str = 'SPOTIPIE') -> 'Credentials':
        """
        Reads Spotify OAuth2 credentials from the following environment variables:
        ``{prefix}_CLIENT_ID, {prefix}_CLIENT_SECRET, {prefix}_REDIRECT_URI``.

        Raises:
            ``KeyError``: if no variable is defined for ``client_id`` and ``redirect_uri``.
        """
        return Credentials(os.environ[prefix + '_CLIENT_ID'],
                           os.getenv(prefix + '_CLIENT_SECRET'),
                           os.environ[prefix + '_REDIRECT_URI'])

    def __iter__(self):
        yield self.client_id
        if self.client_secret:
            yield self.client_secret
        yield self.redirect_uri


class Flow(Enum):
    CLIENT_CREDENTIALS = 'client_credentials'
    IMPLICIT_GRANT = 'implicit_grant'
    AUTHORIZATION_CODE = 'authorization_code'


class BaseOAuth2Session(abc.ABC):
    """
    Base class for all session classes. Please, note that this class is not a subclass of
    :class:`requests.Session`. In fact, it is a wrapper of :class:`requests_oauthlib.OAuth2Session`
    which is a subclass of :class:`requests.Session`. You can access the actual session object
    using the property `session`.

    Properties:
        session (:class:`requests_oauthlib.OAuth2Session`): (get-only) session object
        token (OAuth2Token): (get/set) token object
        client_id (str): (get-only)
        scope (FrozenSet[str]): (get-only)
    """
    FLOW: Flow

    def __init__(self, session: OAuth2Session):
        self._session = session
        self._token = None
        self._listeners: Dict[str, List[Callback]] = dict(token_updated=[], token_expired=[])

    def add_listener(self, event_name: str, listener: Callback) -> None:
        """
        Adds a listener for one of the available events (see :mod:`~spotipie.auth.events`).

        Args:
            event_name (str): either "token_updated" or "token_expired"
            listener: a callable taking an event object in input
        """
        self._listeners[event_name].append(listener)

    def remove_listener(self, event_name: str, listener: Callback) -> None:
        self._listeners[event_name].remove(listener)

    def _notify_listeners(self, event: SessionEvent):
        for listener in self._listeners[event.name]:
            listener(event)

    @property
    def session(self) -> requests.Session:
        """
        Returns the :class:`requests_oauthlib.OAuth2Session` instance wrapped by this object.
        You should not need to use this. If you do, makes sure your use doesn't interfere with
        the behavior of the wrapper.
        """
        return self._session

    @property
    def client_id(self):
        return self._session.client_id

    @property
    def is_authorized(self):
        return self._session.authorized

    @property
    def token(self) -> OAuth2Token:
        return self._token

    @token.setter
    def token(self, token: TokenType):
        self.set_token(token)

    def set_token(self, token: TokenType):
        """
        Args:
            token: a OAuth2Token or an equivalent dictionary
        """
        old_token = self.token

        if isinstance(token, dict):
            if 'scope' not in token:
                self._session.token = token
                self._token = OAuth2Token(scope=self.scope, **token)
            else:
                self._token = OAuth2Token(**token)
                del token['scope']
                self._session.token = token

        elif isinstance(token, OAuth2Token):
            self._token = token
            token_dict = token.to_dict()
            del token_dict['scope']
            self._session.token = token_dict

        else:
            raise TypeError('token must either be a dict or an OAuth2Token')

        self._notify_listeners(TokenUpdatedEvent(self, old_token, self.token))

    @property
    def scope(self) -> Tuple[str]:
        if self.token:
            return self.token.scope
        return normalize_scope(self._session.scope)

    def request(self, method, url, params=None, data=None, headers=None,
                withhold_token=False, **kwargs):
        """
        Make a request. See :class:`requests.Session` documentation for the full argument list.

        Raises:
            TokenExpired: if the token is expired and not refreshed/updated automatically or by a
                          listener on the "token_expired" event.
        """
        if self.token and self.token.is_expired():
            self._notify_listeners(TokenExpiredEvent(self, self.token, withhold_token))

        return self._session.request(method=method, url=url, data=data, headers=headers,
                                     params=params, withhold_token=withhold_token, **kwargs)

    def mount(self, prefix, adapter):
        self._session.mount(prefix, adapter)


class RefreshableOAuth2Session(BaseOAuth2Session, abc.ABC):
    """
    Base abstract class for sessions whose token can be refreshed automatically either
    using a refresh-token (authorization code flow) or not (client credentials flow).
    """

    def __init__(self, session, client_secret, auto_refresh):
        super().__init__(session)
        self._client_secret = client_secret
        self._auto_refresh = None
        self.auto_refresh = auto_refresh

    @property
    def client_secret(self) -> str:
        return self._client_secret

    @property
    def auto_refresh(self) -> bool:
        return self._auto_refresh

    @auto_refresh.setter
    def auto_refresh(self, value: bool) -> None:
        """ Enable/disable token auto-refresh """
        if value is True:
            self.enable_auto_refresh()
        elif value is False:
            self.disable_auto_refresh()
        else:
            raise TypeError('auto_refresh must be a boolean')

    def enable_auto_refresh(self) -> None:
        """ Enable token auto-refresh. Equivalent to ``session.auto_refresh = True``. """
        # Oauth2Session uses auto_refresh_url as a "flag" for enabling auto-refresh
        self._session.auto_refresh_url = REFRESH_URL
        self._session.auto_refresh_kwargs = {'client_id': self.client_id,
                                             'client_secret': self.client_secret}
        self._auto_refresh = True

    def disable_auto_refresh(self) -> None:
        """ Disable token auto-refresh. Equivalent to ``session.auto_refresh = False``. """
        self._session.auto_refresh_url = None
        self._auto_refresh = False

    @abc.abstractmethod
    def _refresh_token(self) -> Dict:
        pass

    def refresh_token(self) -> OAuth2Token:
        """ Obtains a new token, stores it in the session and returns it. """
        logger.debug('Obtaining a new token')
        self.set_token(self._refresh_token())
        logger.debug('New token: %s' % self.token)

    def request(self, method, url, params=None, data=None, headers=None,
                withhold_token=False, **kwargs):

        if self.token and self.token.is_expired():
            self._notify_listeners(TokenExpiredEvent(self, self.token, withhold_token))
            if self.auto_refresh and not withhold_token:
                self.refresh_token()

        return self._session.request(method=method, url=url, data=data, headers=headers,
                                     withhold_token=withhold_token, params=params, **kwargs)


class ClientCredentialsSession(RefreshableOAuth2Session):
    FLOW = Flow.CLIENT_CREDENTIALS

    def __init__(self, client_id, client_secret, auto_refresh=True, **kwargs):
        session = OAuth2Session(client=BackendApplicationClient(client_id=client_id), **kwargs)
        super().__init__(session, client_secret, auto_refresh)

    def fetch_token(self, timeout=None):
        token = self._session.fetch_token(TOKEN_URL, client_secret=self._client_secret,
                                          timeout=timeout)
        self.set_token(token)
        return self.token

    def _refresh_token(self, timeout=None):
        return self.fetch_token(timeout=timeout)


class AuthorizationCodeSession(RefreshableOAuth2Session):
    """ Session for authorization code flow """
    FLOW = Flow.AUTHORIZATION_CODE

    def __init__(self, client_id, client_secret, redirect_uri, scope=None,
                 auto_refresh=True, **kwargs):
        session = OAuth2Session(
            client_id=client_id, redirect_uri=redirect_uri, scope=scope, **kwargs
        )
        super().__init__(session, client_secret, auto_refresh)

    def authorization_url(self, force_dialog=False, **kwargs) -> Tuple[str, str]:
        """
        Generates the URL the user has to visit in order to authorize (the application using) this
        session. The "state" parameter (useful for security reasons) is automatically generated and
        included in the URL. This function returns the authorization url and the generated state.

        Args:
            force_dialog (bool):
                Whether or not to force the user to approve the app again if they've already done
                so. If false (default), a user who has already approved the application may be
                automatically redirected to the URI specified by redirect_uri. If True, the user
                will not be automatically redirected and will have to approve the app again.

            **kwargs:
                other query arguments to include in the authorization URLs; at the moment of
                writing this functions, no other parameter exists.

        Returns:
            tuple(authorization_url, state)
        """
        return self._session.authorization_url(AUTH_URL, show_dialog=force_dialog, **kwargs)

    def fetch_token(self, callback_url, timeout=None):
        """
        Extracts the ``code`` and the ``state`` parameters from the callback URL and, after having
        checked the correctness of the ``state``, it makes a request to Spotify in order to exchange
        the authorization code for an access token.

        Args:
            callback_url:
                the URL Spotify redirects to after the user grants his authorization to your app,
                i.e. the redirect URI with query arguments "code" and "state" (at least).
                The function raises an exception if the callback URL contains an "error" argument

            timeout:

        Raises:
            ``AccessDenied``: if the user decides to not grant access
            ``AuthorizationException``: the callback_url has an ``error`` argument different from
                                        "access_denied"
            :exc:`requests.Timeout`
        """
        url = urlparse(callback_url)
        params = parse_qsl(url.query)
        if 'error' in params:
            if params['error'] == 'access_denied':
                raise AccessDenied
            raise AuthorizationException(params['error'])

        token = self._session.fetch_token(TOKEN_URL, authorization_response=callback_url,
                                          client_secret=self.client_secret,
                                          timeout=timeout)
        self.set_token(token)
        return self.token

    def fetch_token_given_code(self, code, state, timeout=None):
        """
        Variant of :meth:`fetch_token` where you pass the code and state parameters directly
        rather than a callback URL.
        """
        token = self._session.fetch_token(TOKEN_URL, code=code, state=state,
                                          client_secret=self.client_secret,
                                          timeout=timeout)
        self.set_token(token)
        return self.token

    def _refresh_token(self, timeout=None):
        return self._session.refresh_token(TOKEN_URL, timeout=timeout)


class ImplicitGrantSession(BaseOAuth2Session):
    """ Session following the "implicit grant flow" for authorization """
    FLOW = Flow.IMPLICIT_GRANT

    def __init__(self, client_id, redirect_uri, scope=None, **kwargs):
        session = OAuth2Session(
            client=MobileApplicationClient(client_id=client_id),
            redirect_uri=redirect_uri,
            scope=scope, **kwargs
        )
        super().__init__(session)

    def authorization_url(self, force_dialog=False, **kwargs) -> Tuple[str, str]:
        """
        Generates the URL the user has to visit in order to authorize (the application using) this
        session. The "state" parameter (useful for security reasons) is automatically generated and
        included in the URL. This function returns the authorization url and the generated state.

        Args:
            force_dialog (bool):
                Whether or not to force the user to approve the app again if they've already done
                so. If false (default), a user who has already approved the application may be
                automatically redirected to the URI specified by redirect_uri. If True, the user
                will not be automatically redirected and will have to approve the app again.

            **kwargs:
                other query arguments to include in the authorization URLs; at the moment of
                writing this functions, no other parameter exists.

        Returns:
            tuple(authorization_url, state)
        """
        return self._session.authorization_url(AUTH_URL, show_dialog=force_dialog, **kwargs)

    def read_token_from_callback_url(self, callback_url) -> OAuth2Token:
        """
        Parses the callback URL and grab the token information contained in the fragment of the URL.
        Sets the ``token`` property and returns the token.
        """
        token = self._session.token_from_fragment(authorization_response=callback_url)
        self.set_token(token)
        return self.token
