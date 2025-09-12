"""Encryption Layer Roundtrip Test (ChaCha20-Poly1305 preferred)

Ensures encrypt->decrypt returns original payload for at least one generated key.
Falls back gracefully if cryptography backend absent.
"""

from __future__ import annotations
import pytest
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from connection.encryption_layer import EncryptionLayer


@pytest.mark.parametrize(
    "payload", [b"hello", b"", b"some longer test payload 1234567890"]
)
def test_roundtrip(payload):
    enc = EncryptionLayer()
    key_id = enc.create_encryption_key(profile_name="standard", key_type="symmetric")
    key = enc.encryption_keys[key_id]
    encrypted = enc.encryption_engine.encrypt_data(payload, key)
    # For some algorithms (fallback/XOR) an empty input can result in empty ciphertext; only assert type.
    assert encrypted.encrypted_content is not None
    out = enc.encryption_engine.decrypt_data(encrypted, key)
    assert out == payload, "Roundtrip mismatch"
