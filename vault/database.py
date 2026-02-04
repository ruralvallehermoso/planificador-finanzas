"""
SQLite database connection with SQLCipher encryption support.
Falls back to standard SQLite if SQLCipher is not available.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all vault models."""
    pass


# Database location - secure location in user's Application Support
def get_vault_db_path() -> str:
    """Get the path to the vault database file."""
    # Use Application Support on macOS for secure storage
    app_support = Path.home() / "Library" / "Application Support" / "Planificador"
    app_support.mkdir(parents=True, exist_ok=True)
    return str(app_support / "vault.db")


# Get master password from environment
VAULT_MASTER_KEY = os.environ.get("VAULT_MASTER_KEY", "")

# SQLCipher database URL
VAULT_DB_PATH = get_vault_db_path()
DATABASE_URL = f"sqlite:///{VAULT_DB_PATH}"

# Check if we should use SQLCipher
USE_SQLCIPHER = False
try:
    # Try to import pysqlcipher3
    from pysqlcipher3 import dbapi2 as sqlite3
    USE_SQLCIPHER = True
    print("✅ SQLCipher available - using encrypted database")
except ImportError:
    import sqlite3
    print("⚠️ SQLCipher not available - using standard SQLite (less secure)")

# Create engine with appropriate settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


# If using SQLCipher, set up encryption key
if USE_SQLCIPHER and VAULT_MASTER_KEY:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLCipher encryption key on every connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA key = '{VAULT_MASTER_KEY}'")
        # Additional security settings
        cursor.execute("PRAGMA cipher_memory_security = ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize the database tables."""
    from models import Platform, Credential, PlatformAsset  # noqa
    Base.metadata.create_all(bind=engine)
    print(f"✅ Vault database initialized at: {VAULT_DB_PATH}")


def get_db():
    """Dependency for FastAPI to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
