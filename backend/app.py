import uuid
import logging
import uvicorn
from fastapi import FastAPI, UploadFile, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
import aioboto3

from models.sql import initializeDB
from services.sql import newSong, newArtist, newPlaylist, deleteSong, deleteArtist, deletePlaylist, addSongToPlaylist, removeSongFromPlaylist, getPlaylist, getSongInfo, getSongs
from services.s3 import newFile, removeFile, getS3Client
from services.redis import redis_client
# APP SETUP

logger = logging.getLogger()
app = FastAPI()

sql_engine = create_engine(
    "sqlite:///dev.sqlite",
    connect_args={"check_same_thread": False}
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # We only want to run this if the engine is actually SQLite
    if type(dbapi_connection) is __import__("sqlite3").Connection:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

initializeDB(sql_engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sql_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

aws = aioboto3.Session()

# ENDPOINTS

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post('/new/artist')
def make_new_artist(name: str, db: Session = Depends(get_db)):
    artist_id = uuid.uuid4().hex
    res = newArtist(db, name, artist_id)
    
    if res != 0:
        raise HTTPException(500, "Error while adding artist")
    return Response(artist_id) 

@app.post("/new/song")
async def make_new_song(
    title: str, 
    artist_id: str, 
    file: UploadFile, 
    s3 = Depends(getS3Client),
    db: Session = Depends(get_db)
):
    file_key = uuid.uuid4().hex
    while True:
        try:
            await s3.get_object(Bucket='musikii-dev', Key=file_key)
            logger.warning("New UUID already exists in S3! Trying again...")
            file_key = uuid.uuid4().hex
        except Exception:
            break
    
    res = newSong(db, title, artist_id, file_key)
    if (res != 0):
        raise HTTPException(500, "Cannot register song to database. Nothing was saved!")
    
    res = await newFile(s3, file, file_key)
    if (res != 0):
        raise HTTPException(500, "Upload failed")
    
    return Response(file_key)

@app.post("/new/playlist")
def make_new_playlist(name: str, db: Session = Depends(get_db)):
    playlist_id = uuid.uuid4().hex
    res = newPlaylist(db, name, playlist_id)

    if res != 0:
        raise HTTPException(500, "Error while adding artist")
    return Response(playlist_id)
    
@app.post("/remove/artist")
def delete_artist(id: str, db: Session = Depends(get_db)):
    res = deleteArtist(db, id)
    if res == 23:
        raise HTTPException(403, "Artist has song(s) still registered. Please remove every song associated before removing")
    if res == 22:
        raise HTTPException(404, "Artist not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    return Response(id)

@app.post("/remove/song")
async def delete_song(id: str, s3 = Depends(getS3Client), db: Session = Depends(get_db)):
    res = deleteSong(db, id)
    if res == 22:
        raise HTTPException(404, "Song not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    if res == 0:
        res = await removeFile(s3, id)
        if res == 1:
            raise HTTPException(500, "Removal failed")
        return Response(id)
    
@app.post("/remove/playlist")
def delete_playlist(id: str, db: Session = Depends(get_db)):
    res = deletePlaylist(db, id)
    if res == 22:
        raise HTTPException(404, "Playlist not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    return Response(id)

@app.get("/add/{playlist_id}")
def add_song_to_playlist(playlist_id: str, song_id: str, position: int | None = None, db: Session = Depends(get_db)):
    res = addSongToPlaylist(db, song_id, playlist_id, position)
    if res == 22:
        raise HTTPException(404, "Song or playlist not found")
    if res == 1:
        raise HTTPException(500, "Addition failed")
    return {"playlist_id": playlist_id, "song_id": song_id}
    
@app.get("/remove/{playlist_id}")
def remove_song_to_playlist(playlist_id: str, song_id: str, position: int, db: Session = Depends(get_db)):
    res = removeSongFromPlaylist(db, song_id, playlist_id, position)
    if res == 22:
        raise HTTPException(404, "Song or playlist not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    return {"playlist_id": playlist_id, "song_id": song_id}

@app.get("/get/songs")
def get_songs(db: Session = Depends(get_db)):
    return getSongs(db)

@app.get("/get/song/{id}")
def get_song_info(id: str, db: Session = Depends(get_db)):
    return getSongInfo(db, id)

@app.get("/get/playlist/{id}")
def get_playlist_info(id: str, db: Session = Depends(get_db)):
    return getPlaylist(db, id)

@app.get("/stream/{file_key}")
async def stream_audio(file_key: str, s3 = Depends(getS3Client)):
    try:
        obj = await s3.get_object(Bucket='musikii-dev', Key=file_key)
        async def loop():
            async for chunk in obj["Body"].iter_chunks():
                yield chunk
        return StreamingResponse(loop(), media_type="audio/mpeg", status_code=200)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)