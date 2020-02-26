__all__ = ['SessionEvent', 'TokenExpiredEvent', 'TokenUpdatedEvent']

import abc
from typing import ClassVar

from attr import attrs

from spotipie.auth._token import OAuth2Token

if False:  # for mypy
    from .sessions import BaseOAuth2Session


class SessionEvent(abc.ABC):
    pass


# noinspection PyUnresolvedReferences
@attrs(frozen=True, auto_attribs=True)
class TokenExpiredEvent(SessionEvent):
    """
    Triggered when the request method is called but the token has expired. The token expiration time
    is checked before the actual request is made, so a listener to this event can be used to obtain
    a new token and set the token property of the session so that the request can be carried out
    without problems. This is handled automatically in refreshable sessions (client credentials and
    authorization code sessions) but not in the implicit grant session where you must catch this
    event to implement an "auto-refresh" feature.

    Attributes:
        session: "BaseOauth2Session"
        expired_token: OAuth2Token
        withhold_token: bool
            this is the value of the argument passed to the request method that can be used to
            prevent the session to refresh its token
    """
    name: ClassVar[str] = "token_expired"
    session: 'BaseOAuth2Session'
    expired_token: OAuth2Token
    withhold_token: bool


@attrs(frozen=True, auto_attribs=True)
class TokenUpdatedEvent(SessionEvent):
    """
    Triggered whenever the setter of the token property is called (even if the new token is equal to
    the old one). This event is guaranteed to be called when a session auto-refreshes its token, so
    you can listen to this event to save the new token somewhere if you want.

    Attributes
        session: "BaseOauth2Session"
        old_token: OAuth2Token
        new_token: OAuth2Token
    """
    name: ClassVar[str] = "token_updated"
    session: 'BaseOAuth2Session'
    old_token: OAuth2Token
    new_token: OAuth2Token
