import logging
import uuid
from typing import Annotated
from fastapi import APIRouter, UploadFile, Response, HTTPException, Depends, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from services.sql import getDB
from services.sql.library import newSong, newArtist, newPlaylist, deleteSong, deleteArtist, deletePlaylist, modifySong, modifyPlaylist, modifyArtist, getPlaylist, getSong, getSongs, getArtist, getArtists, getPlaylists, addSongToPlaylist, removeSongFromPlaylist, newResource, deleteResource
from services.s3 import getS3Client

logger = logging.getLogger()
router = APIRouter()

UUID_HEX_PATTERN = r"^[0-9a-fA-F]{32}$"

UUIDPath = Annotated[str, Path(pattern=UUID_HEX_PATTERN, description="32-character hex UUID")]
UUIDQuery = Annotated[str, Query(pattern=UUID_HEX_PATTERN, description="32-character hex UUID")]
UUIDField = Annotated[str, Field(pattern=UUID_HEX_PATTERN, description="32-character hex UUID")]


class ArtistPatch(BaseModel):
    name: str | None = None


class SongPatch(BaseModel):
    title: str | None = None
    artist_id: str | None = None


class PlaylistPatch(BaseModel):
    name: str | None = None
    song_id: UUIDField | None = None
    position: int | None = None
    remove_song: bool = False


# Artist-specific routes
@router.get('/artists')
def get_artists(db: Session = Depends(getDB)):
    return getArtists(db)


@router.get('/artist/{artist_id}')
def get_artist_info(artist_id: UUIDPath, db: Session = Depends(getDB)):
    res = getArtist(db, artist_id)
    if res == 22:
        raise HTTPException(404, "Artist not found")
    return res


@router.post('/artist')
def create_artist(name: str, db: Session = Depends(getDB)):
    artist_id = uuid.uuid4().hex
    res = newArtist(db, name, artist_id)
    
    if res != 0:
        raise HTTPException(500, "Error while adding artist")
    return Response(artist_id) 


