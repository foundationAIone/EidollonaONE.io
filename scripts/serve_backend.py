"""Local development launcher for the FastAPI HUD service."""
from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        import uvicorn
        from web_interface.server.main import app
    except Exception as exc:  # pragma: no cover - defensive path
        print({"error": "server_boot", "detail": str(exc)})
        sys.exit(0)

    host = os.getenv("HUD_HOST", "127.0.0.1")
    port = int(os.getenv("HUD_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
