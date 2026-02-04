"""
Vault API - Secure credential storage with HYBRID encryption (RSA + AES).
Runs on localhost:5001 for local-only access.
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db, VAULT_DB_PATH
from models import Platform, Credential, PlatformAsset, KeyStore
from schemas import (
    PlatformCreate, PlatformUpdate, PlatformResponse, PlatformDetailResponse,
    CredentialCreate, CredentialUpdate, CredentialResponse,
    PlatformAssetCreate, PlatformAssetUpdate, PlatformAssetResponse,
    UnlockRequest, UnlockResponse, HealthResponse
)
# Switch to Hybrid Crypto
from crypto_hybrid import HybridCrypto, VaultSession

# Global vault session
_vault_session = VaultSession()


def get_vault_session() -> VaultSession:
    """Get the active vault session, raising error if locked."""
    if not _vault_session.is_active():
        raise HTTPException(status_code=401, detail="Vault is locked. Unlock first with /unlock")
    return _vault_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    
    # Auto-unlock if master key is in environment (for dev convenience)
    # real production usage should require manual unlock
    master_key = os.environ.get("VAULT_MASTER_KEY")
    if master_key:
        try:
            # Create a localized DB session just for startup unlock
            db = next(get_db())
            keystore = db.query(KeyStore).first()
            
            if keystore:
                try:
                    _vault_session.load_keys(
                        keystore.private_key_encrypted,
                        keystore.dek_encrypted,
                        master_key
                    )
                    print("🔓 Vault auto-unlocked with hybrid keys")
                except Exception as e:
                    print(f"❌ Auto-unlock failed: {e}")
            else:
                 print("ℹ️ Vault not initialized. Use /setup first.")
            
        except Exception as e:
            print(f"⚠️ Startup error: {e}")
    else:
        print("🔒 Vault is locked. Use /unlock endpoint")
    
    yield


app = FastAPI(
    title="Vault API (Hybrid)",
    description="Secure storage with RSA+AES hybrid encryption",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Setup & Auth Endpoints =============

@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Check vault status."""
    keystore = db.query(KeyStore).first()
    is_setup = keystore is not None
    platform_count = db.query(Platform).count() if _vault_session.is_active() else 0
    
    return HealthResponse(
        status="ok",
        vault_path=VAULT_DB_PATH,
        is_unlocked=_vault_session.is_active(),
        is_setup=is_setup,
        platform_count=platform_count
    )


@app.post("/setup", response_model=UnlockResponse)
def setup_vault(request: UnlockRequest, db: Session = Depends(get_db)):
    """Initialize the vault with a master password (generates keys)."""
    if db.query(KeyStore).first():
        raise HTTPException(status_code=400, detail="Vault already initialized")
    
    try:
        crypto = HybridCrypto()
        
        # 1. Generate keys
        priv_key, pub_key = crypto.generate_rsa_keypair()
        dek = crypto.generate_dek()
        
        # 2. Encrypt keys
        priv_enc = crypto.encrypt_private_key(priv_key, request.master_password)
        dek_enc = crypto.encrypt_dek(dek, pub_key)
        pub_pem = crypto.serialize_public_key(pub_key)
        
        # 3. Save to DB
        keystore = KeyStore(
            id="primary",
            public_key=pub_pem,
            private_key_encrypted=priv_enc,
            dek_encrypted=dek_enc
        )
        db.add(keystore)
        db.commit()
        
        # 4. Auto-unlock
        _vault_session.private_key = priv_key
        _vault_session.public_key = pub_key
        _vault_session.dek = dek
        
        return UnlockResponse(success=True, message="Vault initialized with hybrid encryption")
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/unlock", response_model=UnlockResponse)
def unlock_vault(request: UnlockRequest, db: Session = Depends(get_db)):
    """Unlock the vault."""
    keystore = db.query(KeyStore).first()
    if not keystore:
        raise HTTPException(status_code=404, detail="Vault not initialized")
    
    try:
        _vault_session.load_keys(
            keystore.private_key_encrypted,
            keystore.dek_encrypted,
            request.master_password
        )
        return UnlockResponse(success=True, message="Vault unlocked")
    except Exception as e:
        return UnlockResponse(success=False, message="Invalid password or corrupted keys")


@app.post("/lock", response_model=UnlockResponse)
def lock_vault():
    """Lock the vault."""
    _vault_session.clear()
    return UnlockResponse(success=True, message="Vault locked")


# ============= Resource Endpoints (Using Hybrid Crypto) =============

# Helper to format response (same as before)
def platform_to_response(platform: Platform) -> PlatformResponse:
    total_value = sum(a.current_value or 0 for a in platform.assets)
    return PlatformResponse(
        id=platform.id,
        name=platform.name,
        type=platform.type,
        website=platform.website,
        logo_url=platform.logo_url,
        notes=platform.notes,
        is_active=platform.is_active,
        created_at=platform.created_at,
        updated_at=platform.updated_at,
        credential_count=len(platform.credentials),
        asset_count=len(platform.assets),
        total_value=total_value
    )

