"""
Crypto utilities for encrypting/decrypting sensitive vault fields.
Uses Fernet (AES-256-CBC) with PBKDF2 key derivation.
"""

import base64
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Salt should be consistent for the same vault
# Can be customized via environment variable
VAULT_SALT = os.environ.get("VAULT_SALT", "planificador-vault-2024").encode()


class VaultCrypto:
    """Handles encryption/decryption of sensitive fields using a master password."""
    
    def __init__(self, master_password: str):
        """Initialize with master password to derive encryption key."""
        self.fernet = self._create_fernet(master_password)
    
    def _create_fernet(self, password: str) -> Fernet:
        """Derive a Fernet key from the master password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=VAULT_SALT,
            iterations=480000,  # High iteration count for security
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
        if not plaintext:
            return ""
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string. Returns plaintext."""
        if not ciphertext:
            return ""
        try:
            return self.fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise ValueError("Invalid master password or corrupted data")
    
    def verify_password(self, test_value: str = "vault-test") -> bool:
        """
        Verify the master password by attempting to decrypt a known test value.
        Used to check if the password is correct before accessing the vault.
        """
        try:
            encrypted = self.encrypt(test_value)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_value
        except Exception:
            return False


def get_crypto(master_password: str) -> VaultCrypto:
    """Factory function to get a VaultCrypto instance."""
    return VaultCrypto(master_password)
