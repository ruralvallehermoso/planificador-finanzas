from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para los modelos ORM."""


import os

# Ensure Postgres URL uses postgresql:// scheme (Vercel often gives postgres://)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # Test connections before using them
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependencia de FastAPI para obtener una sesión de BBDD por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


