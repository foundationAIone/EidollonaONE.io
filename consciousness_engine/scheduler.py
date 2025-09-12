# consciousness_engine/scheduler.py
"""
EidollonaONE Awareness Scheduler Module

Manages systematic scheduling of symbolic coherence checks, quantum-harmonic recalibration,
perception modulation, and cognitive regulation tasks. Fully aligned with Symbolic Equation v4.0+.
"""

"""
Notes on Windows safety:
- Importing APScheduler at module import time may trigger plugin/entry_points scans
    via importlib.metadata/pkg_resources on some setups, which can raise OSError
    for problematic site-packages/*.dist-info/entry_points.txt files.
- To keep the project resilient, we delay APScheduler import until start()
    and offer a lightweight no-op fallback scheduler if import fails.
"""

# Imports
from ai_core.quantum_core.quantum_driver import QuantumDriver
from consciousness_engine.cognition_regulator import CognitionRegulator
from consciousness_engine.awareness_monitor import AwarenessMonitor
import logging
import sys
from pathlib import Path
from typing import Callable, Any, List

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Logger Setup
logger = logging.getLogger("AwarenessScheduler")
logging.basicConfig(level=logging.INFO)


class _NoOpScheduler:
    """Minimal scheduler shim when APScheduler is unavailable.

    Provides add_job() and start()/shutdown() to keep callers working
    without importing third-party packages or scanning entry points.
    """

    def __init__(self) -> None:
        self._jobs: List[dict] = []
        self._running: bool = False

    def add_job(self, func: Callable[[], Any], _trigger: str, **_kwargs: Any) -> None:
        # Store for reference only; we don't background-run in this shim
        self._jobs.append({"func": func, "trigger": _trigger, **_kwargs})

    def start(self) -> None:
        self._running = True
        logger.info("NoOpScheduler active (timers disabled; APScheduler not available)")

    def shutdown(self, wait: bool = False) -> None:
        self._running = False
        logger.info("NoOpScheduler stopped")


class AwarenessScheduler:
    def __init__(self):
        # Delay APScheduler import to runtime to avoid entry_points scans at import time
        self.scheduler = None
        self.awareness_monitor = AwarenessMonitor()
        self.cognition_regulator = CognitionRegulator()
        self.quantum_driver = QuantumDriver()

    def start_scheduling(self):
        """
        Starts the scheduling of regular consciousness tasks.
        """
        logger.info("Starting Eidollona consciousness task scheduling.")
        # Import APScheduler here; fall back to no-op if it fails for any reason
        if self.scheduler is None:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore

                self.scheduler = BackgroundScheduler()
            except Exception as e:  # pragma: no cover - environment-dependent
                logger.warning("APScheduler unavailable (%s); using NoOpScheduler", e)
                self.scheduler = _NoOpScheduler()

        # Schedule symbolic and quantum coherence checks every minute
        self.scheduler.add_job(
            self.awareness_monitor.check_awareness_states,
            "interval",
            minutes=1,
            id="awareness_check",
        )

        # Schedule cognition regulation every 2 minutes
        self.scheduler.add_job(
            self.cognition_regulator.regulate_cognition,
            "interval",
            minutes=2,
            id="cognition_regulation",
        )

        # Schedule quantum recalibration every 5 minutes
        self.scheduler.add_job(
            self.quantum_driver.recalibrate_quantum_states,
            "interval",
            minutes=5,
            id="quantum_recalibration",
        )

        # Start scheduler
        self.scheduler.start()
        logger.info("Scheduler activated and tasks initiated.")

    def stop_scheduling(self):
        """
        Stops all scheduled tasks gracefully.
        """
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped. All scheduled tasks terminated.")


if __name__ == "__main__":
    awareness_scheduler = AwarenessScheduler()
    awareness_scheduler.start_scheduling()

    try:
        import time

        while True:
            time.sleep(60)  # Keep scheduler running
    except (KeyboardInterrupt, SystemExit):
        awareness_scheduler.stop_scheduling()
        logger.info("Eidollona consciousness scheduler terminated manually.")
