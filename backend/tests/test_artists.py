from tests.conftest import INVALID_UUID


def test_create_artist_returns_id(client):
    response = client.post("/library/artist", params={"name": "Daft Punk"})

    assert response.status_code == 200
    assert len(response.text) == 32


def test_get_artists_lists_created_artists(client, make_artist):
    artist_id = make_artist(name="Daft Punk")

    response = client.get("/library/artists")

    assert response.status_code == 200
    assert {"id": artist_id, "name": "Daft Punk"} in response.json()


def test_get_artists_empty_when_none_created(client):
    response = client.get("/library/artists")

    assert response.status_code == 200
    assert response.json() == []


def test_get_artist_info_returns_artist_with_songs(client, make_artist, make_song):
    artist_id = make_artist(name="Daft Punk")
    song_id = make_song(artist_id, title="One More Time")

    response = client.get(f"/library/artist/{artist_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Daft Punk"
    assert body["songs"] == [
        {"id": song_id, "title": "One More Time", "artist": {"name": "Daft Punk"}}
    ]


def test_get_artist_info_not_found(client):
    response = client.get(f"/library/artist/{'a' * 32}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Artist not found"


def test_modify_artist_updates_name(client, make_artist):
    artist_id = make_artist(name="Old Name")

    response = client.patch(f"/library/artist/{artist_id}", json={"name": "New Name"})

    assert response.status_code == 200
    assert response.text == artist_id
    assert client.get(f"/library/artist/{artist_id}").json()["name"] == "New Name"


def test_modify_artist_no_changes_provided(client, make_artist):
    artist_id = make_artist()

    response = client.patch(f"/library/artist/{artist_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No changes were provided"


def test_modify_artist_not_found(client):
    response = client.patch(f"/library/artist/{'a' * 32}", json={"name": "Anyone"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Artist not found"


def test_delete_artist_success(client, make_artist):
    artist_id = make_artist()

    response = client.delete(f"/library/artist/{artist_id}")

    assert response.status_code == 200
    assert response.text == artist_id
    assert client.get(f"/library/artist/{artist_id}").status_code == 404


def test_delete_artist_not_found(client):
    response = client.delete(f"/library/artist/{'a' * 32}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Artist not found"


def test_delete_artist_with_songs_is_rejected(client, make_artist, make_song):
    artist_id = make_artist()
    song_id = make_song(artist_id)

    response = client.delete(f"/library/artist/{artist_id}")

    assert response.status_code == 403
    assert "still registered" in response.json()["detail"]
    assert client.get(f"/library/song/{song_id}").json() != 22


def test_get_artist_info_invalid_uuid_is_rejected(client):
    response = client.get(f"/library/artist/{INVALID_UUID}")

    assert response.status_code == 422
