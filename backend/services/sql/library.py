import logging
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.functions import ReturnTypeFromArgs
from fastapi import UploadFile
from models.sql import Resource, Song, Artist, Playlist, PlaylistSongLink
from services.s3 import newFile, removeFile

logger = logging.getLogger()
class unaccent(ReturnTypeFromArgs):
    pass

# Artists-related queries
def getArtists(q: str, session: Session):
    if q != "":
        if session.connection().engine.dialect.name == "postgresql":
            query = select(Artist).where(
                func.unaccent(Artist.name).icontains(q)
            )
        else:
            query = select(Artist).where(Artist.name.icontains(q))

    else:
        query = select(Artist)
    artists = session.execute(query).scalars().all()

    result = []
    for artist in artists:
        result.append({
            'id': artist.id,
            'name': artist.name
        })
    return result


def getArtist(session: Session, uuid: str):
    query = select(Artist).where(Artist.id == uuid)
    artist = session.execute(query).scalar_one_or_none()
    if not artist:
        return 22

    result = {
        'name': artist.name,
        'songs': []
    }
    for song in artist.songs:
        result['songs'].append({
            'id': song.id,
            'title': song.title,
            'artist': {'name': song.artist.name}
        })

    return result


def newArtist(session: Session, name: str, uuid: str) -> int:
    try:
        if session.get(Artist, uuid):
            return 21
        
        new_artist = Artist(id=uuid, name=name)
        session.add(new_artist)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while adding new artist : {e}")
        return 1


def deleteArtist(session: Session, uuid: str) -> int:
    try:
        artist = session.get(Artist, uuid)
        if not artist:
            logger.warning(f"Tried to remove non-existant artist with UUID : {uuid}")
            return 22

        if artist.songs:
            logger.warning(f"Tried to remove artist with song(s) still registered : {uuid}")
            return 23

        session.delete(artist)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while removing artist : {e}")
        return 1


def modifyArtist(session: Session, uuid: str, name: str | None) -> int:
    try:
        artist = session.get(Artist, uuid)
        if not artist:
            logger.warning(f"Tried to modify non-existant artist with UUID: {uuid}")
            return 22

        if name is not None:
            artist.name = name
            
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while modifying artist : {e}")
        return 1


# Resource-related queries
async def newResource(session: Session, s3, uuid: str, file: UploadFile):
    try:
        query = select(Resource).where(Resource.id.like("%" + uuid))
        if session.execute(query).scalar_one_or_none():
            return 21

        new_resource = Resource(id=uuid, uploaded=False)
        session.add(new_resource)
        session.commit()

        if await newFile(s3, file, uuid) != 0:
            return 2
        new_resource.uploaded = True
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while creating new resource : {e}")
        return 1


async def deleteResource(session: Session, s3, uuid: str):
    try:
        query = select(Resource).where(Resource.id.like("%" + uuid))
        if not (resource := session.execute(query).scalar_one_or_none()):
            return 21

        if await removeFile(s3, resource.id) != 0:
            return 2
        session.delete(resource)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while deleting resource {uuid}: {e}")
        return 1


# Songs-related queries
def getSongs(session: Session):
    query = select(Song).options(joinedload(Song.artist))
    songs = session.execute(query).scalars().all()

    result = []
    for song in songs:
        if not song.artist:
            return 23
        result.append({
            'id': song.id,
            'title': song.title,
            'artist': {'name': song.artist.name}
        })
    return result


def getSong(session: Session, uuid: str):
    query = select(Song).options(joinedload(Song.artist)).where(Song.id == uuid)
    song = session.execute(query).scalar_one_or_none()
    if not song:
        return 22
    if not song.artist:
        return 23
    
    return {
        'title': song.title,
        'artist': {'name': song.artist.name},
        'file_id': song.resource.id
    }


def newSong(session: Session, title: str, artist_id: str, uuid: str) -> int:
    try:
        if not session.get(Artist, artist_id):
            return 221
        if session.get(Song, uuid):
            return 21
        
        new_song = Song(id=uuid, title=title, artist_id=artist_id, resource_id=uuid)
        session.add(new_song)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while adding new song : {e}")
        return 1


def deleteSong(session: Session, uuid: str) -> int:
    try:
        song = session.get(Song, uuid)
        if not song:
            logger.warning(f"Tried to remove non-existant song with UUID : {uuid}")
            return 22
        
        session.delete(song)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while removing song : {e}")
        return 1


def modifySong(session: Session, uuid: str, title: str | None, artist_id: str | None) -> int:
    try:
        song = session.get(Song, uuid)
        if not song:
            logger.warning(f"Tried to modify non-existant song with UUID: {uuid}")
            return 22

        if title is not None:
            song.title = title

        if artist_id is not None:
            artist = session.get(Artist, artist_id)
            if not artist:
                logger.warning(f"Tried to modify song with non-existant artist UUID: {uuid}")
                return 221
            song.artist = artist
            
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while modifying song : {e}")
        return 1


# Playlist-related queries
def getPlaylists(session: Session):
    query = select(Playlist)
    playlists = session.execute(query).scalars().all()

    result = []
    for playlist in playlists:
        result.append({
            'id': playlist.id,
            'name': playlist.name
        })

    return result


def getPlaylist(session: Session, uuid: str):
    playlist = session.get(Playlist, uuid)
    if not playlist:
        logger.warning(f"Tried to query non-existant playlist with UUID : {uuid}")
        return 22
    query = (select(PlaylistSongLink)
                .where(PlaylistSongLink.playlist == playlist)
                .order_by(PlaylistSongLink.track_position)
                .options(joinedload(PlaylistSongLink.song).joinedload(Song.artist)))
    links = session.execute(query).scalars().all()

    result = {"name": playlist.name, "songs": []}
    for link in links:
        result["songs"].append({
            'position': link.track_position,
            'title': link.song.title,
            'artist': link.song.artist.name,
            's3_hash': link.song.id
        })
    return result


