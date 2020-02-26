import pytest

from spotipie import Spotify
from spotipie.auth import ClientCredentialsSession, Credentials
from spotipie.utils import ResourceInfo

TRACK_INFO = ResourceInfo('track', '3Fcfwhm8oRrBvBZ8KGhtea')
ALBUM_INFO = ResourceInfo('album', '66nX0SGMQ7DrGiMrZlMkqS')
ARTIST_INFO = ResourceInfo('artist', '7ENzCHnmJUr20nUjoZ0zZ1')
PLAYLIST_INFO = ResourceInfo('playlist', '37i9dQZF1DWWEJlAGA9gs0')
USER_INFO = ResourceInfo('user', 'spotify')

RESOURCES_INFO = [TRACK_INFO, ALBUM_INFO, ARTIST_INFO, PLAYLIST_INFO, USER_INFO]


@pytest.fixture(scope='module')
def client():
    client_id, client_secret, _ = Credentials.from_environment('SPOTIFY')
    sess = ClientCredentialsSession(client_id, client_secret)
    sess.fetch_token()
    return Spotify(sess)


@pytest.mark.parametrize(
    'resource', RESOURCES_INFO, ids=[res.type for res in RESOURCES_INFO])
def test_get(client, resource):
    data = client.get(resource.uri)
    assert data['type'] == resource.type
    assert data['id'] == resource.id


def test_tracks(client):
    tracks = client.tracks(['3Fcfwhm8oRrBvBZ8KGhtea', '0aWMVrwxPNYkKmFthzmpRi'])
    assert len(tracks) == 2
    assert tracks[0]['type'] == tracks[1]['type'] == 'track'
    assert tracks[0]['id'] == '3Fcfwhm8oRrBvBZ8KGhtea'
    assert tracks[1]['id'] == '0aWMVrwxPNYkKmFthzmpRi'
    assert tracks[1]['name'] == 'Blue in Green'


def test_audio_features(client):
    features = client.track_audio_features('3Fcfwhm8oRrBvBZ8KGhtea')
    assert features['type'] == 'audio_features'
    assert 'acousticness' in features
    assert 'danceability' in features


def test_categories(client):
    categories = client.categories(limit=10, offset=5)
    assert categories['limit'] == 10
    assert categories['offset'] == 5


def test_recommendation(client):
    r = client.recommendations(limit=10, seed_artists=['7ENzCHnmJUr20nUjoZ0zZ1'],
                               max_instrumentalness=0.5, min_danceability=0.4)
    assert 'tracks' in r
    assert 'seeds' in r
