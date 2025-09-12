"""
Avatar package

Keep this package lightweight at import time to avoid pulling heavy optional
dependencies during simple unit tests (e.g., embodiment controller).

Downstream modules should import subpackages directly, e.g.:
    from avatar.embodiment.embodiment_controller import EmbodimentController

Heavy integrations under rpm_ecosystem should be imported explicitly by
consumers that need them, not via package import side-effects.
"""

__version__ = "1.0.0"
__author__ = "EidollonaONE Team"
__description__ = "Eidollona avatar system (lightweight package init)"

__all__ = []