def newPlaylist(session: Session, name: str, uuid: str) -> int:
    try:
        if session.get(Playlist, uuid):
            return 21
        
        new_playlist = Playlist(id=uuid, name=name)
        session.add(new_playlist)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while adding new playlist : {e}")
        return 1

    
def deletePlaylist(session: Session, uuid: str) -> int:
    try:
        playlist = session.get(Playlist, uuid)
        if not playlist:
            logger.warning(f"Tried to remove non-existant playlist with UUID : {uuid}")
            return 22
        
        session.delete(playlist)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while removing playlist : {e}")
        return 1


def modifyPlaylist(
    session: Session,
    uuid: str,
    name: str | None = None,
    song_uuid: str | None = None,
    position: int | None = None,
    remove_song: bool = False,
) -> int:
    try:
        playlist = session.get(Playlist, uuid)
        if not playlist:
            logger.warning(f"Tried to modify non-existant playlist with UUID : {uuid}")
            return 22

        if name is not None:
            playlist.name = name

        if song_uuid is not None:
            song = session.get(Song, song_uuid)
            if not song:
                logger.warning(f"Tried to modify playlist with non-existant song UUID : {song_uuid}")
                return 221

            if remove_song:
                query = select(PlaylistSongLink).where(
                    PlaylistSongLink.playlist_id == uuid,
                    PlaylistSongLink.song_id == song_uuid,
                )
                if position is not None:
                    query = query.where(PlaylistSongLink.track_position == position)
                else:
                    query = query.order_by(PlaylistSongLink.track_position)

                link = session.execute(query).scalars().first()
                if not link:
                    return 22

                remove_position = link.track_position
                session.delete(link)

                query = (
                    update(PlaylistSongLink)
                    .where(PlaylistSongLink.playlist_id == uuid)
                    .where(PlaylistSongLink.track_position > remove_position)
                    .values(track_position=PlaylistSongLink.track_position - 1)
                )
                session.execute(query)
            else:
                query = select(func.max(PlaylistSongLink.track_position)).where(
                    PlaylistSongLink.playlist_id == uuid
                )
                maxi = session.execute(query).scalar() or 0

                if position is None or position > maxi:
                    target_position = maxi + 1
                else:
                    target_position = max(1, position)
                    query = (
                        update(PlaylistSongLink)
                        .where(PlaylistSongLink.playlist_id == uuid)
                        .where(PlaylistSongLink.track_position >= target_position)
                        .values(track_position=PlaylistSongLink.track_position + 1)
                    )
                    session.execute(query)

                session.add(
                    PlaylistSongLink(
                        playlist=playlist,
                        song=song,
                        track_position=target_position,
                    )
                )

        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while modifying playlist : {e}")
        return 1

def addSongToPlaylist(session: Session, song_uuid: str, playlist_uuid: str, position: int | None) -> int:
    try:
        playlist = session.get(Playlist, playlist_uuid)
        if not playlist:
            logger.warning(f"Tried to add song to non-existant playlist with UUID : {playlist_uuid}")
            return 22
        
        song = session.get(Song, song_uuid)
        if not song:
            logger.warning(f"Tried to add non-existant song with UUID to playlist : {song_uuid}")
            return 22
        
        query = select(func.max(PlaylistSongLink.track_position)).where(
            PlaylistSongLink.playlist == playlist
        )

        maxi = session.execute(query).scalar() or 0
        
        if position is None or position > maxi:
            target_position = maxi + 1
        else:
            target_position = max(1, position)
            query = (update(PlaylistSongLink)
                        .where(PlaylistSongLink.playlist == playlist)
                        .where(PlaylistSongLink.track_position >= target_position)
                        .values(track_position=PlaylistSongLink.track_position + 1))
            session.execute(query)

        new_link = PlaylistSongLink(
            playlist=playlist,
            song=song,
            track_position=target_position
        )
        session.add(new_link)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding song to playlist : {e}")
        return 1


def removeSongFromPlaylist(session: Session, song_uuid: str, playlist_uuid: str, position: int) -> int:
    try:
        query = select(PlaylistSongLink).where(
            PlaylistSongLink.playlist_id == playlist_uuid,
            PlaylistSongLink.track_position == position
        )
        link = session.execute(query).scalar_one_or_none()

        if not link:
            return 22
        
        session.delete(link)

        query = (update(PlaylistSongLink)
                    .where(PlaylistSongLink.playlist_id == playlist_uuid)
                    .where(PlaylistSongLink.track_position > position)
                    .values(track_position=PlaylistSongLink.track_position - 1))
        
        session.execute(query)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error removing song from playlist : {e}")
        return 1


def getSongFromPlaylistIndex(session: Session, playlist_id: str, index: int):
    playlist = session.get(Playlist, playlist_id)
    if not playlist:
        logger.warning(f"Tried to query non-existant playlist with UUID : {playlist_id}")
        return 22
    query = (select(PlaylistSongLink)
             .where(
                 PlaylistSongLink.playlist_id == playlist_id,
                 PlaylistSongLink.track_position == index
             )
             .options(joinedload(PlaylistSongLink.song).joinedload(Song.artist)))
    link = session.execute(query).scalar_one_or_none()

    if not link:
        return 22
        
    # 5. Return the cleanly formatted data
    return {
        "id": link.song.id,
        "title": link.song.title,
        "artist": link.song.artist.name
    }
