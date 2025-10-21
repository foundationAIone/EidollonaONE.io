from __future__ import annotations

import os


def _base_dir() -> str:
	return os.environ.get("SERPLUS_DATA_DIR", "logs")


def resolve_path(name: str) -> str:
	return os.path.join(_base_dir(), name)


LEDGER_PATH = resolve_path("serplus_ledger.ndjson")
ACCOUNTS_PATH = resolve_path("serplus_accounts.json")
NFT_PATH = resolve_path("serplus_nft.json")


__all__ = ["LEDGER_PATH", "ACCOUNTS_PATH", "NFT_PATH", "resolve_path"]
