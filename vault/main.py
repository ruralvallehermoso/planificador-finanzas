"""
Vault API - Secure credential storage with encrypted SQLite.
Runs on localhost:5001 for local-only access.
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db, VAULT_DB_PATH
from models import Platform, Credential, PlatformAsset
from schemas import (
    PlatformCreate, PlatformUpdate, PlatformResponse, PlatformDetailResponse,
    CredentialCreate, CredentialUpdate, CredentialResponse,
    PlatformAssetCreate, PlatformAssetUpdate, PlatformAssetResponse,
    UnlockRequest, UnlockResponse, HealthResponse
)
from crypto import VaultCrypto, get_crypto


# Global crypto instance - set when vault is unlocked
_crypto: Optional[VaultCrypto] = None


def get_crypto_instance() -> VaultCrypto:
    """Get the crypto instance, raising error if vault is locked."""
    if _crypto is None:
        raise HTTPException(status_code=401, detail="Vault is locked. Unlock first with /unlock")
    return _crypto


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    
    # Auto-unlock if master key is in environment
    master_key = os.environ.get("VAULT_MASTER_KEY")
    if master_key:
        global _crypto
        _crypto = get_crypto(master_key)
        print("🔓 Vault auto-unlocked from environment variable")
    else:
        print("🔒 Vault is locked. Use /unlock endpoint or set VAULT_MASTER_KEY")
    
    yield


app = FastAPI(
    title="Vault API",
    description="Secure credential storage with encrypted SQLite",
    version="1.0.0",
    lifespan=lifespan
)

# Allow CORS only from localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Health & Auth Endpoints =============

@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Check vault health and status."""
    platform_count = db.query(Platform).count() if _crypto else 0
    return HealthResponse(
        status="ok",
        vault_path=VAULT_DB_PATH,
        is_unlocked=_crypto is not None,
        platform_count=platform_count
    )


@app.post("/unlock", response_model=UnlockResponse)
def unlock_vault(request: UnlockRequest):
    """Unlock the vault with master password."""
    global _crypto
    try:
        crypto = get_crypto(request.master_password)
        if crypto.verify_password():
            _crypto = crypto
            return UnlockResponse(success=True, message="Vault unlocked successfully")
        else:
            return UnlockResponse(success=False, message="Invalid master password")
    except Exception as e:
        return UnlockResponse(success=False, message=str(e))


@app.post("/lock", response_model=UnlockResponse)
def lock_vault():
    """Lock the vault, clearing the crypto instance."""
    global _crypto
    _crypto = None
    return UnlockResponse(success=True, message="Vault locked")


# ============= Platform Endpoints =============

def generate_id(name: str) -> str:
    """Generate a URL-friendly ID from a name."""
    base = name.lower().replace(" ", "-").replace(".", "")
    # Remove non-alphanumeric except dashes
    base = "".join(c for c in base if c.isalnum() or c == "-")
    return f"{base}-{uuid.uuid4().hex[:6]}"


def platform_to_response(platform: Platform) -> PlatformResponse:
    """Convert Platform model to response with counts."""
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
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """List all platforms."""
    query = db.query(Platform)
    if type:
        query = query.filter(Platform.type == type)
    if active_only:
        query = query.filter(Platform.is_active == True)
    
    platforms = query.order_by(Platform.name).all()
    return [platform_to_response(p) for p in platforms]


@app.post("/platforms", response_model=PlatformResponse)
def create_platform(
    data: PlatformCreate,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Create a new platform."""
    platform_id = data.id or generate_id(data.name)
    
    # Check for duplicate
    existing = db.query(Platform).filter(Platform.id == platform_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Platform with ID {platform_id} already exists")
    
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
    show_secrets: bool = Query(False, description="Show decrypted passwords"),
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Get platform details with credentials and assets."""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    # Decrypt credentials
    credentials = []
    for cred in platform.credentials:
        cred_response = CredentialResponse(
            id=cred.id,
            platform_id=cred.platform_id,
            label=cred.label,
            username=crypto.decrypt(cred.username_encrypted) if cred.username_encrypted else None,
            password=crypto.decrypt(cred.password_encrypted) if show_secrets and cred.password_encrypted else ("••••••••" if cred.password_encrypted else None),
            pin=crypto.decrypt(cred.pin_encrypted) if show_secrets and cred.pin_encrypted else ("••••" if cred.pin_encrypted else None),
            extra=crypto.decrypt(cred.extra_encrypted) if show_secrets and cred.extra_encrypted else ("••••••••" if cred.extra_encrypted else None),
            notes=crypto.decrypt(cred.notes_encrypted) if cred.notes_encrypted else None,
            last_updated=cred.last_updated,
            created_at=cred.created_at
        )
        credentials.append(cred_response)
    
    # Assets
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
        )
        for a in platform.assets
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