@router.delete("/artist/{artist_id}")
def delete_artist(artist_id: UUIDPath, db: Session = Depends(getDB)):
    res = deleteArtist(db, artist_id)
    if res == 23:
        raise HTTPException(403, "Artist has song(s) still registered. Please remove every song associated before removing")
    if res == 22:
        raise HTTPException(404, "Artist not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    return Response(artist_id)


@router.patch("/artist/{artist_id}")
def modify_artist(artist_id: UUIDPath, patch: ArtistPatch, db: Session = Depends(getDB)):
    if patch.name is None:
        raise HTTPException(400, "No changes were provided")

    res = modifyArtist(
        db,
        artist_id,
        name=patch.name
    )
    if res == 22:
        raise HTTPException(404, "Artist not found")
    if res == 1:
        raise HTTPException(500, "Modification failed")

    return Response(artist_id)


# Song-specific routes
@router.get("/songs")
def get_songs(db: Session = Depends(getDB)):
    return getSongs(db)


@router.get("/song/{song_id}")
def get_song_info(song_id: UUIDPath, db: Session = Depends(getDB)):
    return getSong(db, song_id)


@router.post("/song")
async def create_new_song(
    title: str,
    artist_id: UUIDQuery,
    file: UploadFile,
    s3 = Depends(getS3Client),
    db: Session = Depends(getDB)
):
    file_key = uuid.uuid4().hex
    try_count = 0
    while (res := await newResource(db, s3, file_key, file)) == 21 and try_count <= 10:
        logger.warning("New UUID already exists in S3! Trying again...")
        file_key = uuid.uuid4().hex
        try_count = try_count + 1
    if try_count >= 10:
        raise HTTPException(500, "UUID generation failed")
    if res == 2:
        raise HTTPException(500, "Upload failed")
    if res == 1:
        raise HTTPException(500, "Error while creating resource")

    res = newSong(db, title, artist_id, file_key)
    if (res != 0):
        raise HTTPException(500, "Cannot register song to database. Nothing was saved!")
    
    return Response(file_key)


@router.delete("/song/{song_id}")
async def delete_song(song_id: UUIDPath, s3 = Depends(getS3Client), db: Session = Depends(getDB)):
    res = deleteSong(db, song_id)
    if res == 22:
        raise HTTPException(404, "Song not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    if res == 0:
        res = await deleteResource(db, s3, song_id)
        if res == 1:
            raise HTTPException(500, "Removal failed")
        return Response(song_id)


@router.patch("/song/{song_id}")
def modify_song(song_id: UUIDPath, patch: SongPatch, db: Session = Depends(getDB)):
    if patch.title is None and patch.artist_id is None:
        raise HTTPException(400, "No changes were provided")

    res = modifySong(
        db,
        song_id,
        title=patch.title,
        artist_id=patch.artist_id
    )
    if res == 22:
        raise HTTPException(404, "Song not found")
    if res == 221:
        raise HTTPException(404, "Artist not found")
    if res == 1:
        raise HTTPException(500, "Modification failed")

    return Response(song_id)


# Playlist-specific routes
@router.get("/playlists")
def get_playlists(db: Session = Depends(getDB)):
    return getPlaylists(db)


@router.get("/playlist/{playlist_id}")
def get_playlist_info(playlist_id: UUIDPath, db: Session = Depends(getDB)):
    res = getPlaylist(db, playlist_id)
    if res == 22:
        raise HTTPException(404, "Artist not found")
    return res


@router.post("/playlist")
def create_new_playlist(name: str, db: Session = Depends(getDB)):
    playlist_id = uuid.uuid4().hex
    res = newPlaylist(db, name, playlist_id)

    if res != 0:
        raise HTTPException(500, "Error while adding artist")
    return Response(playlist_id)


@router.delete("/playlist/{playlist_id}")
def delete_playlist(playlist_id: UUIDPath, db: Session = Depends(getDB)):
    res = deletePlaylist(db, playlist_id)
    if res == 22:
        raise HTTPException(404, "Playlist not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    return Response(playlist_id)


@router.patch("/playlist/{playlist_id}")
def modify_playlist(playlist_id: UUIDPath, patch: PlaylistPatch, db: Session = Depends(getDB)):
    if patch.name is None and patch.song_id is None:
        raise HTTPException(400, "No playlist changes were provided")

    res = modifyPlaylist(
        db,
        playlist_id,
        name=patch.name,
        song_uuid=patch.song_id,
        position=patch.position,
        remove_song=patch.remove_song,
    )
    if res == 22:
        raise HTTPException(404, "Playlist not found")
    if res == 221:
        raise HTTPException(404, "Song not found")
    if res == 1:
        raise HTTPException(500, "Modification failed")

    return Response(playlist_id)



@router.get("/add/{playlist_id}", deprecated=True)
def add_song_to_playlist(playlist_id: UUIDPath, song_id: UUIDQuery, position: int | None = None, db: Session = Depends(getDB)):
    res = addSongToPlaylist(db, song_id, playlist_id, position)
    if res == 22:
        raise HTTPException(404, "Song or playlist not found")
    if res == 1:
        raise HTTPException(500, "Addition failed")
    return {"playlist_id": playlist_id, "song_id": song_id}

    
@router.get("/remove/{playlist_id}", deprecated=True)
def remove_song_from_playlist(playlist_id: UUIDPath, song_id: UUIDQuery, position: int, db: Session = Depends(getDB)):
    res = removeSongFromPlaylist(db, song_id, playlist_id, position)
    if res == 22:
        raise HTTPException(404, "Song or playlist not found")
    if res == 1:
        raise HTTPException(500, "Removal failed")
    return {"playlist_id": playlist_id, "song_id": song_id}


# Stream-specific routes
@router.get("/stream/{file_key}")
async def stream_audio(file_key: UUIDPath, s3 = Depends(getS3Client)):
    try:
        obj = await s3.get_object(Bucket='musikii-dev', Key=file_key)
        async def loop():
            async for chunk in obj["Body"].iter_chunks():
                yield chunk
        return StreamingResponse(loop(), media_type="audio/mpeg", status_code=200)
    except Exception as e:
        raise HTTPException(500, detail=str(e))