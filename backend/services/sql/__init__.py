import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from models.sql import initializeDB

logger = logging.getLogger()

DB_DIALECT = os.getenv("DB_DIALECT")

if DB_DIALECT == "sqlite":
    sql_engine = create_engine(
        "sqlite:///dev.sqlite",
        connect_args={"check_same_thread": False}
    )
elif DB_DIALECT == "postgresql":
    sql_engine = create_engine(
        "postgresql://musikii:musikii@localhost:5432/musikii"
    )
else:
    raise RuntimeError("DB not configured! Duplicate .env.example as .env and specify the environment variables you want.")
    



@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # We only want to run this if the engine is actually SQLite
    if type(dbapi_connection) is __import__("sqlite3").Connection:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    if type(dbapi_connection) is __import__("psycopg2").extensions.connection:
        cursor = dbapi_connection.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
        cursor.close()

initializeDB(sql_engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sql_engine)

def getDB():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
