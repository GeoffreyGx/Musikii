from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from models.sql import initializeDB

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

def getDB():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
