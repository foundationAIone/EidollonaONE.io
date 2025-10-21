"""
ai_core.probabilistic_quantum_rendering.renderer

High-level rendering facades that sit on top of the SAFE quantum probability
stack.  Whereas :mod:`.models` provides structured data views and
:mod:`.ascii` focuses on terminal visualization, this module focuses on
orchestration:

* Fetching typed QPIR snapshots from the SE4.3 engine (with fallbacks)
* Producing SAFE JSON/HUD payloads
* Rendering ASCII summaries (with optional audit logging)

Everything in here is deterministic, read-only, and SAFE-aligned; it respects
Gate₁₂ and surfaces Reality Alignment (RA) without introducing side effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from .ascii import AsciiConfig, AsciiRenderer
from .models import QPIRSnapshotModel, fetch_snapshot_model

if TYPE_CHECKING:  # pragma: no cover - typing only
	from quantum_probabilistic_information_rendering_system import (  # type: ignore
		RenderConfig as RenderConfigType,
		RenderSnapshot as RenderSnapshotType,
	)
else:  # pragma: no cover - runtime fallback for optional dependency
	RenderConfigType = Any
	RenderSnapshotType = Any


SnapshotInput = Optional[Any]


class QPIRRenderer:
	"""Convenience facade for fetching QPIR snapshots and rendering them."""

	def __init__(
		self,
		qpir_config: Optional[RenderConfigType] = None,
		ascii_config: Optional[AsciiConfig] = None,
	) -> None:
		self._qpir_config = qpir_config
		self._ascii_config = ascii_config
		self._ascii_renderer: Optional[AsciiRenderer] = None

	# ------------------------------------------------------------------
	# Snapshot helpers
	# ------------------------------------------------------------------
	def snapshot(self) -> QPIRSnapshotModel:
		"""Fetch a live snapshot using the configured QPIR settings."""

		return fetch_snapshot_model(self._qpir_config)

	def hud_payload(self, snapshot: SnapshotInput = None) -> Dict[str, Any]:
		"""Return a JSON/HUD-ready dictionary for the supplied snapshot."""

		model = self._ensure_model(snapshot)
		return model.to_payload()

	# ------------------------------------------------------------------
	# ASCII helpers
	# ------------------------------------------------------------------
	def ascii_block(self, snapshot: SnapshotInput = None) -> str:
		"""Render the snapshot as a multi-line ASCII block without printing."""

		renderer = self._ascii()
		payload = self.hud_payload(snapshot)
		return renderer.render_snapshot(payload)

	def print_ascii(self, snapshot: SnapshotInput = None) -> None:
		"""Print the ASCII snapshot and emit the corresponding audit event."""

		renderer = self._ascii()
		payload = self.hud_payload(snapshot)
		renderer.print_snapshot(payload)

	# ------------------------------------------------------------------
	# Internals
	# ------------------------------------------------------------------
	def _ascii(self) -> AsciiRenderer:
		if self._ascii_renderer is None:
			self._ascii_renderer = AsciiRenderer(self._ascii_config)
		return self._ascii_renderer

	def _ensure_model(self, snapshot: SnapshotInput) -> QPIRSnapshotModel:
		if snapshot is None:
			return self.snapshot()
		if isinstance(snapshot, QPIRSnapshotModel):
			return snapshot
		return QPIRSnapshotModel.from_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Functional helpers
# ---------------------------------------------------------------------------
def snapshot_model(config: Optional[RenderConfigType] = None) -> QPIRSnapshotModel:
	"""Fetch a typed snapshot using the global fetch helper."""

	return fetch_snapshot_model(config)


def hud_payload(
	config: Optional[RenderConfigType] = None,
	snapshot: SnapshotInput = None,
) -> Dict[str, Any]:
	"""
	Convenience wrapper returning a HUD-ready payload.

	If *snapshot* is provided it will be normalized into a
	:class:`QPIRSnapshotModel` instance first; otherwise this will fetch a live
	snapshot using the provided configuration.
	"""

	return QPIRRenderer(qpir_config=config).hud_payload(snapshot)


def render_ascii_block(
	config: Optional[RenderConfigType] = None,
	ascii_config: Optional[AsciiConfig] = None,
	snapshot: SnapshotInput = None,
) -> str:
	"""Return an ASCII block representing the snapshot (no printing)."""

	return QPIRRenderer(qpir_config=config, ascii_config=ascii_config).ascii_block(snapshot)


def print_ascii_snapshot(
	config: Optional[RenderConfigType] = None,
	ascii_config: Optional[AsciiConfig] = None,
	snapshot: SnapshotInput = None,
) -> None:
	"""Print the ASCII snapshot, emitting SAFE audit events in the process."""

	QPIRRenderer(qpir_config=config, ascii_config=ascii_config).print_ascii(snapshot)

