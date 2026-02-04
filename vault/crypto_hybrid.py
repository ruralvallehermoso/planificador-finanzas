"""
Advanced hybrid encryption module using RSA (asymmetric) and AES-GCM (symmetric).
Provides HybridCrypto class for managing keys and encrypting data.
"""

import os
import base64
from typing import Tuple, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.backends import default_backend


class HybridCrypto:
    """
    Handles hybrid encryption:
    1. Data is encrypted with a symmetric key (DEK) using AES-256-GCM.
    2. The DEK is encrypted with an RSA public key.
    3. The RSA private key is encrypted with the master password (using Argon2id + AES-GCM).
    """

    def __init__(self):
        self.backend = default_backend()

    # ============= Key Generation =============

    def generate_rsa_keypair(self) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Generate a new RSA-4096 key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=self.backend
        )
        return private_key, private_key.public_key()

    def generate_dek(self) -> bytes:
        """Generate a random 32-byte Data Encryption Key (AES-256)."""
        return os.urandom(32)

    # ============= Master Password Protection =============

    def encrypt_private_key(self, private_key: rsa.RSAPrivateKey, master_password: str) -> str:
        """
        Encrypt the RSA private key using the master password.
        Uses Argon2id for KDF and AES-GCM for encryption.
        Returns format: salt.nonce.ciphertext (all base64)
        """
        # 1. Derive key from password
        salt = os.urandom(16)
        kdf = Argon2id(
            salt=salt,
            length=32,
            iterations=2,
            lanes=4,
            memory_cost=65536,
            ad=None,
            secret=None,
        )
        derived_key = kdf.derive(master_password.encode())

        # 2. Serialize private key to bytes
        pem_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # 3. Encrypt with AES-GCM
        nonce = os.urandom(12)
        cipher = Cipher(algorithms.AES(derived_key), modes.GCM(nonce), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(pem_bytes) + encryptor.finalize()
        tag = encryptor.tag

        # 4. Pack result
        # Format: salt.nonce.tag.ciphertext
        parts = [salt, nonce, tag, ciphertext]
        return ".".join(base64.urlsafe_b64encode(p).decode() for p in parts)

    def decrypt_private_key(self, encrypted_blob: str, master_password: str) -> rsa.RSAPrivateKey:
        """
        Decrypt the RSA private key using the master password.
        """
        try:
            parts = [base64.urlsafe_b64decode(p) for p in encrypted_blob.split(".")]
            if len(parts) != 4:
                raise ValueError("Invalid blob format")
            
            salt, nonce, tag, ciphertext = parts

            # 1. Derive key
            kdf = Argon2id(
                salt=salt,
                length=32,
                iterations=2,
                lanes=4,
                memory_cost=65536,
                ad=None,
                secret=None,
            )
            derived_key = kdf.derive(master_password.encode())

            # 2. Decrypt
            cipher = Cipher(algorithms.AES(derived_key), modes.GCM(nonce, tag), backend=self.backend)
            decryptor = cipher.decryptor()
            pem_bytes = decryptor.update(ciphertext) + decryptor.finalize()

            # 3. Load Key
            return serialization.load_pem_private_key(pem_bytes, password=None, backend=self.backend)
            
        except Exception as e:
            raise ValueError("Invalid password or corrupted key data") from e

    # ============= DEK Management =============

    def encrypt_dek(self, dek: bytes, public_key: rsa.RSAPublicKey) -> str:
        """
        Encrypt the DEK with the RSA public key.
        Returns base64 string.
        """
        encrypted = public_key.encrypt(
            dek,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_dek(self, encrypted_dek: str, private_key: rsa.RSAPrivateKey) -> bytes:
        """Decrypt the DEK with the RSA private key."""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_dek)
        return private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    # ============= Data Encryption (Symmetric) =============

    def encrypt_data(self, data: str, dek: bytes) -> str:
        """
        Encrypt string data using AES-256-GCM with the DEK.
        Returns: nonce.tag.ciphertext (base64)
        """
        if not data:
            return ""
            
        nonce = os.urandom(12)
        cipher = Cipher(algorithms.AES(dek), modes.GCM(nonce), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data.encode()) + encryptor.finalize()
        tag = encryptor.tag

        parts = [nonce, tag, ciphertext]
        return ".".join(base64.urlsafe_b64encode(p).decode() for p in parts)

    def decrypt_data(self, encrypted_blob: str, dek: bytes) -> str:
        """Decrypt string data using AES-256-GCM with the DEK."""
        if not encrypted_blob:
            return ""
            
        try:
            parts = [base64.urlsafe_b64decode(p) for p in encrypted_blob.split(".")]
            if len(parts) != 3:
                # Fallback for legacy Fernet if needed, or raise error
                raise ValueError("Invalid data format")
                
            nonce, tag, ciphertext = parts
            
            cipher = Cipher(algorithms.AES(dek), modes.GCM(nonce, tag), backend=self.backend)
            decryptor = cipher.decryptor()
            return (decryptor.update(ciphertext) + decryptor.finalize()).decode()
            
        except Exception:
            raise ValueError("Decryption failed")

    # ============= Visualization Helpers =============
    
    def serialize_public_key(self, public_key: rsa.RSAPublicKey) -> str:
        """Export public key to PEM string."""
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode()


# Global instance manager
class VaultSession:
    """Manages the active vault session with keys in memory."""
    def __init__(self):
        self.private_key: Optional[rsa.RSAPrivateKey] = None
        self.public_key: Optional[rsa.RSAPublicKey] = None
        self.dek: Optional[bytes] = None
        self.crypto = HybridCrypto()

    def is_active(self) -> bool:
        return self.dek is not None and self.private_key is not None

    def load_keys(self, encrypted_priv_key: str, encrypted_dek: str, master_password: str):
        """Unlock the vault: Decrypt private key, then decrypt DEK."""
        self.private_key = self.crypto.decrypt_private_key(encrypted_priv_key, master_password)
        self.public_key = self.private_key.public_key()
        self.dek = self.crypto.decrypt_dek(encrypted_dek, self.private_key)

    def clear(self):
        self.private_key = None
        self.public_key = None
        self.dek = None