@app.get("/platforms", response_model=List[PlatformResponse])
def list_platforms(
    type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    vault: VaultSession = Depends(get_vault_session)
):
    query = db.query(Platform)
    if type:
        query = query.filter(Platform.type == type)
    if active_only:
        query = query.filter(Platform.is_active == True)
    
    return [platform_to_response(p) for p in query.order_by(Platform.name).all()]


@app.post("/platforms", response_model=PlatformResponse)
def create_platform(
    data: PlatformCreate,
    db: Session = Depends(get_db),
    vault: VaultSession = Depends(get_vault_session)
):
    platform_id = data.id or f"p-{uuid.uuid4().hex[:8]}"
    
    if db.query(Platform).filter(Platform.id == platform_id).first():
        raise HTTPException(status_code=400, detail="Platform ID exists")
    
    platform = Platform(
        id=platform_id,
        name=data.name,
        type=data.type.upper(),
        website=data.website,
        logo_url=data.logo_url,
        notes=data.notes,
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform_to_response(platform)


@app.get("/platforms/{platform_id}", response_model=PlatformDetailResponse)
def get_platform(
    platform_id: str,
    show_secrets: bool = Query(False),
    db: Session = Depends(get_db),
    vault: VaultSession = Depends(get_vault_session)
):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    # Decrypt credentials using HybridCrypto (AES-GCM via DEK)
    credentials = []
    for cred in platform.credentials:
        # Helper to decrypt field safely
        def decrypt(val):
            return vault.crypto.decrypt_data(val, vault.dek) if val else None
            
        cred_response = CredentialResponse(
            id=cred.id,
            platform_id=cred.platform_id,
            label=cred.label,
            username=decrypt(cred.username_encrypted),
            password=decrypt(cred.password_encrypted) if show_secrets else ("••••••••" if cred.password_encrypted else None),
            pin=decrypt(cred.pin_encrypted) if show_secrets else ("••••" if cred.pin_encrypted else None),
            extra=decrypt(cred.extra_encrypted) if show_secrets else ("••••••••" if cred.extra_encrypted else None),
            notes=decrypt(cred.notes_encrypted),
            last_updated=cred.last_updated,
            created_at=cred.created_at
        )
        credentials.append(cred_response)
    
    # Assets (no encryption for now, but ready if needed)
    assets = [
        PlatformAssetResponse(
            id=a.id,
            platform_id=a.platform_id,
            name=a.name,
            asset_type=a.asset_type,
            current_value=a.current_value,
            currency=a.currency,
            finanzas_asset_id=a.finanzas_asset_id,
            account_number=a.account_number,
            notes=a.notes,
            last_updated=a.last_updated,
            created_at=a.created_at
        ) for a in platform.assets
    ]
    
    total_value = sum(a.current_value or 0 for a in platform.assets)
    
    return PlatformDetailResponse(
        id=platform.id,
        name=platform.name,
        type=platform.type,
        website=platform.website,
        logo_url=platform.logo_url,
        notes=platform.notes,
        is_active=platform.is_active,
        created_at=platform.created_at,
        updated_at=platform.updated_at,
        credential_count=len(credentials),
        asset_count=len(assets),
        total_value=total_value,
        credentials=credentials,
        assets=assets
    )


@app.post("/platforms/{platform_id}/credentials", response_model=CredentialResponse)
def create_credential(
    platform_id: str,
    data: CredentialCreate,
    db: Session = Depends(get_db),
    vault: VaultSession = Depends(get_vault_session)
):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    # Encrypt using HybridCrypto (AES-GCM via DEK)
    def encrypt(val):
        return vault.crypto.encrypt_data(val, vault.dek) if val else None

    credential = Credential(
        id=f"cred-{uuid.uuid4().hex[:8]}",
        platform_id=platform_id,
        label=data.label,
        username_encrypted=encrypt(data.username),
        password_encrypted=encrypt(data.password),
        pin_encrypted=encrypt(data.pin),
        extra_encrypted=encrypt(data.extra),
        notes_encrypted=encrypt(data.notes),
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    
    return CredentialResponse(
        id=credential.id,
        platform_id=credential.platform_id,
        label=credential.label,
        username=data.username,
        password="••••••••" if data.password else None,
        pin="••••" if data.pin else None,
        extra="••••••••" if data.extra else None,
        notes=data.notes,
        last_updated=credential.last_updated,
        created_at=credential.created_at
    )


# Basic delete/update endpoints usually don't involve crypto logic 
# (unless updating secrets), so skipping for brevity but they exist similarly

if __name__ == "__main__":
    import uvicorn
    print("🔐 Starting Hybrid Vault API on http://localhost:5001")
    uvicorn.run(app, host="127.0.0.1", port=5001)
