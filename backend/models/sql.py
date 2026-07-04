from __future__ import annotations

from typing import List
from sqlalchemy import Table, Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.engine import Engine

class Base(DeclarativeBase):
    pass

song_links = Table('song_links', Base.metadata,
                    Column('id', Integer, primary_key=True, autoincrement=True),
                    Column("playlistId", ForeignKey("playlist.id", ondelete="CASCADE")),
                    Column("songId", ForeignKey("song.id", ondelete="CASCADE"))
                    )

class PlaylistSongLink(Base):
    __tablename__ = 'playlist_song_link'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_id: Mapped[str] = mapped_column(ForeignKey("playlist.id", ondelete="CASCADE"))
    song_id: Mapped[str] = mapped_column(ForeignKey("song.id", ondelete="CASCADE"))
    track_position: Mapped[int] = mapped_column(Integer, default=1)

    playlist: Mapped[Playlist] = relationship(back_populates="song_links")
    song: Mapped[Song] = relationship(back_populates="playlist_links")

class Artist(Base):
    __tablename__ = "artist"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    songs: Mapped[List[Song]] = relationship(
        back_populates="artist",
        cascade="all, delete-orphan"
    )

class Resource(Base):
    __tablename__ = "resource"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    uploaded: Mapped[bool] = mapped_column(Boolean)
    song: Mapped[Song] = relationship(back_populates="resource")

class Song(Base):
    __tablename__ = "song"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    artist_id: Mapped[str] = mapped_column(ForeignKey("artist.id", ondelete="CASCADE"))
    artist: Mapped[Artist] = relationship(back_populates="songs")
    resource_id: Mapped[str] = mapped_column(ForeignKey("resource.id", ondelete="RESTRICT"))
    resource: Mapped[Resource] = relationship(back_populates="song")
    playlist_links: Mapped[List[PlaylistSongLink]] = relationship(
        back_populates="song",
        cascade="all, delete-orphan"
    )

class Playlist(Base):
    __tablename__ = "playlist"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    song_links: Mapped[List[PlaylistSongLink]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistSongLink.track_position"
    )

def initializeDB(engine: Engine):
    Base.metadata.create_all(engine)