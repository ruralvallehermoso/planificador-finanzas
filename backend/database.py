from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para los modelos ORM."""


import os
import shutil

# Ensure Postgres URL uses postgresql:// scheme (Vercel often gives postgres://)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")

# VERCEL/AWS LAMBDA FIX: SQLite must be in /tmp
if "sqlite" in DATABASE_URL and not os.access(".", os.W_OK):
    print("⚠️ Read-only file system detected. Copying DB to /tmp...")
    TMP_DB_PATH = "/tmp/portfolio.db"
    if not os.path.exists(TMP_DB_PATH):
        try:
             # Try to find source DB in api/ or root
             src = "portfolio.db"
             if not os.path.exists(src):
                 src = "api/portfolio.db" # In case we are running from root
             
             if os.path.exists(src):
                 shutil.copy2(src, TMP_DB_PATH)
                 print(f"✅ Copied {src} to {TMP_DB_PATH}")
             else:
                 print(f"⚠️ Source DB {src} not found, starting empty in /tmp")
        except Exception as e:
             print(f"❌ DB Copy Error: {e}")
    
    DATABASE_URL = f"sqlite:///{TMP_DB_PATH}"

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


