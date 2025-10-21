from __future__ import annotations

from ai_core.probabilistic_rendering_engine import ProbabilisticRenderingEngine, RenderRequest
from ai_core.quantum_core.quantum_probabilistic_inference import run_inference


def _signals() -> dict:
    return {
        "coherence": 0.78,
        "impetus": 0.52,
        "risk": 0.22,
        "uncertainty": 0.28,
        "mirror_consistency": 0.67,
        "S_EM": 0.74,
        "ethos": {
            "authenticity": 0.88,
            "integrity": 0.90,
            "responsibility": 0.86,
            "enrichment": 0.89,
        },
    }


def test_render_probability_field_dimensions() -> None:
    engine = ProbabilisticRenderingEngine()
    req = RenderRequest(signals=_signals(), nx=24, ny=24, seed=11)
    resp = engine.render(req)
    assert resp.field.nx == 24
    assert resp.field.ny == 24
    assert len(resp.field.grid) == 24
    assert all(len(row) == 24 for row in resp.field.grid)
    assert all(abs(sum(row) - 1.0) < 1e-6 for row in resp.field.grid)
    assert abs(sum(strategy.weight for strategy in resp.strategies) - 1.0) < 1e-6
    assert isinstance(resp.rec, str) and resp.rec


def test_run_inference_produces_hotspots() -> None:
    engine = ProbabilisticRenderingEngine()
    resp = engine.render(RenderRequest(signals=_signals(), nx=16, ny=16, seed=21))
    report = run_inference(resp.field, resp.strategies, conservatism=0.5, ethos_bias=0.6)
    assert len(report.hotspots) > 0
    assert all("x" in spot and "y" in spot and "value" in spot for spot in report.hotspots)
    assert abs(sum(strategy.weight for strategy in report.adjustments) - 1.0) < 1e-6
    assert report.summary["entropy"] > 0.0
    assert report.summary["peak"] <= 1.0
    assert 0.0 <= report.summary["ouroboros_score"] <= 1.0
    assert isinstance(report.summary.get("ouroboros_metrics"), dict)




