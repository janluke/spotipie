__all__ = [
    'pretty', 'get_default_http_adapter', 'ResourceInfo', 'normalize_scope',
    'format_uri', 'format_url', 'RESOURCE_TYPES',
]

import pprint
from typing import Iterable, Tuple

import urllib3
from attr import attrib, attrs
from cachecontrol import CacheControlAdapter

from spotipie.exceptions import ResourceTypeMismatch

OPEN_SPOTIFY_URL = 'https://open.spotify.com'
RESOURCE_TYPES = frozenset(['track', 'album', 'artist', 'playlist', 'user'])


def format_uri(obj_type, obj_id, owner_id=None):
    if owner_id:
        return 'spotify:user:{}:{}:{}'.format(owner_id, obj_type, obj_id)
    return 'spotify:{}:{}'.format(obj_type, obj_id)


def format_url(obj_type, obj_id, owner_id=None):
    if owner_id:
        return '/'.join([OPEN_SPOTIFY_URL, 'user', owner_id, obj_type, obj_id])
    return '/'.join([OPEN_SPOTIFY_URL, obj_type, obj_id])


@attrs(frozen=True)
class ResourceInfo:
    """
    Pseudo-immutable object storing type and ID of a Spotify Resource. The ``owner_id`` is an
    optional field and can be provided only for playlists: the old URIs and URLs for playlists
    required this field in the past. In any case,

    It can be constructed from spotify URIs (strings) and URLs.
    """
    type = attrib()
    id = attrib()
    owner_id = attrib(default=None)

    def __attrs_post_init__(self):
        if self.type not in RESOURCE_TYPES:
            raise ValueError('invalid resource type: %r' % self.type)

        if not self.id.isalnum():
            raise ValueError('invalid resource id: %r' % self.id)

        if self.owner_id:
            if self.type != 'playlist':
                raise ValueError('you provided owner_id but the object is not a playlist, it is: %r'
                                 % self.type)
            if not self.owner_id.isalnum():
                raise ValueError('invalid owner obj_id (not alphanumeric): %r' % self.owner_id)

    @staticmethod
    def _from_tokens(tokens, uri_or_url):
        if len(tokens) == 2:
            obj_type, obj_id = tokens[-2:]
            return ResourceInfo(obj_type, obj_id)

        elif len(tokens) == 4:
            # Handles legacy playlist URI/URL: spotify:user:{id}:playlist:{id} and analogous URL
            user, owner_id, playlist, obj_id = tokens
            if user != 'user':
                raise ValueError('invalid Spotify URI/URL: ' + uri_or_url)
            return ResourceInfo(playlist, obj_id, owner_id)

        else:
            raise ValueError('invalid Spotify URI/URL: ' + uri_or_url)

    @staticmethod
    def from_uri(uri):
        tokens = uri.split(':')
        if tokens[0] == 'spotify':   # "spotify:" part is optional
            tokens.pop(0)
        return ResourceInfo._from_tokens(tokens, uri)

    @staticmethod
    def from_url(url):
        if not url.startswith(OPEN_SPOTIFY_URL):
            raise ValueError('invalid URL: ' + url)
        tokens = url.split('/')[3:]
        return ResourceInfo._from_tokens(tokens, url)

    @staticmethod
    def parse(uri_or_url: str):
        if uri_or_url.startswith('https'):
            return ResourceInfo.from_url(uri_or_url)
        return ResourceInfo.from_uri(uri_or_url)

    @property
    def url(self):
        return format_url(self.type, self.id, self.owner_id)

    @property
    def uri(self):
        return format_uri(self.type, self.id, self.owner_id)

    def __repr__(self):
        if self.owner_id:
            return '%s(type=%r, id=%r, owner_id=%r)' % (self.__class__.__name__,
                                                        self.type, self.id, self.owner_id)
        return '%s(type=%r, id=%r)' % (self.__class__.__name__, self.type, self.id,)

    def __eq__(self, other):
        """ Note: owner_id is not used """
        return isinstance(other, ResourceInfo) and other.type == self.type and other.id == self.id

    def __hash__(self):
        """ Note: owner_id is not used """
        return hash(self.type, self.id)


def get_id(identifier, expected_type=None):
    """ Returns the base-62 ID number of a Spotify resource given a Spotify URI, a Spotify URL or
    the ID itself.

    May raise:
        * :exc:`ValueError` - if either ``identifier`` or ``expected_type`` are not valid;
        * :exc:`~spotipie.TypeMismatchError` - if the caller expect the first argument is the
          identifier of an object of type ``expected_type`` but it is not.
    """
    if identifier.isalnum():
        return identifier

    resource = ResourceInfo.parse(identifier)

    if expected_type and resource.type != expected_type:
        if expected_type not in RESOURCE_TYPES:
            raise ValueError('Invalid expected_type argument: ' + expected_type)
        else:
            raise ResourceTypeMismatch(expected_type, actual_type=resource.type)

    return resource.id


def pretty(d: dict) -> str:
    """ Prettify a dictionary """
    return pprint.pformat(d, indent=2, width=100, compact=True)


def normalize_scope(scope) -> Tuple[str, ...]:
    if not scope:
        return tuple()
    elif isinstance(scope, str):
        return tuple(sorted(scope.split()))
    elif isinstance(scope, Iterable):
        return tuple(sorted(list(scope)))
    else:
        raise TypeError('scope must be str or Iterable[str]')


def get_default_http_adapter(adapter_class=CacheControlAdapter):
    """
    Returns an HTTPAdapter that can be mounted to a session in order to add automatically
    resend a request if it failed. By default, a CacheControlAdapter is added. This
    adds caching to the session. Pass :class:`~requests.adapters.HttpAdapter` if you
    don't want caching.
    """
    return adapter_class(
        max_retries=urllib3.Retry(
            total=10,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504)
        ))
