"""
Tests for the vault crypto module.
Run with: python -m pytest test_crypto.py -v
"""

import pytest
from crypto import VaultCrypto, get_crypto


class TestVaultCrypto:
    """Tests for the VaultCrypto class."""
    
    def test_encrypt_decrypt_basic(self):
        """Test basic encryption and decryption."""
        crypto = get_crypto("test-password-123")
        
        original = "my-secret-password"
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == original
        assert encrypted != original
    
    def test_encrypt_produces_different_output(self):
        """Test that same plaintext produces different ciphertext each time."""
        crypto = get_crypto("test-password")
        
        encrypted1 = crypto.encrypt("secret")
        encrypted2 = crypto.encrypt("secret")
        
        # Fernet includes random IV, so ciphertexts should differ
        assert encrypted1 != encrypted2
    
    def test_different_passwords_produce_different_outputs(self):
        """Test that different passwords produce different encrypted outputs."""
        crypto1 = get_crypto("password1")
        crypto2 = get_crypto("password2")
        
        encrypted1 = crypto1.encrypt("secret")
        encrypted2 = crypto2.encrypt("secret")
        
        assert encrypted1 != encrypted2
    
    def test_wrong_password_fails_decrypt(self):
        """Test that decryption with wrong password fails."""
        crypto1 = get_crypto("correct-password")
        crypto2 = get_crypto("wrong-password")
        
        encrypted = crypto1.encrypt("secret")
        
        with pytest.raises(ValueError, match="Invalid master password"):
            crypto2.decrypt(encrypted)
    
    def test_empty_string_handling(self):
        """Test that empty strings are handled correctly."""
        crypto = get_crypto("test")
        
        assert crypto.encrypt("") == ""
        assert crypto.decrypt("") == ""
    
    def test_unicode_support(self):
        """Test encryption of unicode characters."""
        crypto = get_crypto("test")
        
        original = "Contraseña con ñ y 日本語"
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == original
    
    def test_verify_password_success(self):
        """Test password verification with correct password."""
        crypto = get_crypto("correct-password")
        assert crypto.verify_password() is True
    
    def test_long_password(self):
        """Test with a very long password."""
        long_password = "a" * 1000
        crypto = get_crypto(long_password)
        
        encrypted = crypto.encrypt("secret")
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == "secret"
    
    def test_special_characters_in_secret(self):
        """Test encryption of special characters."""
        crypto = get_crypto("test")
        
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?\n\t"
        encrypted = crypto.encrypt(special)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == special


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
