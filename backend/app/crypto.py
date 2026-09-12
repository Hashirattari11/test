"""Symmetric encryption for secrets stored at rest (GitHub access tokens).

We use Fernet (AES-128-CBC + HMAC) from the `cryptography` package. The key
lives only in the environment (`TOKEN_ENCRYPTION_KEY`) and never touches the DB.

Generate a key once and set it in your environment:
    python backend/scripts/generate_key.py
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


class TokenCipher:
    def __init__(self, key: str):
        if not key:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY is not set. Generate one with "
                "`python backend/scripts/generate_key.py` and add it to your env."
            )
        # Fernet expects a 32-byte urlsafe-base64 key as bytes.
        self._fernet = Fernet(key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "Failed to decrypt a stored token. The TOKEN_ENCRYPTION_KEY may "
                "have changed since the token was stored."
            ) from exc


_cipher: TokenCipher | None = None


def get_cipher() -> TokenCipher:
    """Lazily build the cipher so importing this module never crashes at import
    time when the key is absent (e.g. during unit tests that don't need it)."""
    global _cipher
    if _cipher is None:
        _cipher = TokenCipher(settings.token_encryption_key)
    return _cipher
