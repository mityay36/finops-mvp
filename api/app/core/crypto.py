from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""


class CredentialCipher:
    """Thin wrapper around Fernet for symmetric encryption of credentials."""

    def __init__(self, key: str | None = None) -> None:
        resolved = key or settings.fernet_key
        if not resolved:
            raise CryptoError(
                "FERNET_KEY is not configured. "
                "Generate one with scripts/generate_fernet_key.py and set FERNET_KEY env."
            )
        try:
            self._fernet = Fernet(resolved.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise CryptoError(f"Invalid FERNET_KEY: {exc}") from exc

    def encrypt(self, plaintext: str) -> str:
        if not isinstance(plaintext, str):
            raise CryptoError("plaintext must be a string")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise CryptoError("Failed to decrypt: invalid token or wrong key") from exc


cipher = CredentialCipher()
