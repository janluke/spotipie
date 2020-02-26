__all__ = ['Spotify']

import logging

from spotipie.auth import BaseOAuth2Session
from spotipie.exceptions import HttpError, InsufficientScope
from spotipie.utils import ResourceInfo

logger = logging.getLogger(__name__)


class Spotify(object):
    API_BASE_URL = 'https://api.spotify.com/v1'
    TYPE_TO_METHOD_NAME = dict(
        track='track', album='album',
        artist='artist', playlist='playlist',
        user='user_public_profile'
    )

    def __init__(self, session: BaseOAuth2Session):
        """
        Simple spotify web API client. It returns dictionaries matching exactly what is returned
        by the API as JSON. It implements all endpoints, including the beta endpoints.

        Args:
            session (BaseOAuth2Session):
        """
        self.session = session

    def _request(self, method, url, params={}, json_data=None, content_type=None):
        """
        Args:
            method:
                http method (GET, POST, PUT, DELETE)
            url:
            params:
                query parameters
            json_data:
                object to be serialized to a JSON string and sent as the body of the request
                (passed to requests.request in the ``json`` argument)
        """
        if not url.startswith('http'):
            url = self.API_BASE_URL + url

        headers = {}
        if content_type:
            headers['Content-Type'] = content_type

        # Remove None params and convert sequences to strings of comma-separated values
        processed_params = dict()
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (tuple, list)):
                processed_params[key] = ','.join(map(str, value))
            else:
                processed_params[key] = value

        if json_data:
            json_data = {key: value for key, value in json_data.items() if value is not None}
            json_data = json_data or None

        response = self.session.request(method, url, headers=headers,
                                        params=processed_params, json=json_data)

        if response.status_code >= 400:
            response.connection.close()
            raise HttpError(response)

        if response.text and response.text != 'null':
            return response.json()
        return None

    def _get(self, url, params={}):
        return self._request('GET', url, params)

    def _post(self, url, params={}, json_data=None, content_type='application/json'):
        return self._request('POST', url, params, json_data, content_type)

    def _delete(self, url, params={}, json_data=None):
        return self._request('DELETE', url, params, json_data)

    def _put(self, url, params={}, json_data=None, content_type='application/json'):
        return self._request('PUT', url, params, json_data, content_type)

    def _ensure_scope(self, needed_scope, current_scope=None, public=None):
        """
        Ensures that the current authorization scope is sufficient to carry out the request.
        If not, it raises an InsufficientScopeError with detailed information.

        Args:
            needed_scope (string): space-separated scope strings
            current_scope (Optional[Set[str]]): set of scope strings
            public (bool):
                some requests need the "public" or "private" version of the same scope (e.g.
                playlist-modify-public and playlist-modify-private) depending on whether the
                resource is public or private; rather than calling this function
                differently depending on the value of public, you can directly pass "public";
                the scopes in ``needed_scope`` ending with ``"-"`` will be completed with the
                right suffix, e.g.::

                    self._ensure_scope('playlist-modify-', public=False)

                will check for "playlist-modify-private".
        """
        needed_scope = set(needed_scope.split())
        if public is not None:
            suffix = 'public' if public else 'private'
            needed_scope = set(scope_string + suffix if scope_string.endswith('-') else scope_string
                               for scope_string in needed_scope)

        if current_scope is None:
            current_scope = set(self.session.scope)

        if not current_scope >= needed_scope:
            raise InsufficientScope(needed_scope, current_scope)

    def _get_resource(self, res_type, res_id, **kwargs):
        method_name = self.TYPE_TO_METHOD_NAME.get(res_type)
        if method_name is None:
            raise ValueError('Invalid object type: ' + res_type)
        method = getattr(self, method_name)
        return method(res_id, **kwargs)

    def get(self, uri_or_url, **kwargs):
        """
        Returns an object (track, album, artist, playlist or user) given its spotify URI or URL.
        """
        resource = ResourceInfo.parse(uri_or_url)
        return self._get_resource(resource.type, resource.id, **kwargs)

    def iter(self, start_page):
        """
        Returns an iterator of all the items in a sequence of pages (dictionary with 'items'
        and 'next' keys). For example::

            all_playlist_tracks = list(client.all(playlist['tracks']))
            all_album_tracks = list(client.all(album['tracks']))
        """
        yield from start_page['items']
        page = start_page
        while page['next']:
            page = self._get(page['next'])
            yield from page['items']

    def next_page(self, page):
        """
        Returns the next result given a paged result

        Args:
            page: a previously returned paged result
        """
        if page['next']:
            return self._get(page['next'])
        else:
            return None

    def previous_page(self, result):
        """
        Returns the previous result given a paged result

        Args:
            result: a previously returned paged result
        """
        if result['previous']:
            return self._get(result['previous'])
        else:
            return None

    # **********************************************************************#
    #                              Albums                                   #
    # **********************************************************************#
    def album(self, album_id, market=None):
        """
        Get Spotify catalog information for a single album.
        https://developer.spotify.com/documentation/web-api/reference/albums/get-album/
        """
        return self._get(url='/albums/{id}'.format(id=album_id), params=dict(market=market))

    def album_tracks(self, album_id, limit=20, offset=0, market=None):
        """
        Get Spotify catalog information about an album's tracks.
        https://developer.spotify.com/documentation/web-api/reference/albums/get-albums-tracks/

        Args:
            album_id:
            limit:
                *Optional*. The maximum number of tracks to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first track to return. Default: 0 (the first object).
                Use with limit to get the next set of tracks.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
        """
        return self._get(url='/albums/{id}/tracks'.format(id=album_id),
                         params=dict(limit=limit, offset=offset, market=market))

    def albums(self, ids, market=None):
        """
        Get Spotify catalog information for multiple albums identified by their Spotify IDs.
        https://developer.spotify.com/documentation/web-api/reference/albums/get-several-albums/

        Args:
            ids:
                *Required*. A list of the Spotify IDs. Maximum: 20 IDs.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
        """
        return self._get(url='/albums', params=dict(ids=ids, market=market))['albums']

    # **********************************************************************#
    #                             Artists                                  #
    # **********************************************************************#
    def artist(self, artist_id):
        """
        Get Spotify catalog information for a single artist identified by their unique Spotify ID.
        https://developer.spotify.com/documentation/web-api/reference/artists/get-artist/
        """
        return self._get(url='/artists/{id}'.format(id=artist_id))

    def artist_albums(self, artist_id, include_groups=None, market=None, limit=20, offset=0):
        """
        Get Spotify catalog information about an artist's albums. Optional parameters can be
        specified in the query string to filter and sort the response_args.
        https://developer.spotify.com/documentation/web-api/reference/artists/get-artists-albums/

        Args:
            artist_id:
            include_groups:
                *Optional*. A comma-separated list of keywords that will be used to filter the
                response_args. If not supplied, all album types will be returned. Valid values are:
                - ``album`` - ``single`` - ``appears_on`` - ``compilation``
                For example:
                ``include_groups=album,single``.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Supply this parameter to limit the response_args to one particular geographical
                market.
                For example, for albums available in Sweden: ``market=SE``. *If not given, results
                will be returned for all markets and you are likely to get duplicate results per
                album, one for each market in which the album is available!*
            limit:
                *Optional*. The number of album objects to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first album to return. Default: 0 (i.e., the first
                album). Use with ``limit`` to get the next set of albums.
        """
        return self._get(url='/artists/{id}/albums'.format(id=artist_id),
                         params=dict(include_groups=include_groups, market=market,
                                     limit=limit, offset=offset))

    def artist_top_tracks(self, artist_id, market):
        """
        Get Spotify catalog information about an artist's top tracks by country.
        https://developer.spotify.com/documentation/web-api/reference/artists/get-artists-top-tracks/

        Args:
            artist_id:
            market:
                *Required*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
        """
        return self._get(url='/artists/{id}/top-tracks'.format(id=artist_id),
                         params=dict(market=market))

    def artist_related_artists(self, artist_id):
        """
        Get Spotify catalog information about artists similar to a given artist. Similarity is
        based on analysis of the Spotify community's listening history.
        https://developer.spotify.com/documentation/web-api/reference/artists/get-related-artists/

        Args:
            artist_id: The Spotify ID for the artist.
        """
        return self._get(url='/artists/{id}/related-artists'.format(id=artist_id))

    def artists(self, ids):
        """
        Get Spotify catalog information for several artists based on their Spotify IDs.
        https://developer.spotify.com/documentation/web-api/reference/artists/get-several-artists/

        Args:
            ids: A list of the Spotify IDs. Maximum: 50 IDs.
        """
        return self._get(url='/artists', params=dict(ids=ids))['artists']

    # **********************************************************************#
    #                              Browse                                   #
    # **********************************************************************#
    def category(self, category_id, country=None, locale=None):
        """
        Get a single category used to tag items in Spotify (on, for example, the Spotify player's
        “Browse” tab).
        https://developer.spotify.com/documentation/web-api/reference/browse/get-category/

        Args:
            category_id:
                The `Spotify category ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the category.
            country:
                *Optional*. A country: an `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__. Provide this parameter to
                ensure that the category exists for a particular country.
            locale:
                *Optional*. The desired language, consisting of an `ISO 639-1
                <http://en.wikipedia.org/wiki/ISO_639-1>`__ language code and an `ISO 3166-1
                alpha-2 country code <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__, joined
                by an underscore. For example: ``es_MX``, meaning "Spanish (Mexico)". Provide this
                parameter if you want the category strings returned in a particular language. Note
                that, if ``locale`` is not supplied, or if the specified language is not available,
                the category strings returned will be in the Spotify default language (American
                English).
        """
        return self._get(url='/browse/categories/{category_id}'.format(category_id=category_id),
                         params=dict(country=country, locale=locale))

    def category_playlists(self, category_id, country=None, limit=20, offset=0):
        """
        Get a list of Spotify playlists tagged with a particular category.
        https://developer.spotify.com/documentation/web-api/reference/browse/get-categorys-playlists/

        Args:
            category_id:
                The `Spotify category ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the category.
            country:
                *Optional*. A country: an `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__.
            limit:
                *Optional*. The maximum number of items to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first item to return. Default: 0 (the first object).
                Use with ``limit`` to get the next set of items.
        """
        return self._get(
            url='/browse/categories/{category_id}/playlists'.format(category_id=category_id),
            params=dict(country=country, limit=limit, offset=offset))

    def categories(self, country=None, locale=None, limit=20, offset=0):
        """
        Get a list of categories used to tag items in Spotify (on, for example, the Spotify
        player's “Browse” tab).
        https://developer.spotify.com/documentation/web-api/reference/browse/get-list-categories/

        Args:
            country:
                *Optional*. A country: an `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__. Provide this parameter if you
                want to narrow the list of returned categories to those relevant to a particular
                country. If omitted, the returned items will be globally relevant.
            locale:
                *Optional*. The desired language, consisting of an `ISO 639-1
                <http://en.wikipedia.org/wiki/ISO_639-1>`__ language code and an `ISO 3166-1
                alpha-2 country code <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__, joined
                by an underscore. For example: ``es_MX``, meaning “Spanish (Mexico)”. Provide this
                parameter if you want the category metadata returned in a particular language. Note
                that, if ``locale`` is not supplied, or if the specified language is not available,
                all strings will be returned in the Spotify default language (American English).
                The ``locale`` parameter, combined with the ``country`` parameter, may give odd
                results if not carefully matched. For example ``country=SE&locale=de_DE`` will
                return a list of categories relevant to Sweden but as German language strings.
            limit:
                *Optional*. The maximum number of categories to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first item to return. Default: 0 (the first object).
                Use with ``limit`` to get the next set of categories.
        """
        return self._get(url='/browse/categories',
                         params=dict(country=country, locale=locale, limit=limit,
                                     offset=offset))['categories']

    def featured_playlists(self, locale=None, country=None, timestamp=None, limit=20, offset=0):
        """
        Get a list of Spotify featured playlists (shown, for example, on a Spotify player's
        ‘Browse' tab).
        https://developer.spotify.com/documentation/web-api/reference/browse/get-list-featured-playlists/

        Args:
            locale:
                *Optional*. The desired language, consisting of a lowercase `ISO 639-1 language
                code <http://en.wikipedia.org/wiki/ISO_639-1>`__ and an uppercase `ISO 3166-1
                alpha-2 country code <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__, joined
                by an underscore. For example: ``es_MX``, meaning “Spanish (Mexico)”. Provide this
                parameter if you want the results returned in a particular language (where
                available). Note that, if ``locale`` is not supplied, or if the specified language
                is not available, all strings will be returned in the Spotify default language
                (American English). The ``locale`` parameter, combined with the ``country``
                parameter, may give odd results if not carefully matched. For example
                ``country=SE&locale=de_DE`` will return a list of categories relevant to Sweden but
                as German language strings.
            country:
                *Optional*. A country: an `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__. Provide this parameter if you
                want the list of returned items to be relevant to a particular country. If omitted,
                the returned items will be relevant to all countries.
            timestamp:
                *Optional*. A timestamp in `ISO 8601 format
                <http://en.wikipedia.org/wiki/ISO_8601>`__: ``yyyy-MM-ddTHH:mm:ss``. Use this
                parameter to specify the user's local time to get results tailored for that
                specific date and time in the day. If not provided, the response_args defaults to
                the current UTC time. Example: “2014-10-23T09:00:00” for a user whose local time is
                9AM. If there were no featured playlists (or there is no data) at the specified
                time, the response_args will revert to the current UTC time.
            limit:
                *Optional*. The maximum number of items to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first item to return. Default: 0 (the first object).
                Use with ``limit`` to get the next set of items.
        """
        return self._get(url='/browse/featured-playlists',
                         params=dict(locale=locale, country=country, timestamp=timestamp,
                                     limit=limit, offset=offset))

    def new_releases(self, country=None, limit=20, offset=0):
        """
        Get a list of new album releases featured in Spotify (shown, for example, on a Spotify
        player's “Browse” tab).
        https://developer.spotify.com/documentation/web-api/reference/browse/get-list-new-releases/

        Args:
            country:
                *Optional*. A country: an `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__. Provide this parameter if you
                want the list of returned items to be relevant to a particular country. If omitted,
                the returned items will be relevant to all countries.
            limit:
                *Optional*. The maximum number of items to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first item to return. Default: 0 (the first object).
                Use with ``limit`` to get the next set of items.
        """
        return self._get(url='/browse/new-releases',
                         params=dict(country=country, limit=limit, offset=offset))

    def recommendations(self, limit=20, market=None,
                        seed_artists=None, seed_genres=None, seed_tracks=None,
                        **filters):
        """
        Create a playlist-style listening experience based on seed artists, tracks and genres.
        https://developer.spotify.com/documentation/web-api/reference/browse/get-recommendations/

        Args:
            limit:
                *Optional*. The target size of the list of recommended tracks. For seeds with
                unusually small pools or when highly restrictive filtering is applied, it may be
                impossible to generate the requested number of recommended tracks. Debugging
                information for such cases is available in the response_args.
                Default: 20. Minimum: 1. Maximum: 100.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide>`__.
                Because ``min_*``, ``max_*`` and ``target_*`` are applied to pools before
                relinking, the generated results may not precisely match the filters applied.
                Original, non-relinked tracks are available via the ``linked_from`` attribute of
                the `relinked track response_args
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide>`__.
            seed_artists (list or string of comma-separated values):
                List of the Spotify IDs of the seed artists.
                Up to 5 seed values may be provided in any combination of
                ``seed_artists``, ``seed_tracks`` and ``seed_genres``.
            seed_genres (list or string of comma-separated values):
                A list of any genres in the set of `available genre seeds
                <https://developer.spotify.com/#available-genre-seeds>`__.
                Up to 5 seed values may be provided in any combination of ``seed_artists``,
                ``seed_tracks`` and ``seed_genres``.
            seed_tracks (list or string of comma-separated values):
                A list of `Spotify IDs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for a seed track. Up to 5 seed values may be provided in any combination of
                ``seed_artists``, ``seed_tracks`` and ``seed_genres``.

            **filters:
                Open the endpoint URL above for the complete list of tunable attributes
                (at the bottom of the page). Filters are of three types:

                - max_{attribute}:  a hard ceiling on the selected track attribute's value, e.g.
                  ``max_instrumentalness=0.35`` would filter out most tracks that are likely to be
                  instrumental.

                - min_{attribute}:
                    e.g. ``min_tempo=140`` would restrict results to only those tracks with a tempo
                    of greater than 140 beats per minute.

                - target_{attribute}:
                    tracks with the attribute values nearest to the target values will be preferred,
                    e.g. you might request ``target_energy=0.6`` and ``target_danceability=0.8``;
                    all target values will be weighed equally in ranking results.
        """
        params = dict(limit=limit, market=market, seed_artists=seed_artists,
                      seed_genres=seed_genres, seed_tracks=seed_tracks)
        params.update(filters)
        return self._get(url='/recommendations', params=params)

    # **********************************************************************#
    #                              Follow                                   #
    # **********************************************************************#
    def user_is_following(self, obj_type, ids):
        """
        Check to see if the current user is following one or more artists or Spotify users.
        https://developer.spotify.com/documentation/web-api/reference/follow/check-current-user-follows/

        Relevant authorization scopes: user-follow-read

        Args:
            obj_type: either 'artist' or 'user'
            ids (list of IDs or string of comma-separated artist IDs):
        """
        self._ensure_scope('user-follow-read')

        if obj_type not in ['user', 'artist']:
            raise ValueError('Invalid "obj_type" argument: ' + str(obj_type))
        return self._get(url='/me/following/contains', params=dict(type=obj_type, ids=ids))

    def user_is_following_users(self, ids):
        """
        Check to see if the current user is following one or more Spotify users.
        https://developer.spotify.com/documentation/web-api/reference/follow/check-current-user-follows/

        Relevant authorization scopes: user-follow-read

        Args:
            ids (list of IDs or string of comma-separated users IDs):
        """
        return self.user_is_following('user', ids)

    def user_is_following_artists(self, ids):
        """
        Check to see if the current user is following one or more Spotify artists.
        https://developer.spotify.com/documentation/web-api/reference/follow/check-current-user-follows/

        Relevant authorization scopes: user-follow-read

        Args:
            ids (list of IDs or string of comma-separated users IDs):
        """
        return self.user_is_following('artist', ids)

    def playlist_is_followed_by(self, playlist_id, user_ids):
        """
        Check to see if one or more Spotify users are following a specified playlist.
        https://developer.spotify.com/documentation/web-api/reference/follow/check-user-following-playlist/

        Relevant authorization scopes: playlist-read-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__ of
                the playlist.
            user_ids:
                *Required*. A list of `Spotify User IDs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__ ;
                the ids of the users that you want to check to see if they follow the playlist.
                Maximum: 5 ids.

        Returns:
            dictionary id -> True/False
        """
        return self._get(
            url='/playlists/{playlist_id}/followers/contains'.format(playlist_id=playlist_id),
            params=dict(ids=user_ids))

    def follow(self, obj_type, ids):
        """
        Add the current user as a follower of one or more artists or other Spotify users.
        https://developer.spotify.com/documentation/web-api/reference/follow/follow-artists-users/

        Relevant authorization scopes: user-follow-modify

        Args:
            obj_type:
                *Required*. The ID type: either ``artist`` or ``user``.
            ids (list of Spotify ID strings):
                *Optional*. A list of the artist or user `Spotify IDs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__. A
                maximum of 50 IDs can be sent in one request
        """
        self._ensure_scope('user-follow-modify')
        return self._put(url='/me/following', params=dict(type=obj_type),
                         json_data=dict(ids=ids))

    def follow_artists(self, artist_ids):
        return self.follow('artist', artist_ids)

    def follow_users(self, user_ids):
        return self.follow('user', user_ids)

    def follow_playlist(self, playlist_id, public=True):
        """
        Add the current user as a follower of a playlist.
        https://developer.spotify.com/documentation/web-api/reference/follow/follow-playlist/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__ of
                the playlist. Any playlist can be followed, regardless of its `public/private
                status
                <https://developer.spotify.com/documentation/general/guides/working-with-playlists/#public-private-and-collaborative-status>`__,
                as long as you know its playlist ID.
            public (Boolean):
                *Optional*. Defaults to ``true``. If ``true`` the playlist will be included in
                user's public playlists, if ``false`` it will remain private. To be able to follow
                playlists privately, the user must have granted the ``playlist-modify-private``
                `scope
                <https://developer.spotify.com/documentation/general/guides/authorization-guide/#list-of-scopes>`__.
        """
        self._ensure_scope('playlist-modify-', public=public)

        return self._put(url='/playlists/{playlist_id}/followers'.format(playlist_id=playlist_id),
                         json_data=dict(public=public))

    def user_followed_artists(self, obj_type, limit=20, after=None):
        """
        Get the current user's followed artists.
        https://developer.spotify.com/documentation/web-api/reference/follow/get-followed/

        Relevant authorization scopes: user-follow-read

        Args:
            obj_type:
                *Required*. The ID type: currently only ``artist`` is supported.
            limit:
                *Optional*. The maximum number of items to return. Default: 20. Minimum: 1.
                Maximum: 50.
            after:
                *Optional*. The last artist ID retrieved from the previous request.
        """
        self._ensure_scope('user-follow-read')
        return self._get(url='/me/following?obj_type=artist',
                         params=dict(type=obj_type, limit=limit, after=after))

    def unfollow(self, obj_type, ids):
        """
        Remove the current user as a follower of one or more artists or other Spotify users.
        https://developer.spotify.com/documentation/web-api/reference/follow/unfollow-artists-users/

        Relevant authorization scopes: user-follow-modify

        Args:
            obj_type:
                *Required*. The ID type: either ``artist`` or ``user``.
            ids (list of Spotify ID strings):
                A list of the artist or user `Spotify IDs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__. A
                maximum of 50 IDs can be sent in one request
        """
        self._ensure_scope('user-follow-modify')
        return self._delete(url='/me/following', params=dict(type=obj_type),
                            json_data=dict(ids=ids))

    def unfollow_artists(self, artist_ids):
        return self.unfollow('artist', artist_ids)

    def unfollow_users(self, user_ids):
        return self.unfollow('user', user_ids)

    def unfollow_playlist(self, playlist_id):
        """
        Remove the current user as a follower of a playlist.
        https://developer.spotify.com/documentation/web-api/reference/follow/unfollow-playlist/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The Spotify ID of the playlist that is to be no longer followed.
        """
        return self._delete(
            url='/playlists/{playlist_id}/followers'.format(playlist_id=playlist_id))

    # **********************************************************************#
    #                              Library                                 #
    # **********************************************************************#
    def user_saved_albums_contains(self, album_ids):
        """
        Check if one or more albums is already saved in the current Spotify user's ‘Your Music'
        library.
        https://developer.spotify.com/documentation/web-api/reference/library/check-users-saved-albums/

        Relevant authorization scopes: user-library-read

        Args:
            album_ids: Maximum: 50 IDs.

        Returns:
            dictionary album_id -> bool(the album is between the user saved albums)
        """
        self._ensure_scope('user-library-read')
        return self._get(url='/me/albums/contains', params=dict(ids=album_ids))

    def user_saved_tracks_contains(self, track_ids):
        """
        Check if one or more tracks is already saved in the current Spotify user's ‘Your Music'
        library.
        https://developer.spotify.com/documentation/web-api/reference/library/check-users-saved-tracks/

        Relevant authorization scopes: user-library-read

        Args:
            track_ids: Maximum: 50 IDs.

        Returns:
            dictionary track_id -> bool(the track is between the user saved tracks)
        """
        self._ensure_scope('user-library-read')
        return self._get(url='/me/tracks/contains', params=dict(ids=track_ids))

    def user_saved_albums(self, limit=20, offset=0, market=None):
        """
        Get a list of the albums saved in the current Spotify user's ‘Your Music' library.
        https://developer.spotify.com/documentation/web-api/reference/library/get-users-saved-albums/

        Relevant authorization scopes: user-library-read

        Args:
            limit:
                *Optional*. The maximum number of objects to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first object to return. Default: 0 (i.e., the first
                object). Use with ``limit`` to get the next set of objects.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        self._ensure_scope('user-library-read')
        return self._get(url='/me/albums',
                         params=dict(limit=limit, offset=offset, market=market))

    def user_saved_tracks(self, limit=20, offset=0, market=None):
        """
        Get a list of the songs saved in the current Spotify user's ‘Your Music' library.
        https://developer.spotify.com/documentation/web-api/reference/library/get-users-saved-tracks/

        Relevant authorization scopes: user-library-read

        Args:
            limit:
                *Optional*. The maximum number of objects to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first object to return. Default: 0 (i.e., the first
                object). Use with ``limit`` to get the next set of objects.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        self._ensure_scope('user-library-read')
        return self._get(url='/me/tracks',
                         params=dict(limit=limit, offset=offset, market=market))

    def remove_albums_from_library(self, ids=None):
        """
        Remove one or more albums from the current user's ‘Your Music' library.
        https://developer.spotify.com/documentation/web-api/reference/library/remove-albums-user/

        Relevant authorization scopes: user-library-modify

        Args:
            ids: Maximum: 50 IDs.
        """
        self._ensure_scope('user-library-modify')
        return self._delete(url='/me/albums?ids={ids}', params=dict(ids=ids))

    def remove_tracks_from_library(self, ids=None):
        """
        Remove one or more tracks from the current user's ‘Your Music' library.
        https://developer.spotify.com/documentation/web-api/reference/library/remove-tracks-user/

        Relevant authorization scopes: user-library-modify

        Args:
            ids: Maximum: 50 IDs.
        """
        self._ensure_scope('user-library-modify')
        return self._delete(url='/me/tracks', params=dict(ids=ids))

    def save_albums_to_library(self, ids=None):
        """
        Save one or more albums to the current user's ‘Your Music' library.
        https://developer.spotify.com/documentation/web-api/reference/library/save-albums-user/

        Relevant authorization scopes: user-library-modify

        Args:
            ids: Maximum: 50 IDs.
        """
        self._ensure_scope('user-library-modify')
        return self._put(url='/me/albums?ids={ids}', params=dict(ids=ids))

    def save_tracks_to_library(self, ids=None):
        """
        Save one or more tracks to the current user's ‘Your Music' library.
        https://developer.spotify.com/documentation/web-api/reference/library/save-tracks-user/

        Relevant authorization scopes: user-library-modify

        Args:
            ids: Maximum: 50 IDs.
        """
        self._ensure_scope('user-library-modify')
        return self._put(url='/me/tracks', params=dict(ids=ids))

    # **********************************************************************#
    #                          Personalization                             #
    # **********************************************************************#
    def user_top(self, obj_type, limit=20, offset=0, time_range='medium_term'):
        """
        Get the current user's top artists or tracks based on calculated affinity.
        https://developer.spotify.com/documentation/web-api/reference/personalization/get-users-top-artists-and-tracks/

        Relevant authorization scopes: user-top-read

        Args:
            obj_type:
                The type of entity to return. Valid values: ``artists`` or ``tracks``.
            limit:
                *Optional*. The number of entities to return. Default: 20. Minimum: 1. Maximum: 50.
                For example: ``limit=2``
            offset:
                *Optional*. The index of the first entity to return. Default: 0 (i.e., the first
                track). Use with limit to get the next set of entities.
            time_range:
                *Optional*. Over what time frame the affinities are computed. Valid values:
                ``long_term`` (calculated from several years of data and including all new data as
                it becomes available), ``medium_term`` (approximately last 6 months),
                ``short_term`` (approximately last 4 weeks). Default: ``medium_term``.
        """
        self._ensure_scope('user-top-read')

        if obj_type not in ['artists', 'tracks']:
            raise ValueError('Invalid obj_type argument: ' + obj_type)

        return self._get(url='/me/top/{type}'.format(type=obj_type),
                         params=dict(limit=limit, offset=offset, time_range=time_range))

    def user_top_artists(self, limit=20, offset=0, time_range='medium_term'):
        """
        Get the current user's top artists based on calculated affinity.
        https://developer.spotify.com/documentation/web-api/reference/personalization/get-users-top-artists-and-tracks/

        Relevant authorization scopes: user-top-read

        Args:
            limit:
                *Optional*. The number of entities to return. Default: 20. Minimum: 1. Maximum: 50.
                For example: ``limit=2``
            offset:
                *Optional*. The index of the first entity to return. Default: 0 (i.e., the first
                track). Use with limit to get the next set of entities.
            time_range:
                *Optional*. Over what time frame the affinities are computed. Valid values:
                ``long_term`` (calculated from several years of data and including all new data as
                it becomes available), ``medium_term`` (approximately last 6 months),
                ``short_term`` (approximately last 4 weeks). Default: ``medium_term``.
        """
        return self.user_top('artists', limit, offset, time_range)

    def user_top_tracks(self, limit=20, offset=0, time_range='medium_term'):
        """
        Get the current user's top tracks based on calculated affinity.
        https://developer.spotify.com/documentation/web-api/reference/personalization/get-users-top-artists-and-tracks/

        Relevant authorization scopes: user-top-read

        Args:
            limit:
                *Optional*. The number of entities to return. Default: 20. Minimum: 1. Maximum: 50.
                For example: ``limit=2``
            offset:
                *Optional*. The index of the first entity to return. Default: 0 (i.e., the first
                track). Use with limit to get the next set of entities.
            time_range:
                *Optional*. Over what time frame the affinities are computed. Valid values:
                ``long_term`` (calculated from several years of data and including all new data as
                it becomes available), ``medium_term`` (approximately last 6 months),
                ``short_term`` (approximately last 4 weeks). Default: ``medium_term``.
        """
        return self.user_top('tracks', limit, offset, time_range)

    # **********************************************************************#
    #                              Player                                   #
    # **********************************************************************#
    def available_devices(self):
        """
        Get information about a user's available devices.
        https://developer.spotify.com/documentation/web-api/reference/player/get-a-users-available-devices/

        Relevant authorization scopes: user-read-playback-state
        """
        self._ensure_scope('user-read-playback-state')
        return self._get(url='/me/player/devices')

    def playback_state(self, market=None):
        """
        Get information about the user's current playback state, including track, track progress,
        and active device.
        https://developer.spotify.com/documentation/web-api/reference/player/get-information-about-the-users-current-playback/

        Relevant authorization scopes: user-read-playback-state

        Args:
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        self._ensure_scope('user-read-playback-state')
        return self._get(url='/me/player', params=dict(market=market))

    def user_recently_played_tracks(self, limit=20, after=None, before=None):
        """
        Get tracks from the current user's recently played tracks.
        https://developer.spotify.com/documentation/web-api/reference/player/get-recently-played/

        Relevant authorization scopes: user-read-recently-played

        Args:
            limit:
                *Optional*. The maximum number of items to return. Default: 20. Minimum: 1.
                Maximum: 50.
            after:
                *Optional*. A Unix timestamp in milliseconds. Returns all items after (but not
                including) this cursor position. If ``after`` is specified, ``before`` must not be
                specified.
            before:
                *Optional*. A Unix timestamp in milliseconds. Returns all items before (but not
                including) this cursor position. If ``before`` is specified, ``after`` must not be
                specified.
        """
        self._ensure_scope('user-read-recently-played')
        return self._get(url='/me/player/recently-played',
                         params=dict(limit=limit, after=after, before=before))

    def currently_playing_track(self, market=None):
        """
        Get the object currently being played on the user's Spotify account.
        https://developer.spotify.com/documentation/web-api/reference/player/get-the-users-currently-playing-track/

        Relevant authorization scopes: user-read-currently-playing, user-read-playback-state

        Args:
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        self._ensure_scope('user-read-currently-playing user-read-playback-state')
        return self._get(url='/me/player/currently-playing', params=dict(market=market))

    def pause(self, device_id=None):
        """
        Pause playback on the user's account.
        https://developer.spotify.com/documentation/web-api/reference/player/pause-a-users-playback/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._put(url='/me/player/pause', params=dict(device_id=device_id))

    def seek(self, position_ms, device_id=None):
        """
        Seeks to the given position in the user's currently playing track.
        https://developer.spotify.com/documentation/web-api/reference/player/seek-to-position-in-currently-playing-track/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            position_ms:
                *Required*. The position in milliseconds to seek to. Must be a positive number.
                Passing in a position that is greater than the length of the track will cause the
                player to start playing the next song.
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._put(url='/me/player/seek',
                         params=dict(position_ms=position_ms, device_id=device_id))

    def set_repeat_mode(self, state, device_id=None):
        """
        Set the repeat mode for the user's playback. Options are repeat-track, repeat-context, and
        off.
        https://developer.spotify.com/documentation/web-api/reference/player/set-repeat-mode-on-users-playback/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            state:
                ``"track"``, ``"context"`` or ``"off"``. ``"track"`` will repeat the current
                track. ``"context"`` will repeat the current context. ``"off"`` will turn repeat off
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._put(url='/me/player/repeat',
                         params=dict(state=state, device_id=device_id))

    def set_volume(self, volume_percent, device_id=None):
        """
        Set the volume for the user's current playback device.
        https://developer.spotify.com/documentation/web-api/reference/player/set-volume-for-users-playback/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            volume_percent:
                *Required*. Integer. The volume to set. Must be a value from 0 to 100 inclusive.
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._put(url='/me/player/volume',
                         params=dict(volume_percent=volume_percent, device_id=device_id))

    def skip_to_next_track(self, device_id=None):
        """
        Skips to next track in the user's queue.
        https://developer.spotify.com/documentation/web-api/reference/player/skip-users-playback-to-next-track/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._post(url='/me/player/next', params=dict(device_id=device_id))

    def skip_to_previous_track(self, device_id=None):
        """
        Skips to previous track in the user's queue.
        https://developer.spotify.com/documentation/web-api/reference/player/skip-users-playback-to-previous-track/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._post(url='/me/player/previous', params=dict(device_id=device_id))

    def play(self, device_id=None, context_uri=None, uris=None, start_from=0, position_ms=None):
        """
        Start a new context or resume current playback on the user's active device.
        https://developer.spotify.com/documentation/web-api/reference/player/start-a-users-playback/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
            context_uri (string):
                *Optional*. Spotify URI of the context to play. Valid contexts are albums, artists,
                playlists.
            uris (list of URIs):
                *Optional*. A list of the Spotify track URIs to play
            start_from (int or str):
                *Optional*. Indicates from where in the context playback should start. Only
                available when ``context_uri`` corresponds to an album or playlist object, or when
                the ``uris`` parameter is used. It can be provided

                - as an integer - the position of the track from which to start
                - or as a string - the Spotify URI of the track from which to start.

            position_ms (integer):
                *Optional*. Indicates from what position to start playback. Must be a positive
                number. Passing in a position that is greater than the length of the track will
                cause the player to start playing the next song.
        """
        self._ensure_scope('user-modify-playback-state')

        offset = None
        if start_from:
            if isinstance(start_from, int):
                offset = {'position': start_from}
            elif isinstance(start_from, str):
                offset = {'uri': start_from}
            else:
                raise TypeError('Invalid start_from argument: ' + str(start_from))

        return self._put(url='/me/player/play', params=dict(device_id=device_id),
                         json_data=dict(context_uri=context_uri, uris=uris, offset=offset,
                                        position_ms=position_ms))

    def toggle_shuffle(self, state, device_id=None):
        """
        Toggle shuffle on or off for user's playback.
        https://developer.spotify.com/documentation/web-api/reference/player/toggle-shuffle-for-users-playback/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            state:
                *Required* **true** : Shuffle user's playback **false** : Do not shuffle user's
                playback.
            device_id:
                *Optional*. The id of the device this command is targeting. If not supplied, the
                user's currently active device is the target.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._put(url='/me/player/shuffle',
                         params=dict(state=state, device_id=device_id))

    def transfer_user_playback(self, device_ids, play=None):
        """
        Transfer playback to a new device and determine if it should start playing.
        https://developer.spotify.com/documentation/web-api/reference/player/transfer-a-users-playback/

        Relevant authorization scopes: user-modify-playback-state

        Args:
            device_ids (list of Spotify Device IDs):
                *Required*. A list containing the ID of the device on which playback should be
                started/transferred. For example: ``{device_ids:["74ASZWbe4lXaubB36ztrGX"]}``
                Note: Although an list is accepted, only a single device_id is currently supported.
                Supplying more than one will return ``400 Bad Request``
            play (boolean):
                ``True``: ensure playback happens on new device.
                ``False`` or ``None``: keep the current playback state.
        """
        self._ensure_scope('user-modify-playback-state')
        return self._put(url='/me/player', json_data=dict(device_ids=device_ids, play=play))

    # **********************************************************************#
    #                             Playlist                                 #
    # **********************************************************************#
    def add_tracks_to_playlist(self, playlist_id, uris=None, position=None):
        """
        Add one or more tracks to a user’s playlist.
        https://developer.spotify.com/documentation/web-api/reference/playlists/add-tracks-to-playlist/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
            uris (list of Spotify URI strings):
                *Optional*. A list of the `Spotify track URIs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__ to
                add
            position (integer):
                Optional. The position to insert the tracks, a zero-based index. If omitted,
                the tracks will be appended to the playlist.
        """
        return self._post(url='/playlists/{playlist_id}/tracks'.format(playlist_id=playlist_id),
                          json_data=dict(uris=uris, position=position))

    def change_playlist_details(self, playlist_id, name=None, public=None, collaborative=None,
                                description=None):
        """
        Change a playlist’s name and public/private state. (The user must, of course, own the
        playlist.)
        https://developer.spotify.com/documentation/web-api/reference/playlists/change-playlist-details/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
            name (string):
                *Optional*. The new name for the playlist, for example ``"My New Playlist Title"``.
            public (Boolean):
                *Optional*. If ``true`` the playlist will be public, if ``false`` it will be
                private.
            collaborative (Boolean):
                *Optional*. If ``true`` , the playlist will become collaborative and other users
                will be able to modify the playlist in their Spotify client. *Note: You can only
                set ``collaborative`` to ``true`` on non-public playlists.*
            description (string):
                *Optional*. Value for playlist description as displayed in Spotify Clients and in
                the Web API.
        """
        self._ensure_scope('playlist-modify-', public=public)

        return self._put(url='/playlists/{playlist_id}'.format(playlist_id=playlist_id),
                         json_data=dict(name=name, public=public, collaborative=collaborative,
                                        description=description))

    def create_playlist(self, user_id, name, public=True, collaborative=False, description=None):
        """
        Create a playlist for a Spotify user. (The playlist will be empty until you add tracks.)
        https://developer.spotify.com/documentation/web-api/reference/playlists/create-playlist/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            user_id:
                The user’s `Spotify user ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__.
            name (string):
                *Required*. The name for the new playlist, for example ``"Your Coolest Playlist"``
                . This name does not need to be unique; a user may have several playlists with the
                same name.
            public (Boolean):
                *Optional*. Defaults to ``True`` . If ``true`` the playlist will be public, if
                ``False`` it will be private. To be able to create private playlists, the user must
                have granted the ``playlist-modify-private`` `scope
                <https://developer.spotify.com/documentation/general/guides/authorization-guide/#list-of-scopes>`__
                .
            collaborative (Boolean):
                *Optional*. Defaults to ``False`` . If ``true`` the playlist will be collaborative.
                Note that to create a collaborative playlist you must also set ``public`` to
                ``False`` . To create collaborative playlists you must have granted
                ``playlist-modify-private`` and ``playlist-modify-public`` `scopes
                <https://developer.spotify.com/documentation/general/guides/authorization-guide/#list-of-scopes>`__
                .
            description (string):
                *Optional*. value for playlist description as displayed in Spotify Clients and in
                the Web API.
        """
        self._ensure_scope('playlist-modify-', public=public)

        return self._post(url='/users/{user_id}/playlists'.format(user_id=user_id),
                          json_data=dict(name=name, public=public, collaborative=collaborative,
                                         description=description))

    def current_user_playlists(self, limit=20, offset=0):
        """
        Get a list of the playlists owned or followed by the current Spotify user.
        https://developer.spotify.com/documentation/web-api/reference/playlists/get-a-list-of-current-users-playlists/

        Relevant authorization scopes: playlist-read-private, playlist-read-collaborative

        Args:
            limit:
                *Optional*. The maximum number of playlists to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first playlist to return. Default: 0 (the first
                object). Maximum offset: 100.000. Use with ``limit`` to get the next set of
                playlists.
        """
        return self._get(url='/me/playlists', params=dict(limit=limit, offset=offset))

    def user_playlists(self, user_id, limit=20, offset=0):
        """
        Get a list of the playlists owned or followed by a Spotify user.
        https://developer.spotify.com/documentation/web-api/reference/playlists/get-list-users-playlists/

        Relevant authorization scopes: playlist-read-private, playlist-read-collaborative

        Args:
            user_id:
                The user’s `Spotify user ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__.
            limit:
                *Optional*. The maximum number of playlists to return. Default: 20. Minimum: 1.
                Maximum: 50.
            offset:
                *Optional*. The index of the first playlist to return. Default: 0 (the first
                object). Maximum offset: 100.000. Use with ``limit`` to get the next set of
                playlists.
        """
        return self._get(url='/users/{user_id}/playlists'.format(user_id=user_id),
                         params=dict(limit=limit, offset=offset))

    def playlist_cover_image(self, playlist_id):
        """
        Get the current image associated with a specific playlist.
        https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlist-cover/

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
        """
        return self._get(url='/playlists/{playlist_id}/images'.format(playlist_id=playlist_id))

    def playlist(self, playlist_id, fields=None, market=None):
        """
        Get a playlist owned by a Spotify user.
        https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlist/

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
            fields:
                *Optional*. Filters for the query: a comma-separated list of the fields to return.
                If omitted, all fields are returned. For example, to get just the playlist’s
                description and URI: ``fields=description,uri``. A dot separator can be used to
                specify non-reoccurring fields, while parentheses can be used to specify
                reoccurring fields within objects. For example, to get just the added date and user
                ID of the adder: ``fields="tracks.items(added_at,added_by.id)"``. Use multiple
                parentheses to drill down into nested objects, for example:
                ``fields="tracks.items(track(name,href,album(name,href)))"``. Fields can be excluded
                by enclosing them inside parenthesis starting with an exclamation mark, e.g.
                 ``(!field1,field2)``
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        return self._get(url='/playlists/{playlist_id}'.format(playlist_id=playlist_id),
                         params=dict(fields=fields, market=market))

    def playlist_tracks(self, playlist_id, fields=None, limit=100, offset=0, market=None):
        """
        Get full details of the tracks of a playlist owned by a Spotify user.
        https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlists-tracks/

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
            fields:
                *Optional*. Filters for the query: a comma-separated list of the fields to return.
                If omitted, all fields are returned. For example, to get just the total number of
                tracks and the request limit: ``fields=total,limit`` A dot separator can be used to
                specify non-reoccurring fields, while parentheses can be used to specify
                reoccurring fields within objects. For example, to get just the added date and user
                ID of the adder: ``fields=items(added_at,added_by.id)`` Use multiple parentheses to
                drill down into nested objects, for example:
                ``fields=items(track(name,href,album(name,href)))`` Fields can be excluded by
                prefixing them with an exclamation mark, for example:
                ``fields=items.track.album(!external_urls,images)``
            limit:
                *Optional*. The maximum number of tracks to return. Default: 100. Minimum: 1.
                Maximum: 100.
            offset:
                *Optional*. The index of the first track to return. Default: 0 (the first object).
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        return self._get(url='/playlists/{playlist_id}/tracks'.format(playlist_id=playlist_id),
                         params=dict(fields=fields, limit=limit, offset=offset, market=market))

    def remove_tracks_from_playlist(self, playlist_id):
        """
        Remove one or more tracks from a user’s playlist.
        https://developer.spotify.com/documentation/web-api/reference/playlists/remove-tracks-playlist/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
        """
        return self._delete(url='/playlists/{playlist_id}/tracks'.format(playlist_id=playlist_id))

    def reorder_playlist_tracks(self, playlist_id, range_start, insert_before, range_length=1,
                                snapshot_id=None):
        """
        Reorder a track or a group of tracks in a playlist.
        https://developer.spotify.com/documentation/web-api/reference/playlists/reorder-playlists-tracks/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
            range_start (integer):
                *Required*. The position of the first track to be reordered.
            insert_before (integer):
                *Required*. The position where the tracks should be inserted. To reorder the tracks
                to the end of the playlist, simply set *insert_before* to the position after the
                last track. Examples: To reorder the first track to the last position in a playlist
                with 10 tracks, set *range_start* to 0, and *insert_before* to 10. To reorder the
                last track in a playlist with 10 tracks to the start of the playlist, set
                *range_start* to 9, and *insert_before* to 0.
            range_length (integer):
                *Optional*. The amount of tracks to be reordered. Defaults to 1 if not set. The
                range of tracks to be reordered begins from the *range_start* position, and
                includes the *range_length* subsequent tracks. Example: To move the tracks at index
                9-10 to the start of the playlist, *range_start* is set to 9, and *range_length* is
                set to 2.
            snapshot_id (string):
                *Optional*. The playlist’s snapshot ID against which you want to make the changes.
        """
        return self._put(url='/playlists/{playlist_id}/tracks'.format(playlist_id=playlist_id),
                         json_data=dict(range_start=range_start, range_length=range_length,
                                        insert_before=insert_before, snapshot_id=snapshot_id))

    def replace_playlist_tracks(self, playlist_id, uris=None):
        """
        Replace all the tracks in a playlist, overwriting its existing tracks. This powerful
        request can be useful for replacing tracks, re-ordering existing tracks, or clearing the
        playlist.
        https://developer.spotify.com/documentation/web-api/reference/playlists/replace-playlists-tracks/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
            uris (list of Spotify URI strings):
                *Optional*. A list of the `Spotify track URIs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__ to
                set
        """
        return self._put(url='/playlists/{playlist_id}/tracks'.format(playlist_id=playlist_id),
                         json_data=dict(uris=uris))

    def upload_playlist_cover_image(self, playlist_id):
        """
        Replace the image used to represent a specific playlist.
        https://developer.spotify.com/documentation/web-api/reference/playlists/upload-custom-playlist-cover/

        Relevant authorization scopes: playlist-modify-public, playlist-modify-private

        Args:
            playlist_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the playlist.
        """
        return self._put(url='/playlists/{playlist_id}/images'.format(playlist_id=playlist_id),
                         content_type='image/jpeg')

    # **********************************************************************#
    #                              Search                                  #
    # **********************************************************************#
    def search(self, query, obj_type, market=None, limit=20, offset=0, include_external=None):
        """
        Get Spotify Catalog information about artists, albums, tracks or playlists that match a
        keyword string.
        https://developer.spotify.com/documentation/web-api/reference/search/search/

        Args:
            query:
                *Required*. Search `query
                <https://developer.spotify.com/#writing-a-query---guidelines>`__ keywords and
                optional field filters and operators. For example: ``query=roadhouse%20blues``.
            obj_type:
                *Required*. A comma-separated list of item types to search across. Valid types are:
                ``album`` , ``artist``, ``playlist``, and ``track``. Search results include hits
                from all the specified item types. For example:
                ``query=name:abacab&type=album,track``
                returns both albums **and** tracks with “abacab” included in their name.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                If a country code is specified, only artists, albums, and tracks with content that
                is playable in that market is returned. **Note**: - Playlist results are not
                affected by the market parameter. - If market is set to ``from_token``, and a valid
                access token is specified in the request header, only content playable in the
                country associated with the user account, is returned. - Users can view the country
                that is associated with their account in the `account settings
                <https://www.spotify.com/se/account/overview/>`__. A user must grant access to the
                ``user-read-private`` scope prior to when the access token is issued.
            limit:
                *Optional*. Maximum number of results to return. Default: 20 Minimum: 1 Maximum: 50
                **Note**: The limit is applied within each type, not on the total response_args. For
                example, if the limit value is 3 and the type is ``artist,album``, the response_args
                contains 3 artists and 3 albums.
            offset:
                *Optional*. The index of the first result to return. Default: 0 (the first result).
                Maximum offset (including limit): 10,000. Use with limit to get the next page of
                search results.
            include_external:
                *Optional*. Possible values: *audio* If *include_external=audio* is specified the
                response_args will include any relevant audio content that is hosted externally. By
                default external content is filtered out from responses.
        """
        return self._get(url='/search',
                         params=dict(q=query, type=obj_type, market=market, limit=limit,
                                     offset=offset, include_external=include_external))

    # **********************************************************************#
    #                              Tracks                                  #
    # **********************************************************************#
    def track_audio_analysis(self, track_id):
        """
        Get a detailed audio analysis for a single track identified by its unique Spotify ID.
        https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-analysis/

        Args:
            track_id:
                *Required*. The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the track.
        """
        return self._get(url='/audio-analysis/{id}'.format(id=track_id))

    def track_audio_features(self, track_id):
        """
        Get audio feature information for a single track identified by its unique Spotify ID.
        https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/
        https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/
        Args:
            track_id:
                *Required*. The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the track.
        """
        return self._get(url='/audio-features/{id}'.format(id=track_id))

    def tracks_audio_features(self, track_ids):
        """
        Get audio features for multiple tracks based on their Spotify IDs.
        https://developer.spotify.com/documentation/web-api/reference/tracks/get-several-audio-features/

        Args:
            track_ids:
                *Required*. A list of the `Spotify IDs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the tracks. Maximum: 100 IDs.
        """
        return self._get(url='/audio-features', params=dict(ids=track_ids))

    def tracks(self, ids, market=None):
        """
        Get Spotify catalog information for multiple tracks based on their Spotify IDs.
        https://developer.spotify.com/documentation/web-api/reference/tracks/get-several-tracks/

        Args:
            ids:
                *Required*. A list of the `Spotify IDs
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the tracks. Maximum: 50 IDs.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        return self._get(url='/tracks', params=dict(ids=ids, market=market))['tracks']

    def track(self, track_id, market=None):
        """
        Get Spotify catalog information for a single track identified by its unique Spotify ID.
        https://developer.spotify.com/documentation/web-api/reference/tracks/get-track/

        Args:
            track_id:
                The `Spotify ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__
                for the track.
            market:
                *Optional*. An `ISO 3166-1 alpha-2 country code
                <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`__ or the string ``from_token``.
                Provide this parameter if you want to apply `Track Relinking
                <https://developer.spotify.com/documentation/general/guides/track-relinking-guide/>`__.
        """
        return self._get(url='/tracks/{id}'.format(id=track_id), params=dict(market=market))

    def current_user(self):
        """
        Get detailed profile information about the current user (including the current user’s
        username).
        https://developer.spotify.com/documentation/web-api/reference/users-profile/get-current-users-profile/

        Relevant authorization scopes: user-read-email, user-read-private, user-read-birthdate
        """
        return self._get(url='/me')

    def me(self):
        """
        Get detailed profile information about the current user (including the current user’s
        username).
        https://developer.spotify.com/documentation/web-api/reference/users-profile/get-current-users-profile/

        Relevant authorization scopes: user-read-email, user-read-private, user-read-birthdate
        """
        return self._get(url='/me')

    def user_public_profile(self, user_id):
        """
        Get public profile information about a Spotify user.
        https://developer.spotify.com/documentation/web-api/reference/users-profile/get-users-profile/

        Args:
            user_id:
                The user’s `Spotify user ID
                <https://developer.spotify.com/documentation/web-api/#spotify-uris-and-ids>`__.
        """
        return self._get(url='/users/{user_id}'.format(user_id=user_id))
