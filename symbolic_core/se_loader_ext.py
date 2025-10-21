from importlib import import_module
from typing import Any, Dict, List, Optional


class SEEngineLoaderError(RuntimeError):
    """Raised when a symbolic engine cannot be resolved."""


def _module_name(engine_name: str) -> str:
    return f"symbolic_core.{engine_name}"


def _instantiate_engine(name: str, cfg: Dict[str, Any]) -> Any:
    module = import_module(_module_name(name))
    for attr in ("SymbolicEquation43", "WingsAletheia", "SymbolicEngine"):
        engine_cls = getattr(module, attr, None)
        if engine_cls is None:
            continue
        try:
            return engine_cls(cfg)
        except TypeError:
            # Some legacy engines have no config signature.
            return engine_cls()  # type: ignore[call-arg]
    raise SEEngineLoaderError(f"Module '{name}' does not expose a compatible symbolic engine")


def load_se_engine(cfg: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
    """Load the preferred symbolic engine or return evaluated signals when context is given."""

    cfg = dict(cfg or {})
    preferred = cfg.get("engine", "se43_wings")
    tried: List[str] = []
    last_error: Optional[Exception] = None

    context = kwargs.pop("context", None)
    # "iterations" is accepted for compatibility but ignored by the SE4.3 engine.
    kwargs.pop("iterations", None)

    for name in (preferred, "se43_wings", "se4_legacy"):
        if name in tried:
            continue
        tried.append(name)
        try:
            engine = _instantiate_engine(name, cfg)
        except ModuleNotFoundError:
            continue
        except Exception as exc:  # pragma: no cover - rare loader failures
            last_error = exc
            continue

        if context is not None:
            sample = dict(context or {})
            if not hasattr(engine, "evaluate"):
                raise SEEngineLoaderError(
                    f"Loaded engine '{name}' does not provide an evaluate() method"
                )
            return engine.evaluate(sample)  # type: ignore[attr-defined]

        return engine

    if last_error is not None:
        raise SEEngineLoaderError(f"No symbolic engine found. Tried {tried}: {last_error}") from last_error
    raise SEEngineLoaderError(f"No symbolic engine found. Tried {tried}")
