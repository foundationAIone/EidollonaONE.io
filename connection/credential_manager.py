"""
🔐 Credential Manager Module – EidollonaONE v4.1

Purpose:
Secure management of credentials with strong hashing, optional encryption at rest,
and simple APIs. Designed to operate even when optional subsystems are missing.
"""

from __future__ import annotations

import json
import hashlib
import hmac
import secrets
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

# Optional: use Fernet for encrypt-at-rest of the file
try:
    from cryptography.fernet import Fernet

    FERNET_AVAILABLE = True
except Exception:
    FERNET_AVAILABLE = False

# Fallback logger
import logging

logger = logging.getLogger(__name__)

CREDENTIALS_DIR = Path("credentials")
CREDENTIALS_FILE = CREDENTIALS_DIR / "secure_credentials.json"
KEY_FILE = CREDENTIALS_DIR / "credential_manager.key"

PBKDF2_ITERATIONS_DEFAULT = 200_000
SALT_LENGTH = 16


class CredentialManager:
    def __init__(
        self, storage_path: Optional[Path] = None, encrypt_at_rest: bool = False
    ):
        self.credentials_path = storage_path or CREDENTIALS_FILE
        self.encrypt_at_rest = bool(encrypt_at_rest and FERNET_AVAILABLE)
        self._fernet = self._init_fernet() if self.encrypt_at_rest else None
        self.credentials: Dict[str, Any] = {}
        self._load_credentials()

    def _load_credentials(self) -> None:
        try:
            if not self.credentials_path.exists():
                self.credentials = {}
                return

            if self.encrypt_at_rest and self._fernet:
                try:
                    ciphertext = self.credentials_path.read_bytes()
                    plaintext = self._fernet.decrypt(ciphertext)
                    self.credentials = json.loads(plaintext.decode("utf-8"))
                    return
                except Exception as e:
                    logger.warning(
                        f"Encrypted credentials load failed, falling back to plaintext: {e}"
                    )

            # Plain JSON
            self.credentials = json.loads(
                self.credentials_path.read_text(encoding="utf-8")
            )
        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")
            self.credentials = {}

    def _save_credentials(self) -> None:
        try:
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
            data = json.dumps(self.credentials, indent=2).encode("utf-8")

            if self.encrypt_at_rest and self._fernet:
                ciphertext = self._fernet.encrypt(data)
                self.credentials_path.write_bytes(ciphertext)
            else:
                tmp = self.credentials_path.with_suffix(".tmp")
                tmp.write_bytes(data)
                tmp.replace(self.credentials_path)
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def add_or_update_credential(
        self, service: str, username: str, password: str
    ) -> None:
        salt = secrets.token_bytes(SALT_LENGTH)
        iters = PBKDF2_ITERATIONS_DEFAULT
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iters, dklen=32
        )
        self.credentials[service] = {
            "username": username,
            "hash": digest.hex(),
            "salt": salt.hex(),
            "iters": iters,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        self._save_credentials()

    def get_credential(self, service: str) -> Optional[Dict[str, Any]]:
        return self.credentials.get(service)

    def verify_credential(self, service: str, password_attempt: str) -> bool:
        entry = self.credentials.get(service)
        if not entry:
            return False
        try:
            salt = bytes.fromhex(entry["salt"]) if "salt" in entry else b""
            iters = int(entry.get("iters", PBKDF2_ITERATIONS_DEFAULT))
            expected = bytes.fromhex(entry["hash"]) if "hash" in entry else b""
            attempt = hashlib.pbkdf2_hmac(
                "sha256", password_attempt.encode("utf-8"), salt, iters, dklen=32
            )
            return hmac.compare_digest(attempt, expected)
        except Exception:
            return False

    def remove_credential(self, service: str) -> bool:
        if service in self.credentials:
            del self.credentials[service]
            self._save_credentials()
            return True
        return False

    def list_services(self) -> Dict[str, str]:
        # Return usernames only, mask sensitive parts
        return {
            svc: (entry.get("username") or "")
            for svc, entry in self.credentials.items()
        }

    def _init_fernet(self):
        try:
            CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
            if KEY_FILE.exists():
                key = KEY_FILE.read_bytes()
            else:
                key = Fernet.generate_key()
                KEY_FILE.write_bytes(key)
            return Fernet(key)
        except Exception as e:
            logger.warning(f"Fernet initialization failed: {e}")
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cm = CredentialManager(encrypt_at_rest=False)
    cm.add_or_update_credential("EidollonaWifi", "EidolonAlpha", "secure_password123")
    print("Verify ok:", cm.verify_credential("EidollonaWifi", "secure_password123"))
    print("Verify fail:", cm.verify_credential("EidollonaWifi", "wrong"))
