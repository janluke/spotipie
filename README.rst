========
Overview
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
    :target: https://readthedocs.org/projects/spotipie
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

.. |commits-since| image:: https://img.shields.io/github/commits-since/janLuke/spotipie/v0.1.1.svg
    :alt: Commits since latest release
    :target: https://github.com/janLuke/spotipie/compare/v0.1.1...master

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

Installation
============
If you don't need the authorization flask app::

    pip install spotipie

otherwise::

    pip install spotipie[auth-app]


Usage
=====
You first need to create an OAuth2 session and obtain an authorization token for it.
There's a different OAuth2 session class for each of the three OAuth2 authorization flows
supported by the Spotify API (see `Authorization Flows <https://developer.spotify.com/documentation/general/guides/authorization-guide/>`_):

- ``ClientCredentialsSession``
- ``AuthorizationCodeSession``
- ``ImplicitGrantSession``

Then you can wrap the session with a ``Spotify`` object.

Examples
--------
- `Client credentials flow <https://github.com/janLuke/spotipie/blob/master/docs/examples/client_credentials.py>`_
- `Authorization code flow for desktop apps <https://github.com/janLuke/spotipie/blob/master/docs/examples/desktop_app_authorization_code.py>`_
- `Implicit grant flow for desktop apps <https://github.com/janLuke/spotipie/blob/master/docs/examples/desktop_app_implicit_grant.py>`_
- `Flask web app (authorization code flow) <https://github.com/janLuke/spotipie/blob/master/docs/examples/flask_authorization_code.py>`_

Documentation
=============
https://spotipie.readthedocs.io/



