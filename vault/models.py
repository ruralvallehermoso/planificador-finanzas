"""
SQLAlchemy models for the secure vault.
Stores platforms, credentials, and associated assets.
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from database import Base


class Platform(Base):
    """
    Financial platform (bank, broker, exchange, fund manager).
    Central entity for organizing credentials and assets.
    """
    __tablename__ = "platforms"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # BANK, BROKER, CRYPTO, FUND, OTHER
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credentials = relationship("Credential", back_populates="platform", cascade="all, delete-orphan")
    assets = relationship("PlatformAsset", back_populates="platform", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Platform {self.name} ({self.type})>"


class Credential(Base):
    """
    Encrypted credentials for accessing a platform.
    All sensitive fields (username, password, pin, notes) are stored encrypted.
    """
    __tablename__ = "credentials"
    
    id = Column(String, primary_key=True)
    platform_id = Column(String, ForeignKey("platforms.id"), nullable=False)
    
    # Label for this credential set (e.g., "Main Login", "API Key", "Trading Account")
    label = Column(String, nullable=False, default="Principal")
    
    # Encrypted fields - stored as base64-encoded ciphertext
    username_encrypted = Column(Text, nullable=True)
    password_encrypted = Column(Text, nullable=True)
    pin_encrypted = Column(Text, nullable=True)
    extra_encrypted = Column(Text, nullable=True)  # For 2FA secrets, API keys, etc.
    notes_encrypted = Column(Text, nullable=True)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    platform = relationship("Platform", back_populates="credentials")
    
    def __repr__(self):
        return f"<Credential {self.label} for {self.platform_id}>"


class PlatformAsset(Base):
    """
    Assets associated with a platform.
    Tracks balances/values for each account/product in the platform.
    Can be linked to the main Finanzas asset system.
    """
    __tablename__ = "platform_assets"
    
    id = Column(String, primary_key=True)
    platform_id = Column(String, ForeignKey("platforms.id"), nullable=False)
    
    # Asset details
    name = Column(String, nullable=False)  # "Cuenta Nómina", "Cartera Indexa CT"
    asset_type = Column(String, nullable=True)  # ACCOUNT, FUND, CRYPTO, STOCK, etc.
    current_value = Column(Float, nullable=True)
    currency = Column(String, default="EUR")
    
    # Link to main Finanzas system (optional)
    finanzas_asset_id = Column(String, nullable=True)
    
    # Additional info
    account_number = Column(String, nullable=True)  # Can be encrypted if needed
    notes = Column(Text, nullable=True)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    platform = relationship("Platform", back_populates="assets")
    
    def __repr__(self):
        return f"<PlatformAsset {self.name} ({self.platform_id})>"

class KeyStore(Base):
    """
    Stores encrypted cryptographic keys for the vault.
    Supports hybrid encryption architecture.
    """
    __tablename__ = "keystore"
    
    id = Column(String, primary_key=True, default="primary")
    
    # RSA Public Key (Base64 encoded PEM) - Safe to expose
    public_key = Column(Text, nullable=False)
    
    # RSA Private Key Encrypted with Master Password (AES-GCM)
    # Format: salt.nonce.tag.ciphertext
    private_key_encrypted = Column(Text, nullable=False)
    
    # Data Encryption Key (DEK) Encrypted with RSA Public Key
    # Format: Base64 encoded OAEP ciphertext
    dek_encrypted = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<KeyStore {self.id}>"
