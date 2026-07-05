def test_add_song_to_playlist(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    song_id = make_song(artist_id)

    response = client.get(f"/library/add/{playlist_id}", params={"song_id": song_id})

    assert response.status_code == 200
    assert response.json() == {"playlist_id": playlist_id, "song_id": song_id}
    songs = client.get(f"/library/playlist/{playlist_id}").json()["songs"]
    assert songs[0]["s3_hash"] == song_id


def test_add_song_to_playlist_with_position(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    first_song = make_song(artist_id, title="First")
    second_song = make_song(artist_id, title="Second")
    client.get(f"/library/add/{playlist_id}", params={"song_id": first_song})

    response = client.get(
        f"/library/add/{playlist_id}", params={"song_id": second_song, "position": 1}
    )

    assert response.status_code == 200
    songs = client.get(f"/library/playlist/{playlist_id}").json()["songs"]
    assert [s["title"] for s in songs] == ["Second", "First"]


def test_add_song_to_playlist_unknown_playlist(client, make_artist, make_song):
    artist_id = make_artist()
    song_id = make_song(artist_id)

    response = client.get(f"/library/add/{'a' * 32}", params={"song_id": song_id})

    assert response.status_code == 404


def test_add_song_to_playlist_unknown_song(client, make_playlist):
    playlist_id = make_playlist()

    response = client.get(f"/library/add/{playlist_id}", params={"song_id": "b" * 32})

    assert response.status_code == 404


def test_remove_song_from_playlist(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    song_id = make_song(artist_id)
    client.get(f"/library/add/{playlist_id}", params={"song_id": song_id})

    response = client.get(
        f"/library/remove/{playlist_id}", params={"song_id": song_id, "position": 1}
    )

    assert response.status_code == 200
    assert response.json() == {"playlist_id": playlist_id, "song_id": song_id}
    assert client.get(f"/library/playlist/{playlist_id}").json()["songs"] == []


def test_remove_song_from_playlist_not_found(client, make_playlist):
    playlist_id = make_playlist()

    response = client.get(
        f"/library/remove/{playlist_id}", params={"song_id": "b" * 32, "position": 1}
    )

    assert response.status_code == 404


def test_remove_song_from_playlist_requires_position(client, make_playlist, make_artist, make_song):
    playlist_id = make_playlist()
    artist_id = make_artist()
    song_id = make_song(artist_id)
    client.get(f"/library/add/{playlist_id}", params={"song_id": song_id})

    response = client.get(f"/library/remove/{playlist_id}", params={"song_id": song_id})

    assert response.status_code == 422
