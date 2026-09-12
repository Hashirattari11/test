#!/usr/bin/env python3
"""Generate a Fernet key for TOKEN_ENCRYPTION_KEY.

Usage:
    python scripts/generate_key.py
Copy the printed value into your environment (.env locally, Render dashboard in prod).
Keep it stable: if it changes, previously-stored GitHub tokens can't be decrypted.
"""
from cryptography.fernet import Fernet

if __name__ == "__main__":
    print(Fernet.generate_key().decode())
