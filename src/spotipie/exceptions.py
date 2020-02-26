__all__ = ['SpotipieException', 'HttpError', 'InsufficientScope', 'ResourceTypeMismatch',
           'AccessDenied', 'AuthorizationException', 'AuthorizationTimeout']


class SpotipieException(Exception):
    pass


class AuthorizationException(SpotipieException):
    """
    Exceptional event happened during user authorization (including access denied by the user)
    """
    pass


class AuthorizationTimeout(AuthorizationException):
    """ Raised when the authorization procedure started but the function waiting for a response from
    the user (or the Spotify server) doesn't get any response in ``timeout`` seconds.
    """
    def __init__(self, timeout):
        super().__init__('Timeout! No authorization response after %d seconds.' % timeout)


class AccessDenied(AuthorizationException):
    """ Raised when the user decides to not grant access to the app """
    def __init__(self, message="the user did not grant his/her authorization"):
        super().__init__(message)


class HttpError(SpotipieException):
    """ Error during HTTP request. It has a ``response`` attribute. """
    def __init__(self, response):
        details = (response.json()['error']['message']
                   if response.text and response.text != 'null'
                   else 'error')

        message = '{status} error: {details}\n' \
                  'URL: {url}'.format(status=response.status_code, details=details,
                                      url=response.url)
        self.response = response
        super().__init__(message)


class InsufficientScope(SpotipieException):
    """
    Raised when Spotipie catches that the scope of the session is not sufficient to carry out an
    API request **before** the actual request is made.

    Important notice
    ----------------
    Please, note that not all the errors caused by insufficient scope can be caught before a
    request is made: when this check is not possible and the scope is insufficient, an
    :class:~spotipie.errors.HttpError` is raised instead. So, make sure you include ``HttpError``
    in your ``try-except`` block whenever you want to catch insufficient scope errors.

    This class is here to provide you a better feedback than ``HttpError`` when this is possible.
    """
    def __init__(self, needed_scope, current_scope):
        missing_scope = list(sorted(set(needed_scope) - set(current_scope)))
        msg = ('Insufficient client scope for the request.\n'
               'The current scope is: {}.\n'
               'But the API call requires: {}.\n'
               'Missing scopes: {}\n'
               .format(current_scope, needed_scope, missing_scope))
        super().__init__(msg)
        self.current_scope = current_scope
        self.needed_scope = needed_scope
        self.missing_scope = missing_scope


class ResourceTypeMismatch(SpotipieException):
    """
    Raised when the raiser expect a Spotify resource of some kind but gets another.

    Note: "type" here doesn't refer to a Python type but to the type of a Python resource returned
    by Spotify API as a dictionary (contained in the "type" attribute of the dict).
    """
    def __init__(self, expected_type, actual_type):
        msg = 'expected type %r but got type %r' % (expected_type, actual_type)
        super().__init__(msg)
        self.expected_type = expected_type
        self.actual_type = actual_type
