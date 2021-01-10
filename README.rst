========
Spotipie
========

.. start-badges

.. list-table::
    :stub-columns: 1
    :widths: 1 4

    * - docs
      - |docs|
    * - package
      - | |version| |wheel| |supported-versions|

.. |docs| image:: https://readthedocs.org/projects/spotipie/badge/?style=flat
    :target: https://spotipie.readthedocs.io/en/stable/
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/janLuke/spotipie.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/janLuke/spotipie

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/janLuke/spotipie?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/janLuke/spotipie

.. |requires| image:: https://requires.io/github/janLuke/spotipie/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/janLuke/spotipie/requirements/?branch=master

.. |codecov| image:: https://codecov.io/github/janLuke/spotipie/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/janLuke/spotipie

.. |version| image:: https://img.shields.io/pypi/v/spotipie.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/spotipie

.. |commits-since| image:: https://img.shields.io/github/commits-since/janLuke/spotipie/v0.1.2.svg
    :alt: Commits since latest release
    :target: https://github.com/janLuke/spotipie/compare/v0.1.2...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/spotipie.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/spotipie

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/spotipie.svg
    :alt: Supported versions
    :target: https://pypi.org/project/spotipie

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/spotipie.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/spotipie


.. end-badges

Another wrapper for the Spotify Web API, built on top of ``requests`` and
``requests_oauthlib``.

I wrote this package as a kind of "code generation experiment": the code (and doc) of
``Spotify`` class was almost entirely generated using a script that scrapes the
official Spotify Web API documentation.

For scripts and desktop apps, this package (optionally) includes a flask server
(meant to be run locally) to handle user authorization without requiring the
user to manually copy and paste the OAuth2 callback URL (containing the token)
from the browser to your app.

* Free software: MIT license

.. contents::

Installation
============
If you don't need the authorization flask app::

    pip install spotipie

otherwise::

    pip install spotipie[auth-app]


Usage
=====

1. Obtain your credentials as described
   `here <https://developer.spotify.com/documentation/web-api/quick-start/>`__.

2. (Optional) Store your credentials and redirection URI as environment variables:

   - ``SPOTIPIE_CLIENT_ID``
   - ``SPOTIPIE_CLIENT_SECRET``
   - ``SPOTIPIE_REDIRECT_URI``;

   you could also use another prefix, ``SPOTIPIE`` is just the default one.

3. To use the ``spotipie.Spotify`` client you first need to create an HTTP session
   and authenticate it. The ``Spotify`` constructor takes whatever behaves like
   a ``requests.Session``.
   ``spotipie`` provides one session class for each of the three OAuth2
   authorization flows supported by the Spotify API (see
   `Authorization Flows <https://developer.spotify.com/documentation/general/guides/authorization-guide/>`_);
   these classes are built on top of ``requests_oauthlib.OAuth2Session``
   (by composition, not inheritance):

   - ``ClientCredentialsSession``
   - ``AuthorizationCodeSession``
   - ``ImplicitGrantSession``

   To see how to create a session, see the `Examples`_.

4. Once you have an authenticated session, you can wrap it with the client and
   you're ready to make any API call you want::

    spotify = Spotify(session)
    results = spotify.search('symphony', obj_type='playlist')

   See the API of the client `here <https://spotipie.readthedocs.io/en/latest/api/spotipie.html#spotipie.Spotify>`__.


What OAuth2 flow should I use?
------------------------------
A backend web application should use:

- the *client credentials flow* if it doesn't need access to private user data;
- the *authorization code flow* otherwise.

For scripts and desktop application... it's more complicated. The recommended
flow in this case is *"Authorization code with PKCE"* but it's not supported by
Spotify at the time I'm writing this.

It's not recommended to distribute your code with your API secret key in it, so
both the client credentials flow and the authorization code flow should not be
used, unless you ask your users to use their own API keys; this can be acceptable
if your target users are other developers.

The *implicit grant flow* was designed for apps that run in the browser but has
been used for "native apps" too since it doesn't need the client secret key;
unfortunately, for native apps, it's neither very safe nor convenient from a
user perspective since the authorization is not refreshable.

Examples
========
All the examples assume your API credentials and redirect URI are stored as environment variables.

- `Client credentials flow <https://github.com/janLuke/spotipie/blob/master/docs/examples/client_credentials.py>`_
- `Authorization code flow for scripts / desktop apps <https://github.com/janLuke/spotipie/blob/master/docs/examples/desktop_app_authorization_code.py>`_
- `Implicit grant flow for scripts / desktop apps <https://github.com/janLuke/spotipie/blob/master/docs/examples/desktop_app_implicit_grant.py>`_
- `Flask web app (authorization code flow) <https://github.com/janLuke/spotipie/blob/master/docs/examples/flask_authorization_code.py>`_

API Reference
=============
https://spotipie.readthedocs.io/en/latest/api/spotipie.html



