def test_stream_audio_returns_uploaded_bytes(client, make_artist, make_song):
    artist_id = make_artist()
    song_id = make_song(artist_id, content=b"the-audio-payload")

    response = client.get(f"/library/stream/{song_id}")

    assert response.status_code == 200
    assert response.content == b"the-audio-payload"
    assert response.headers["content-type"] == "audio/mpeg"


def test_stream_audio_unknown_key_returns_500(client):
    response = client.get(f"/library/stream/{'a' * 32}")

    assert response.status_code == 500


def test_stream_audio_invalid_uuid_is_rejected(client):
    response = client.get("/library/stream/not-a-valid-uuid")

    assert response.status_code == 422
