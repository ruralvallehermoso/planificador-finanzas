"""
Script to migrate from legacy Fernet encryption (v1) to Hybrid RSA+AES encryption (v2).
Usage: python migrate.py
"""

import sys
import getpass
from sqlalchemy.orm import Session
from database import get_db, init_db
from models import Credential, PlatformAsset, KeyStore
# Import old crypto for decryption
import crypto as old_crypto
# Import new crypto for encryption
from crypto_hybrid import HybridCrypto
from database import engine

def migrate():
    print("🚀 Starting migration to Hybrid Encryption (v2)...")
    
    # 1. Check if already migrated
    db = next(get_db())
    if db.query(KeyStore).first():
        print("✅ Vault already uses hybrid encryption. No migration needed.")
        return

    # 2. Get master password to decrypt current data
    master_password = getpass.getpass("🔑 Enter your current Master Password: ")
    if not master_password:
        print("❌ Password required.")
        return

    try:
        # Verify password by trying to derive the key (lazy check)
        # In v1, we didn't store a password hash, we just implied it worked if decryption worked.
        # So we'll try to decrypt the first credential we find as a test.
        old_cipher = old_crypto.get_cipher(master_password)
    except Exception as e:
        print(f"❌ Error deriving old key: {e}")
        return

    credentials = db.query(Credential).all()
    print(f"📦 Found {len(credentials)} credentials to migrate.")
    
    # 3. Initialize new Hybrid System
    print("⚙️  Generating new RSA-4096 keys and DEK...")
    hybrid = HybridCrypto()
    priv_key, pub_key = hybrid.generate_rsa_keypair()
    dek = hybrid.generate_dek()
    
    # 4. Migrate Data
    success_count = 0
    error_count = 0
    
    print("🔄 Re-encrypting data...")
    for cred in credentials:
        try:
            # Decrypt with old (Fernet)
            # Only decrypt fields that are present
            username = old_crypto.decrypt_value(old_cipher, cred.username_encrypted) if cred.username_encrypted else None
            password = old_crypto.decrypt_value(old_cipher, cred.password_encrypted) if cred.password_encrypted else None
            pin = old_crypto.decrypt_value(old_cipher, cred.pin_encrypted) if cred.pin_encrypted else None
            extra = old_crypto.decrypt_value(old_cipher, cred.extra_encrypted) if cred.extra_encrypted else None
            notes = old_crypto.decrypt_value(old_cipher, cred.notes_encrypted) if cred.notes_encrypted else None
            
            # Encrypt with new (AES-GCM via DEK)
            cred.username_encrypted = hybrid.encrypt_data(username, dek) if username else None
            cred.password_encrypted = hybrid.encrypt_data(password, dek) if password else None
            cred.pin_encrypted = hybrid.encrypt_data(pin, dek) if pin else None
            cred.extra_encrypted = hybrid.encrypt_data(extra, dek) if extra else None
            cred.notes_encrypted = hybrid.encrypt_data(notes, dek) if notes else None
            
            success_count += 1
        except Exception as e:
            print(f"  ⚠️ Error migrating credential {cred.id}: {e}")
            error_count += 1
    
    # 5. Save Keys to DB (KeyStore)
    print("🔐 Saving new Keystore...")
    priv_enc = hybrid.encrypt_private_key(priv_key, master_password)
    dek_enc = hybrid.encrypt_dek(dek, pub_key)
    pub_pem = hybrid.serialize_public_key(pub_key)
    
    keystore = KeyStore(
        id="primary",
        public_key=pub_pem,
        private_key_encrypted=priv_enc,
        dek_encrypted=dek_enc
    )
    db.add(keystore)
    
    # 6. Commit transaction
    if error_count == 0:
        try:
            db.commit()
            print(f"✅ Migration successful! {success_count} credentials migrated.")
            print("INFO: You can now restart the vault server.")
        except Exception as e:
            db.rollback()
            print(f"❌ Database commit error: {e}")
    else:
        print(f"⚠️ Migration finished with {error_count} errors. Rolling back changes for safety.")
        db.rollback()

if __name__ == "__main__":
    # Ensure tables exist (specifically KeyStore)
    init_db()
    migrate()
