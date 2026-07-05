import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app import app
from models.sql import Base
from services.sql import getDB
from services.s3 import getS3Client


class FakeStreamingBody:
    """Mimics the subset of a boto3 StreamingBody used by the /stream endpoint."""

    def __init__(self, data: bytes):
        self._data = data

    async def iter_chunks(self):
        yield self._data


class FakeS3Client:
    """In-memory stand-in for the aioboto3 S3 client, keyed by object key."""

    def __init__(self):
        self.storage: dict[str, bytes] = {}

    async def upload_fileobj(self, file_obj, Bucket, Key):
        self.storage[Key] = file_obj.read()

    async def delete_object(self, Bucket, Key):
        self.storage.pop(Key, None)

    async def get_object(self, Bucket, Key):
        if Key not in self.storage:
            raise KeyError(f"The specified key {Key} does not exist.")
        return {"Body": FakeStreamingBody(self.storage[Key])}


@pytest.fixture()
def fake_s3():
    return FakeS3Client()


@pytest.fixture()
def client(fake_s3):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def override_get_s3():
        yield fake_s3

    app.dependency_overrides[getDB] = override_get_db
    app.dependency_overrides[getS3Client] = override_get_s3

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def make_artist(client):
    def _make_artist(name: str = "Test Artist"):
        response = client.post("/library/artist", params={"name": name})
        assert response.status_code == 200
        return response.text
    return _make_artist


@pytest.fixture()
def make_song(client):
    def _make_song(artist_id: str, title: str = "Test Song", content: bytes = b"fake-audio-bytes"):
        response = client.post(
            "/library/song",
            params={"title": title, "artist_id": artist_id},
            files={"file": ("test.mp3", content, "audio/mpeg")},
        )
        assert response.status_code == 200
        return response.text
    return _make_song


@pytest.fixture()
def make_playlist(client):
    def _make_playlist(name: str = "Test Playlist"):
        response = client.post("/library/playlist", params={"name": name})
        assert response.status_code == 200
        return response.text
    return _make_playlist


INVALID_UUID = "not-a-valid-uuid"
