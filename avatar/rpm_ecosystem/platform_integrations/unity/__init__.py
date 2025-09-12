"""Unity platform integration exports

This package provides a unified surface for:
- Unity Consciousness SDK and related enums/config
- Unity-specific avatar controller
- Deterministic Unity export tools

All imports are guarded to keep package import resilient across environments.
"""

from __future__ import annotations

__version__ = "0.1.0"

# SDK and core Unity integration (optional)
try:
    from .unity_sdk import (
        UnityConsciousnessSDK,
        UnityProjectConfig,
        UnityVersion,
        ConsciousnessRenderPipeline,
        UnityConsciousnessFeatures,
    )
except Exception:
    UnityConsciousnessSDK = None  # type: ignore
    UnityProjectConfig = None  # type: ignore
    UnityVersion = None  # type: ignore
    ConsciousnessRenderPipeline = None  # type: ignore
    UnityConsciousnessFeatures = None  # type: ignore

# Avatar controller (optional)
try:
    from .avatar_controller_unity import UnityAvatarController, UnityAvatarConfig
except Exception:
    UnityAvatarController = None  # type: ignore
    UnityAvatarConfig = None  # type: ignore

# Export tools (optional)
try:
    from .export_tools import (
        UnityExportOptions,
        validate_unity_export_config,
        export_unity_avatar,
        generate_and_export_unity_avatar,
    )
except Exception:
    UnityExportOptions = None  # type: ignore
    validate_unity_export_config = None  # type: ignore
    export_unity_avatar = None  # type: ignore
    generate_and_export_unity_avatar = None  # type: ignore

__all__ = [
    name
    for name, obj in [
        ("__version__", __version__),
        # SDK + core
        ("UnityConsciousnessSDK", UnityConsciousnessSDK),
        ("UnityProjectConfig", UnityProjectConfig),
        ("UnityVersion", UnityVersion),
        ("ConsciousnessRenderPipeline", ConsciousnessRenderPipeline),
        ("UnityConsciousnessFeatures", UnityConsciousnessFeatures),
        # Avatar controller
        ("UnityAvatarController", UnityAvatarController),
        ("UnityAvatarConfig", UnityAvatarConfig),
        # Export tools
        ("UnityExportOptions", UnityExportOptions),
        ("validate_unity_export_config", validate_unity_export_config),
        ("export_unity_avatar", export_unity_avatar),
        ("generate_and_export_unity_avatar", generate_and_export_unity_avatar),
    ]
    if obj is not None
]
