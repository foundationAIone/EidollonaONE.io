"""
Platform Integrations - Cross-platform avatar implementations

Exports available integration facades for Unity, Unreal, WebXR, and Mobile.
All imports are optional; missing integrations are reported via AVAILABLE_INTEGRATIONS.
"""

__all__ = ["AVAILABLE_INTEGRATIONS"]

# Capability manifest updated at import time
AVAILABLE_INTEGRATIONS = {
    "unity": False,
    "unreal": False,
    "webxr": False,
    "mobile": False,
}

# Unity integration (optional)
try:
    from .unity.avatar_controller_unity import UnityAvatarController, UnityAvatarConfig  # type: ignore

    __all__.extend(["UnityAvatarController", "UnityAvatarConfig"])
    AVAILABLE_INTEGRATIONS["unity"] = True
except Exception as _unity_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["unity"] = False

# Unreal integration (optional)
try:
    from .unreal import (
        MetaHumanConsciousnessIntegration,
        MetaHumanConfig,
        MetaHumanQuality,
        ConsciousnessExpressionMode,
        create_integration as create_unreal_integration,
    )  # type: ignore

    __all__.extend(
        [
            "MetaHumanConsciousnessIntegration",
            "MetaHumanConfig",
            "MetaHumanQuality",
            "ConsciousnessExpressionMode",
            "create_unreal_integration",
        ]
    )
    AVAILABLE_INTEGRATIONS["unreal"] = True
except Exception as _unreal_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["unreal"] = False

# WebXR integration (optional wrapper)
try:
    from ..vr_ar_integration.webxr_integration import (
        WebXRIntegration,
        WebXRSessionConfig,
        WebXRSessionMode,
        WebXRFeature,
        WebXRReferenceSpace,
    )  # type: ignore

    __all__.extend(
        [
            "WebXRIntegration",
            "WebXRSessionConfig",
            "WebXRSessionMode",
            "WebXRFeature",
            "WebXRReferenceSpace",
        ]
    )
    AVAILABLE_INTEGRATIONS["webxr"] = True
except Exception as _webxr_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["webxr"] = False

# Mobile integrations (optional)
try:
    from .mobile import ARKitIntegration, ARCoreIntegration, MobileFaceTracker  # type: ignore

    __all__.extend(["ARKitIntegration", "ARCoreIntegration", "MobileFaceTracker"])
    AVAILABLE_INTEGRATIONS["mobile"] = True
except Exception as _mobile_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["mobile"] = False
