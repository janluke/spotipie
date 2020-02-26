import inspect
import json
import os
import time
from typing import Any, Dict, Optional, Tuple, Union

import attr
from attr import attrib, attrs

from spotipie.utils import normalize_scope

TokenType = Union[Dict, 'OAuth2Token']


@attrs(frozen=True, auto_attribs=True, repr=False)
class OAuth2Token:
    access_token: str
    expires_in: int
    scope: Tuple[str, ...] = attrib(converter=normalize_scope)    # type: ignore
    state: Optional[str] = None
    token_type: str = 'Bearer'
    expires_at: Optional[float] = None
    refresh_token: Optional[str] = None

    def __attrs_post_init__(self):
        if self.expires_at is None:
            object.__setattr__(self, 'expires_at', time.time() + self.expires_in - 2)

    @staticmethod
    def from_dict(data, ignore_unknown_keys=False) -> 'OAuth2Token':
        if ignore_unknown_keys:
            valid_keys = inspect.signature(OAuth2Token.__init__).parameters.keys()
            data = {key: value for key, value in data if key in valid_keys}
        return OAuth2Token(**data)

    @staticmethod
    def from_json_string(string):
        return OAuth2Token.from_dict(json.loads(string))

    @staticmethod
    def from_json(path):
        with open(path) as fin:
            return OAuth2Token.from_dict(json.load(fin))

    def to_dict(self) -> Dict[str, Any]:
        return attr.asdict(self)

    def to_json_string(self):
        return json.dumps(self.to_dict(), indent=2)

    def to_json(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as fout:
            fout.write(self.to_json_string())

    def is_expired(self, margin=2) -> bool:
        return time.time() >= (self.expires_at - margin)

    def __repr__(self) -> str:
        attributes = ',\n'.join(
            '  {}: {!r}'.format(key, value) for key, value in vars(self).items())
        return '{}(\n{}\n)'.format(self.__class__.__name__, attributes)
