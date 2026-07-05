import pytest

from tests.conftest import INVALID_UUID


@pytest.mark.parametrize(
    "method,path",
    [
        ("delete", f"/library/artist/{INVALID_UUID}"),
        ("patch", f"/library/artist/{INVALID_UUID}"),
        ("get", f"/library/playlist/{INVALID_UUID}"),
        ("delete", f"/library/playlist/{INVALID_UUID}"),
        ("patch", f"/library/playlist/{INVALID_UUID}"),
        ("get", f"/library/add/{INVALID_UUID}"),
        ("get", f"/library/remove/{INVALID_UUID}"),
    ],
)
def test_invalid_uuid_path_param_is_rejected(client, method, path):
    kwargs = {"json": {}} if method == "patch" else {}
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 422


def test_add_song_to_playlist_invalid_song_id_query_is_rejected(client, make_playlist):
    playlist_id = make_playlist()

    response = client.get(f"/library/add/{playlist_id}", params={"song_id": INVALID_UUID})

    assert response.status_code == 422


def test_remove_song_from_playlist_invalid_song_id_query_is_rejected(client, make_playlist):
    playlist_id = make_playlist()

    response = client.get(
        f"/library/remove/{playlist_id}",
        params={"song_id": INVALID_UUID, "position": 1},
    )

    assert response.status_code == 422
