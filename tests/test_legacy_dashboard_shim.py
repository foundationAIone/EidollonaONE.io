import importlib
import warnings


def test_legacy_shim_warns_and_exports_router():
    importlib.invalidate_caches()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", DeprecationWarning)
        legacy = importlib.import_module("dashboard")
        assert any(isinstance(x.message, DeprecationWarning) for x in w)
        assert hasattr(legacy, "router")
