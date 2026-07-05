from tests.conftest import INVALID_UUID


def test_create_song_returns_file_id_and_stores_upload(client, make_artist, fake_s3):
    artist_id = make_artist()

    response = client.post(
        "/library/song",
        params={"title": "One More Time", "artist_id": artist_id},
        files={"file": ("song.mp3", b"audio-bytes", "audio/mpeg")},
    )

    assert response.status_code == 200
    file_id = response.text
    assert len(file_id) == 32
    assert fake_s3.storage[file_id] == b"audio-bytes"


def test_create_song_with_unknown_artist_fails(client):
    response = client.post(
        "/library/song",
        params={"title": "Orphan Song", "artist_id": "a" * 32},
        files={"file": ("song.mp3", b"audio-bytes", "audio/mpeg")},
    )

    assert response.status_code == 500


def test_get_songs_lists_created_songs(client, make_artist, make_song):
    artist_id = make_artist(name="Daft Punk")
    song_id = make_song(artist_id, title="One More Time")

    response = client.get("/library/songs")

    assert response.status_code == 200
    assert {"id": song_id, "title": "One More Time", "artist": {"name": "Daft Punk"}} in response.json()


def test_get_song_info_returns_song_details(client, make_artist, make_song):
    artist_id = make_artist(name="Daft Punk")
    song_id = make_song(artist_id, title="One More Time")

    response = client.get(f"/library/song/{song_id}")

    assert response.status_code == 200
    assert response.json() == {
        "title": "One More Time",
        "artist": {"name": "Daft Punk"},
        "file_id": song_id,
    }


def test_get_song_info_not_found_returns_raw_error_code(client):
    # NOTE: unlike other GET-by-id routes, this endpoint does not translate the
    # service layer's "not found" sentinel into an HTTPException, so a
    # nonexistent song currently yields a 200 with a raw `22` body. This test
    # documents actual behavior rather than intended behavior.
    response = client.get(f"/library/song/{'a' * 32}")

    assert response.status_code == 200
    assert response.json() == 22


def test_modify_song_updates_title(client, make_artist, make_song):
    artist_id = make_artist()
    song_id = make_song(artist_id, title="Old Title")

    response = client.patch(f"/library/song/{song_id}", json={"title": "New Title"})

    assert response.status_code == 200
    assert response.text == song_id
    assert client.get(f"/library/song/{song_id}").json()["title"] == "New Title"


def test_modify_song_updates_artist(client, make_artist, make_song):
    artist_id = make_artist(name="Original Artist")
    other_artist_id = make_artist(name="New Artist")
    song_id = make_song(artist_id)

    response = client.patch(f"/library/song/{song_id}", json={"artist_id": other_artist_id})

    assert response.status_code == 200
    assert client.get(f"/library/song/{song_id}").json()["artist"]["name"] == "New Artist"


def test_modify_song_no_changes_provided(client, make_artist, make_song):
    artist_id = make_artist()
    song_id = make_song(artist_id)

    response = client.patch(f"/library/song/{song_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No changes were provided"


def test_modify_song_not_found(client):
    response = client.patch(f"/library/song/{'a' * 32}", json={"title": "Anything"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Song not found"


def test_modify_song_unknown_artist(client, make_artist, make_song):
    artist_id = make_artist()
    song_id = make_song(artist_id)

    response = client.patch(f"/library/song/{song_id}", json={"artist_id": "b" * 32})

    assert response.status_code == 404
    assert response.json()["detail"] == "Artist not found"


def test_delete_song_success_removes_song_and_resource(client, make_artist, make_song, fake_s3):
    artist_id = make_artist()
    song_id = make_song(artist_id)
    assert song_id in fake_s3.storage

    response = client.delete(f"/library/song/{song_id}")

    assert response.status_code == 200
    assert response.text == song_id
    assert song_id not in fake_s3.storage
    assert client.get(f"/library/song/{song_id}").json() == 22


def test_delete_song_not_found(client):
    response = client.delete(f"/library/song/{'a' * 32}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Song not found"


def test_create_song_invalid_artist_uuid_is_rejected(client):
    response = client.post(
        "/library/song",
        params={"title": "Song", "artist_id": INVALID_UUID},
        files={"file": ("song.mp3", b"audio-bytes", "audio/mpeg")},
    )

    assert response.status_code == 422


def test_get_song_info_invalid_uuid_is_rejected(client):
    response = client.get(f"/library/song/{INVALID_UUID}")

    assert response.status_code == 422