@app.put("/platforms/{platform_id}", response_model=PlatformResponse)
def update_platform(
    platform_id: str,
    data: PlatformUpdate,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Update a platform."""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "type" and value:
            value = value.upper()
        setattr(platform, field, value)
    
    db.commit()
    db.refresh(platform)
    return platform_to_response(platform)


@app.delete("/platforms/{platform_id}")
def delete_platform(
    platform_id: str,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Delete a platform and all associated credentials and assets."""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    db.delete(platform)
    db.commit()
    return {"message": f"Platform {platform_id} deleted"}


# ============= Credential Endpoints =============

@app.post("/platforms/{platform_id}/credentials", response_model=CredentialResponse)
def create_credential(
    platform_id: str,
    data: CredentialCreate,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Create a new credential for a platform."""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    credential = Credential(
        id=f"cred-{uuid.uuid4().hex[:8]}",
        platform_id=platform_id,
        label=data.label,
        username_encrypted=crypto.encrypt(data.username) if data.username else None,
        password_encrypted=crypto.encrypt(data.password) if data.password else None,
        pin_encrypted=crypto.encrypt(data.pin) if data.pin else None,
        extra_encrypted=crypto.encrypt(data.extra) if data.extra else None,
        notes_encrypted=crypto.encrypt(data.notes) if data.notes else None,
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


@app.put("/credentials/{credential_id}", response_model=CredentialResponse)
def update_credential(
    credential_id: str,
    data: CredentialUpdate,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Update a credential."""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    if data.label is not None:
        credential.label = data.label
    if data.username is not None:
        credential.username_encrypted = crypto.encrypt(data.username) if data.username else None
    if data.password is not None:
        credential.password_encrypted = crypto.encrypt(data.password) if data.password else None
    if data.pin is not None:
        credential.pin_encrypted = crypto.encrypt(data.pin) if data.pin else None
    if data.extra is not None:
        credential.extra_encrypted = crypto.encrypt(data.extra) if data.extra else None
    if data.notes is not None:
        credential.notes_encrypted = crypto.encrypt(data.notes) if data.notes else None
    
    db.commit()
    db.refresh(credential)
    
    return CredentialResponse(
        id=credential.id,
        platform_id=credential.platform_id,
        label=credential.label,
        username=crypto.decrypt(credential.username_encrypted) if credential.username_encrypted else None,
        password="••••••••" if credential.password_encrypted else None,
        pin="••••" if credential.pin_encrypted else None,
        extra="••••••••" if credential.extra_encrypted else None,
        notes=crypto.decrypt(credential.notes_encrypted) if credential.notes_encrypted else None,
        last_updated=credential.last_updated,
        created_at=credential.created_at
    )


@app.delete("/credentials/{credential_id}")
def delete_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Delete a credential."""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    db.delete(credential)
    db.commit()
    return {"message": f"Credential {credential_id} deleted"}


# ============= Asset Endpoints =============

@app.post("/platforms/{platform_id}/assets", response_model=PlatformAssetResponse)
def create_asset(
    platform_id: str,
    data: PlatformAssetCreate,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Create a new asset for a platform."""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    asset = PlatformAsset(
        id=f"asset-{uuid.uuid4().hex[:8]}",
        platform_id=platform_id,
        name=data.name,
        asset_type=data.asset_type,
        current_value=data.current_value,
        currency=data.currency,
        finanzas_asset_id=data.finanzas_asset_id,
        account_number=data.account_number,
        notes=data.notes,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return PlatformAssetResponse(
        id=asset.id,
        platform_id=asset.platform_id,
        name=asset.name,
        asset_type=asset.asset_type,
        current_value=asset.current_value,
        currency=asset.currency,
        finanzas_asset_id=asset.finanzas_asset_id,
        account_number=asset.account_number,
        notes=asset.notes,
        last_updated=asset.last_updated,
        created_at=asset.created_at
    )


@app.put("/assets/{asset_id}", response_model=PlatformAssetResponse)
def update_asset(
    asset_id: str,
    data: PlatformAssetUpdate,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Update an asset."""
    asset = db.query(PlatformAsset).filter(PlatformAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    
    db.commit()
    db.refresh(asset)
    
    return PlatformAssetResponse(
        id=asset.id,
        platform_id=asset.platform_id,
        name=asset.name,
        asset_type=asset.asset_type,
        current_value=asset.current_value,
        currency=asset.currency,
        finanzas_asset_id=asset.finanzas_asset_id,
        account_number=asset.account_number,
        notes=asset.notes,
        last_updated=asset.last_updated,
        created_at=asset.created_at
    )


@app.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    crypto: VaultCrypto = Depends(get_crypto_instance)
):
    """Delete an asset."""
    asset = db.query(PlatformAsset).filter(PlatformAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    db.delete(asset)
    db.commit()
    return {"message": f"Asset {asset_id} deleted"}


# ============= Main =============

if __name__ == "__main__":
    import uvicorn
    print("🔐 Starting Vault API on http://localhost:5001")
    print("⚠️  This API only accepts connections from localhost")
    uvicorn.run(app, host="127.0.0.1", port=5001)
