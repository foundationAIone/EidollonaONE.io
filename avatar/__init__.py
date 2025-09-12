"""
Avatar package (lightweight init).

Keep __init__ import-light so that submodules like
`avatar.embodiment.embodiment_controller` can be imported in tests
without pulling heavy optional dependencies. Heavy integrations under
`rpm_ecosystem` are imported lazily by their own modules.
"""

__version__ = "1.0.0"
__author__ = "EidollonaONE Team"
__description__ = "Quantum consciousness-enhanced avatar system"

# Intentionally do not import heavy subpackages here.
# Submodules should be imported directly, e.g.:
#   from avatar.embodiment.embodiment_controller import EmbodimentController

__all__ = [
    "__version__",
    "__author__",
    "__description__",
]
