from tests.conftest import INVALID_UUID


def test_create_playlist_returns_id(client):
    response = client.post("/library/playlist", params={"name": "Party Mix"})

    assert response.status_code == 200
    assert len(response.text) == 32


def test_get_playlists_lists_created_playlists(client, make_playlist):
    playlist_id = make_playlist(name="Party Mix")

    response = client.get("/library/playlists")

    assert response.status_code == 200
    assert {"id": playlist_id, "name": "Party Mix"} in response.json()


def test_get_playlist_info_empty(client, make_playlist):
    playlist_id = make_playlist(name="Party Mix")

    response = client.get(f"/library/playlist/{playlist_id}")

    assert response.status_code == 200
    assert response.json() == {"name": "Party Mix", "songs": []}


def test_get_playlist_info_not_found(client):
    response = client.get(f"/library/playlist/{'a' * 32}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Artist not found"  # NOTE: mislabeled in source


def test_modify_playlist_renames(client, make_playlist):
    playlist_id = make_playlist(name="Old Name")

    response = client.patch(f"/library/playlist/{playlist_id}", json={"name": "New Name"})

    assert response.status_code == 200
    assert client.get(f"/library/playlist/{playlist_id}").json()["name"] == "New Name"


def test_modify_playlist_adds_song_at_end(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    first_song = make_song(artist_id, title="First")
    second_song = make_song(artist_id, title="Second")

    client.patch(f"/library/playlist/{playlist_id}", json={"song_id": first_song})
    response = client.patch(f"/library/playlist/{playlist_id}", json={"song_id": second_song})

    assert response.status_code == 200
    songs = client.get(f"/library/playlist/{playlist_id}").json()["songs"]
    assert [s["title"] for s in songs] == ["First", "Second"]
    assert [s["position"] for s in songs] == [1, 2]


def test_modify_playlist_inserts_song_at_position(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    first_song = make_song(artist_id, title="First")
    second_song = make_song(artist_id, title="Second")
    third_song = make_song(artist_id, title="Inserted")

    client.patch(f"/library/playlist/{playlist_id}", json={"song_id": first_song})
    client.patch(f"/library/playlist/{playlist_id}", json={"song_id": second_song})
    response = client.patch(
        f"/library/playlist/{playlist_id}", json={"song_id": third_song, "position": 2}
    )

    assert response.status_code == 200
    songs = client.get(f"/library/playlist/{playlist_id}").json()["songs"]
    assert [s["title"] for s in songs] == ["First", "Inserted", "Second"]
    assert [s["position"] for s in songs] == [1, 2, 3]


def test_modify_playlist_removes_song(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    first_song = make_song(artist_id, title="First")
    second_song = make_song(artist_id, title="Second")
    client.patch(f"/library/playlist/{playlist_id}", json={"song_id": first_song})
    client.patch(f"/library/playlist/{playlist_id}", json={"song_id": second_song})

    response = client.patch(
        f"/library/playlist/{playlist_id}",
        json={"song_id": first_song, "remove_song": True},
    )

    assert response.status_code == 200
    songs = client.get(f"/library/playlist/{playlist_id}").json()["songs"]
    assert [s["title"] for s in songs] == ["Second"]
    assert songs[0]["position"] == 1


def test_modify_playlist_remove_song_not_in_playlist(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    song_id = make_song(artist_id)

    response = client.patch(
        f"/library/playlist/{playlist_id}",
        json={"song_id": song_id, "remove_song": True},
    )

    assert response.status_code == 404


def test_modify_playlist_no_changes_provided(client, make_playlist):
    playlist_id = make_playlist()

    response = client.patch(f"/library/playlist/{playlist_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No playlist changes were provided"


def test_modify_playlist_not_found(client):
    response = client.patch(f"/library/playlist/{'a' * 32}", json={"name": "Anything"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Playlist not found"


def test_modify_playlist_unknown_song(client, make_playlist):
    playlist_id = make_playlist()

    response = client.patch(
        f"/library/playlist/{playlist_id}", json={"song_id": "b" * 32}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Song not found"


def test_delete_playlist_success(client, make_playlist):
    playlist_id = make_playlist()

    response = client.delete(f"/library/playlist/{playlist_id}")

    assert response.status_code == 200
    assert response.text == playlist_id
    assert client.get(f"/library/playlist/{playlist_id}").status_code == 404


def test_delete_playlist_not_found(client):
    response = client.delete(f"/library/playlist/{'a' * 32}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Playlist not found"


def test_modify_playlist_invalid_song_id_uuid_is_rejected(client, make_playlist):
    playlist_id = make_playlist()

    response = client.patch(
        f"/library/playlist/{playlist_id}", json={"song_id": INVALID_UUID}
    )

    assert response.status_code == 422
