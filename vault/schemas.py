"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============= Platform Schemas =============

class PlatformBase(BaseModel):
    name: str
    type: str = Field(description="BANK, BROKER, CRYPTO, FUND, OTHER")
    website: Optional[str] = None
    logo_url: Optional[str] = None
    notes: Optional[str] = None


class PlatformCreate(PlatformBase):
    id: Optional[str] = None  # Auto-generated if not provided


class PlatformUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class PlatformResponse(PlatformBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    credential_count: int = 0
    asset_count: int = 0
    total_value: float = 0.0
    
    class Config:
        from_attributes = True


class PlatformDetailResponse(PlatformResponse):
    credentials: List["CredentialResponse"] = []
    assets: List["PlatformAssetResponse"] = []


# ============= Credential Schemas =============

class CredentialBase(BaseModel):
    label: str = "Principal"
    username: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    extra: Optional[str] = None  # 2FA, API keys, etc.
    notes: Optional[str] = None


class CredentialCreate(CredentialBase):
    pass


class CredentialUpdate(BaseModel):
    label: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    extra: Optional[str] = None
    notes: Optional[str] = None


class CredentialResponse(BaseModel):
    id: str
    platform_id: str
    label: str
    username: Optional[str] = None  # Decrypted
    password: Optional[str] = None  # Decrypted (masked by default)
    pin: Optional[str] = None       # Decrypted (masked by default)
    extra: Optional[str] = None     # Decrypted (masked by default)
    notes: Optional[str] = None     # Decrypted
    last_updated: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Asset Schemas =============

class PlatformAssetBase(BaseModel):
    name: str
    asset_type: Optional[str] = None  # ACCOUNT, FUND, CRYPTO, STOCK
    current_value: Optional[float] = None
    currency: str = "EUR"
    finanzas_asset_id: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None


class PlatformAssetCreate(PlatformAssetBase):
    pass


class PlatformAssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    current_value: Optional[float] = None
    currency: Optional[str] = None
    finanzas_asset_id: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None


class PlatformAssetResponse(PlatformAssetBase):
    id: str
    platform_id: str
    last_updated: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Auth Schemas =============

class UnlockRequest(BaseModel):
    master_password: str


class UnlockResponse(BaseModel):
    success: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    vault_path: str
    is_unlocked: bool
    is_setup: bool
    platform_count: int


# Forward references for nested models
PlatformDetailResponse.model_rebuild()
