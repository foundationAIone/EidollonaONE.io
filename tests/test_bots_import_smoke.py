def test_canonical_namespace():
    import ai_core.bots as b

    assert hasattr(
        b, "TaskExecutorBot"
    ), "TaskExecutorBot not exported from ai_core.bots"


def test_legacy_shim():
    import importlib

    try:
        m = importlib.import_module("ai_core.trading_bots")
        assert hasattr(
            m, "TaskExecutorBot"
        ), "TaskExecutorBot not exported from legacy shim"
    except ModuleNotFoundError:
        # acceptable once shim is removed
        pass
