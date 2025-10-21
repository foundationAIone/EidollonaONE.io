"""
Platform Integrations - Cross-platform avatar implementations

Exports available integration facades for Unity, Unreal, WebXR, and Mobile.
All imports are optional; missing integrations are reported via AVAILABLE_INTEGRATIONS.
"""

from typing import Any

_exports: list[str] = ["AVAILABLE_INTEGRATIONS"]

# Capability manifest updated at import time
AVAILABLE_INTEGRATIONS = {
    "unity": False,
    "unreal": False,
    "webxr": False,
    "mobile": False,
}

# Unity integration (optional)
try:
    from .unity import avatar_controller_unity as _unity_mod  # type: ignore

    _exports.extend(["UnityAvatarController", "UnityAvatarConfig"])
    UnityAvatarController = _unity_mod.UnityAvatarController
    UnityAvatarConfig = _unity_mod.UnityAvatarConfig
    AVAILABLE_INTEGRATIONS["unity"] = True
except Exception as _unity_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["unity"] = False

# Unreal integration (optional)
try:
    from . import unreal as _unreal_mod  # type: ignore

    _unreal_exports = {
        "MetaHumanConsciousnessIntegration": "MetaHumanConsciousnessIntegration",
        "MetaHumanConfig": "MetaHumanConfig",
        "MetaHumanQuality": "MetaHumanQuality",
        "ConsciousnessExpressionMode": "ConsciousnessExpressionMode",
        "create_unreal_integration": "create_integration",
    }
    _unreal_missing = [
        alias for alias, attr_name in _unreal_exports.items() if not hasattr(_unreal_mod, attr_name)
    ]
    if _unreal_missing:
        AVAILABLE_INTEGRATIONS["unreal"] = False
    else:
        _exports.extend(_unreal_exports.keys())
        MetaHumanConsciousnessIntegration = getattr(_unreal_mod, "MetaHumanConsciousnessIntegration")
        MetaHumanConfig = getattr(_unreal_mod, "MetaHumanConfig")
        MetaHumanQuality = getattr(_unreal_mod, "MetaHumanQuality")
        ConsciousnessExpressionMode = getattr(_unreal_mod, "ConsciousnessExpressionMode")
        create_unreal_integration = getattr(_unreal_mod, "create_integration")
        AVAILABLE_INTEGRATIONS["unreal"] = True
except Exception as _unreal_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["unreal"] = False

# WebXR integration (optional wrapper)
try:
    from ..vr_ar_integration import webxr_integration as _webxr_mod  # type: ignore

    required_attrs = [
        "WebXRIntegration",
        "WebXRSessionConfig",
        "WebXRSessionMode",
        "WebXRFeature",
        "WebXRReferenceSpace",
    ]
    if all(hasattr(_webxr_mod, attr) for attr in required_attrs):
        from typing import cast as _cast_any

        _exports.extend(required_attrs)
        _webxr_any = _cast_any(Any, _webxr_mod)
        WebXRIntegration = _webxr_any.WebXRIntegration
        WebXRSessionConfig = _webxr_any.WebXRSessionConfig
        WebXRSessionMode = _webxr_any.WebXRSessionMode
        WebXRFeature = _webxr_any.WebXRFeature
        WebXRReferenceSpace = _webxr_any.WebXRReferenceSpace
        AVAILABLE_INTEGRATIONS["webxr"] = True
    else:
        AVAILABLE_INTEGRATIONS["webxr"] = False

        class WebXRSessionConfig:  # type: ignore[override]
            def __init__(self, **kwargs):
                self.params = dict(kwargs)

        class WebXRSessionMode:  # type: ignore[override]
            IMMERSIVE = "immersive"
            INLINE = "inline"

        class WebXRFeature:  # type: ignore[override]
            POSITIONAL_TRACKING = "positional_tracking"
            HAND_TRACKING = "hand_tracking"

        class WebXRReferenceSpace:  # type: ignore[override]
            LOCAL = "local"
            STAGE = "stage"

        class WebXRIntegration:  # type: ignore[override]
            def __init__(self, **_kwargs):
                self.ready = False

            def connect(self) -> bool:
                return False

        _exports.extend(required_attrs)
except Exception as _webxr_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["webxr"] = False

# Mobile integrations (optional)
try:
    from . import mobile as _mobile_mod  # type: ignore

    _mobile_exports = {
        "ARKitIntegration": "ARKitIntegration",
        "ARCoreIntegration": "ARCoreIntegration",
        "MobileFaceTracker": "MobileFaceTracker",
    }
    _mobile_missing = [
        alias for alias, attr_name in _mobile_exports.items() if not hasattr(_mobile_mod, attr_name)
    ]
    if _mobile_missing:
        AVAILABLE_INTEGRATIONS["mobile"] = False
    else:
        _exports.extend(_mobile_exports.keys())
        ARKitIntegration = getattr(_mobile_mod, "ARKitIntegration")
        ARCoreIntegration = getattr(_mobile_mod, "ARCoreIntegration")
        MobileFaceTracker = getattr(_mobile_mod, "MobileFaceTracker")
        AVAILABLE_INTEGRATIONS["mobile"] = True
except Exception as _mobile_err:  # noqa: F841
    AVAILABLE_INTEGRATIONS["mobile"] = False

__all__: tuple[str, ...] = tuple(_exports)  # pyright: ignore[reportUnsupportedDunderAll]
