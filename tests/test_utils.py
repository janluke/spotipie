import pytest

from spotipie.exceptions import ResourceTypeMismatch
from spotipie.utils import RESOURCE_TYPES, ResourceInfo, get_id


@pytest.mark.parametrize(
    'obj_type', RESOURCE_TYPES
)
def test_resource_info_from_uri(obj_type):
    uri = ResourceInfo.from_uri('spotify:{}:1i6N76fftMZhijOzFQ5ZtL'.format(obj_type))
    assert uri == ResourceInfo(obj_type, '1i6N76fftMZhijOzFQ5ZtL')


def test_resource_info_from_legacy_playlist_uri():
    uri = ResourceInfo.from_uri('spotify:user:spotify:playlist:1i6N76fftMZhijOzFQ5ZtL')
    assert uri == ResourceInfo('playlist', '1i6N76fftMZhijOzFQ5ZtL', 'spotify')


@pytest.mark.parametrize(
    'uri, case', [
        ('spotify:something:1i6N76fftMZhijOzFQ5ZtL', 'invalid object type'),
        ('spotify:track:ciao?123dsanoij123.--sdfke',  'invalid object id'),
        ('spotify:user:spotify:track:dsadsadsadasd', 'owner_id for non-playlist object'),
        ('spotify:user:', 'missing fields'),
        ('spotify:user:ciao:track:aasdddfsdfadf:something', 'too many fields')
    ])
def test_resource_info_from_uri_raises(uri, case):
    with pytest.raises(ValueError):
        ResourceInfo.from_uri(uri)


@pytest.mark.parametrize(
    'url', [
        'https://open.spotify.com/playlist/4Z8bvNgj0iTiBMmFakQMgN',
        'https://open.spotify.com/user/spotify/playlist/4Z8bvNgj0iTiBMmFakQMgN'
    ])
def test_from_url_is_the_inverse_of_to_url(url):
    assert ResourceInfo.from_url(url).url == url


@pytest.mark.parametrize(
    'uri', [
        'spotify:playlist:4Z8bvNgj0iTiBMmFakQMgN',
        'spotify:user:spotify:playlist:4Z8bvNgj0iTiBMmFakQMgN'
    ])
def test_from_uri_is_the_inverse_of_to_uri(uri):
    assert ResourceInfo.from_uri(uri).uri == uri


def test_get_id_from_id():
    assert get_id('1i6N76fftMZhijOzFQ5ZtL') == '1i6N76fftMZhijOzFQ5ZtL'


@pytest.mark.parametrize(
    'uri', (
        'spotify:playlist:1i6N76fftMZhijOzFQ5ZtL',
        'spotify:user:spotify:playlist:1i6N76fftMZhijOzFQ5ZtL',
    ))
def test_get_id_from_uri(uri):
    assert get_id(uri) == '1i6N76fftMZhijOzFQ5ZtL'


@pytest.mark.parametrize(
    'url', (
        'https://open.spotify.com/playlist/4Z8bvNgj0iTiBMmFakQMgN',
        'https://open.spotify.com/user/sbobyx/playlist/4Z8bvNgj0iTiBMmFakQMgN'
    ))
def test_get_id_from_url(url):
    assert get_id(url) == '4Z8bvNgj0iTiBMmFakQMgN'


def test_get_id_raises_for_type_mismatch():
    with pytest.raises(ResourceTypeMismatch):
        get_id('spotify:playlist:1i6N76fftMZhijOzFQ5ZtL', 'track')
