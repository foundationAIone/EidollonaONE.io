from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import os
import pathlib


@dataclass
class FiatDecision:
    decision: str  # allow|hold|deny|redirect
    reasons: List[str]
    scores: Dict[str, float]  # coherence, ethos_min, risk, uncertainty, ser
    next_review_sec: int = 0
    redirect_account: Optional[str] = None


class FiatGate:
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        jp = (policy.get("logging", {}) or {}).get(
            "journal_path", "consciousness_data/fiat_gate_journal.jsonl"
        )
        self.journal_path = jp
        try:
            pathlib.Path(os.path.dirname(jp)).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _ethos_min(self, ethos: Dict[str, float]) -> float:
        if not ethos:
            return 0.0
        return min(
            float(ethos.get("authenticity", 0) or 0),
            float(ethos.get("integrity", 0) or 0),
            float(ethos.get("responsibility", 0) or 0),
            float(ethos.get("enrichment", 0) or 0),
        )

    def evaluate(
        self, tx: Dict[str, Any], v41_signals: Dict[str, Any], ser_score: float
    ) -> FiatDecision:
        th = self.policy.get("thresholds", {})
        coh = float(v41_signals.get("coherence", 0.0) or 0.0)
        risk = float(v41_signals.get("risk", 1.0) or 1.0)
        unc = float(v41_signals.get("uncertainty", 1.0) or 1.0)
        ethos_min = self._ethos_min(v41_signals.get("ethos", {}) or {})
        ser = float(ser_score or 0.0)

        reasons: List[str] = []
        # Threshold checks
        if coh < float(th.get("coherence_min", 0.0) or 0.0):
            reasons.append(f"coherence<{th.get('coherence_min')}")
        if ethos_min < float(th.get("ethos_min", 0.0) or 0.0):
            reasons.append(f"ethos_min<{th.get('ethos_min')}")
        if risk > float(th.get("risk_max", 1.0) or 1.0):
            reasons.append(f"risk>{th.get('risk_max')}")
        if unc > float(th.get("uncertainty_max", 1.0) or 1.0):
            reasons.append(f"uncertainty>{th.get('uncertainty_max')}")
        if ser < float(th.get("ser_min", 0.0) or 0.0):
            reasons.append(f"ser<{th.get('ser_min')}")

        # Category rules
        categories = (self.policy.get("actions", {}) or {}).get("categories") or []
        cat_decision = None
        for rule in categories:
            try:
                if rule.get("tag") in (tx.get("tags") or []):
                    cat_decision = (rule.get("action"), rule.get("note"))
                    break
            except Exception:
                continue

        # Decision synthesis
        if cat_decision:
            act, note = cat_decision
            if note:
                reasons.append(str(note))
            if act == "deny":
                decision = "deny"
            elif act == "hold":
                decision = "hold"
            elif act == "allow":
                decision = "allow"
            else:
                decision = "hold"
        else:
            decision = "allow"

        # Apply thresholds last (thresholds can override category allow)
        if reasons and decision == "allow":
            decision = "hold"

        # Redirect logic for misaligned: if deny → redirect to reserve
        redirect = None
        if decision == "deny":
            redirect = (self.policy.get("actions", {}) or {}).get(
                "redirect_reserve_account"
            )

        next_review = (
            int((self.policy.get("actions", {}) or {}).get("hold_seconds", 86400))
            if decision == "hold"
            else 0
        )

        dec = FiatDecision(
            decision=decision,
            reasons=reasons or ["ok"],
            scores={
                "coherence": coh,
                "ethos_min": ethos_min,
                "risk": risk,
                "uncertainty": unc,
                "ser": ser,
            },
            next_review_sec=next_review,
            redirect_account=redirect,
        )
        self._log(tx, dec)
        return dec

    def _log(self, tx: Dict[str, Any], dec: FiatDecision) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tx": tx,
            "decision": dec.decision,
            "reasons": dec.reasons,
            "scores": dec.scores,
            "next_review_sec": dec.next_review_sec,
            "redirect_account": dec.redirect_account,
        }
        try:
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
