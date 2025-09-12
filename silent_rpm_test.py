"""
Silent RPM import test

Converted to a proper pytest test to avoid SystemExit during collection.
"""

import os
import sys
from pathlib import Path
import warnings


def test_rpm_ecosystem_imports():
    """Ensure rpm_ecosystem imports cleanly and exposes key symbols."""
    warnings.filterwarnings("ignore")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    # Add avatar package path for imports
    avatar_path = Path(__file__).parent / "avatar"
    if str(avatar_path) not in sys.path:
        sys.path.insert(0, str(avatar_path))

    # Perform imports via canonical path
    import avatar.rpm_ecosystem as rpm_ecosystem  # canonical
    from avatar.rpm_ecosystem import EcosystemManager, AvatarConfig  # type: ignore

    # Basic assertions
    assert rpm_ecosystem is not None
    assert EcosystemManager is not None
    assert AvatarConfig is not None
