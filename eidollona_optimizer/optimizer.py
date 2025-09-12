# -*- coding: utf-8 -*-
"""
Eidollona Optimizer (SAFE, non-destructive)
- Cleans temp and caches without touching user libraries or project files.
- Dynamically adapts based on symbolic equation alignment/coherence metrics.
- Power plan toggle stubs for heavy render phases (Windows only, simulated).

Symbolic alignment:
- We derive an "operational load" from the SymbolicEquation coherence level.
    Higher coherence implies less need for aggressive cleanup to avoid disrupting
    harmonic stability; lower coherence allows slightly more aggressive cache/temp cleanup.
"""
from __future__ import annotations
from typing import Dict, Any, List
import os
import shutil
import tempfile
from contextlib import contextmanager

# Lazy import of symbolic core inside functions to avoid noisy global init
from contextlib import redirect_stdout, redirect_stderr
import io


def _quiet_get_symbolic_equation_instance():
    """Import and return get_symbolic_equation_instance with console suppressed."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            from symbolic_core.symbolic_equation import get_symbolic_equation_instance  # type: ignore
        return get_symbolic_equation_instance
    except Exception:
        # Retry without suppression just in case (still safe)
        from symbolic_core.symbolic_equation import get_symbolic_equation_instance  # type: ignore

        return get_symbolic_equation_instance


SAFE_DELETE_DIRS = [
    os.environ.get("TEMP") or tempfile.gettempdir(),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
]

PROTECT_DIR_PREFIXES = [
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Pictures"),
    os.path.expanduser("~\\Music"),
    os.path.expanduser("~\\Videos"),
    os.path.expanduser("~\\Downloads"),
    os.path.expanduser("~\\Desktop"),
]


def _is_protected(path: str) -> bool:
    p = os.path.abspath(path)
    for pref in PROTECT_DIR_PREFIXES:
        if pref and p.startswith(os.path.abspath(pref)):
            return True
    return False


def clean_temp() -> Dict[str, Any]:
    """Remove files in known temp locations, skipping protected paths and handling errors safely."""
    removed: List[str] = []
    errors: List[str] = []
    for base in SAFE_DELETE_DIRS:
        if not base or _is_protected(base):
            continue
        if not os.path.exists(base):
            continue
        try:
            for entry in os.listdir(base):
                full = os.path.join(base, entry)
                try:
                    if os.path.isfile(full) or os.path.islink(full):
                        os.remove(full)
                        removed.append(full)
                    elif os.path.isdir(full):
                        shutil.rmtree(full, ignore_errors=True)
                        removed.append(full)
                except Exception:
                    errors.append(full)
        except Exception:
            errors.append(base)
    return {"removed_count": len(removed), "errors_count": len(errors)}


def set_high_performance_powerplan(simulate: bool = True) -> Dict[str, Any]:
    """Stub for toggling Windows power plan; simulate by default."""
    return {"status": "simulated", "mode": "high_performance", "simulate": simulate}


def restore_powerplan(simulate: bool = True) -> Dict[str, Any]:
    """Stub to restore original power plan; simulate by default."""
    return {"status": "simulated", "mode": "restore", "simulate": simulate}


@contextmanager
def high_performance_phase():
    """
    Context manager that simulates toggling high-performance power plan
    during heavy GPU render phases; always reverts.
    """
    try:
        set_high_performance_powerplan(simulate=True)
        yield
    finally:
        restore_powerplan(simulate=True)


def get_symbolic_load() -> float:
    """
    Compute an operational load in [0,1] from symbolic coherence metrics.

    Mapping rationale (symbolic -> ops):
    - coherence_level (0..1) reflects internal harmonic alignment.
      We treat load ≈ 1 - coherence_level (lower coherence ⇒ higher load on the system)
      to balance cleanup aggressiveness cautiously.
    - If coherence_level unavailable, fall back to 0.5 (neutral).
    """
    try:
        get_eq = _quiet_get_symbolic_equation_instance()
        eq = get_eq()
        # Prefer lightweight metrics accessor if present
        if hasattr(eq, "get_consciousness_metrics"):
            metrics = eq.get_consciousness_metrics()
            coh = float(metrics.get("coherence_level", 0.5))
        else:
            summary = (
                eq.get_current_state_summary()
                if hasattr(eq, "get_current_state_summary")
                else {}
            )
            coh = float(summary.get("coherence_level", 0.5))
        load = 1.0 - max(0.0, min(1.0, coh))
        return float(max(0.0, min(1.0, load)))
    except Exception:
        return 0.5


def adaptive_cleanup() -> Dict[str, Any]:
    """
    Dynamically choose cleanup intensity based on symbolic operational load.
    - Low load (coherence high): minimal cleanup to avoid disrupting stable resonance.
    - High load (coherence low): increase cleanup to relieve environmental pressure.
    Always non-destructive and never touches protected/user/project paths.
    """
    load = get_symbolic_load()
    result = {"load": load, "actions": []}

    # Always safe temp cleanup
    temp_res = clean_temp()
    result["actions"].append({"action": "clean_temp", **temp_res})

    # Example cache directories (best-effort); scale with load threshold
    # We use a two-tier approach: only clean caches when load is high enough to benefit.
    if load >= 0.5:
        cache_dirs = [
            os.path.join(os.environ.get("APPDATA", ""), "Code", "Cache"),
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Microsoft",
                "Windows",
                "Explorer",
                "thumbcache",
            ),
        ]
        removed = 0
        errors = 0
        for cdir in cache_dirs:
            if not cdir or _is_protected(cdir) or not os.path.exists(cdir):
                continue
            try:
                for entry in os.listdir(cdir):
                    full = os.path.join(cdir, entry)
                    try:
                        if os.path.isfile(full) or os.path.islink(full):
                            os.remove(full)
                            removed += 1
                        elif os.path.isdir(full):
                            shutil.rmtree(full, ignore_errors=True)
                            removed += 1
                    except Exception:
                        errors += 1
            except Exception:
                errors += 1
        result["actions"].append(
            {"action": "clean_caches", "removed_count": removed, "errors_count": errors}
        )

    return result
