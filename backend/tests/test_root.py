def test_root_welcome_message(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Musikii API! Access is controlled beyond this endpoint."
    }
