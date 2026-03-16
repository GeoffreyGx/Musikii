import logging
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session, joinedload
from models.sql import Song, Artist, Playlist, PlaylistSongLink

logger = logging.getLogger()

def newSong(session: Session, title: str, artist_id: str, uuid: str) -> int:
    try:
        if not session.get(Artist, artist_id):
            return 221
        if session.get(Song, uuid):
            return 21
        
        new_song = Song(id=uuid, title=title, artist_id=artist_id)
        session.add(new_song)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while adding new song : {e}")
        return 1
    
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
    
def deleteArtist(session: Session, uuid: str) -> int:
    try:
        artist = session.get(Artist, uuid)
        if not artist:
            logger.warning(f"Tried to remove non-existant artist with UUID : {uuid}")
            return 22
        
        session.delete(artist)
        session.commit()
        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"Error while removing artist : {e}")
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

def getSongInfo(session: Session, uuid: str):
    query = select(Song).options(joinedload(Song.artist)).where(Song.id == uuid)
    song = session.execute(query).scalar_one_or_none()
    if not song:
        return 22
    if not song.artist:
        return 23
    
    return {
        'title': song.title,
        'artist': {'name': song.artist.name}
    }

def getSongs(session: Session):
    query = select(Song).options(joinedload(Song.artist))
    songs = session.execute(query).scalars().all()

    result = []
    for song in songs:
        if not song.artist:
            return 23
        result.append({
            'title': song.title,
            'artist': {'name': song.artist.name}
        })
    return result
