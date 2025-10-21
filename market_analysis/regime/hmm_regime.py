from __future__ import annotations

from typing import Dict, List
import math


class SimpleHMM:
    """Minimal 2-state Gaussian HMM with crude Baum–Welch-style updates."""

    def __init__(self) -> None:
        self.pi: List[float] = [0.5, 0.5]
        self.A: List[List[float]] = [[0.95, 0.05], [0.05, 0.95]]
        self.mu: List[float] = [0.0, 0.0]
        self.sig: List[float] = [0.01, 0.04]

    @staticmethod
    def _norm(x: float, mean: float, var: float) -> float:
        v = max(1e-9, var)
        return (1.0 / math.sqrt(2.0 * math.pi * v)) * math.exp(-0.5 * ((x - mean) * (x - mean)) / v)

    def fit(self, returns: List[float], iters: int = 10) -> None:
        if not returns:
            return
        n = len(returns)
        for _ in range(max(1, iters)):
            alpha: List[List[float]] = [[0.0, 0.0] for _ in range(n)]
            for i, x in enumerate(returns):
                b0 = self._norm(x, self.mu[0], self.sig[0])
                b1 = self._norm(x, self.mu[1], self.sig[1])
                if i == 0:
                    alpha[0][0] = self.pi[0] * b0
                    alpha[0][1] = self.pi[1] * b1
                else:
                    a0 = alpha[i - 1][0] * self.A[0][0] + alpha[i - 1][1] * self.A[1][0]
                    a1 = alpha[i - 1][0] * self.A[0][1] + alpha[i - 1][1] * self.A[1][1]
                    alpha[i][0] = a0 * b0
                    alpha[i][1] = a1 * b1
                s = alpha[i][0] + alpha[i][1]
                if s == 0.0:
                    alpha[i][0] = 0.5
                    alpha[i][1] = 0.5
                else:
                    alpha[i][0] /= s
                    alpha[i][1] /= s
            gamma = alpha
            g0_total = sum(g[0] for g in gamma)
            g1_total = sum(g[1] for g in gamma)
            denom0 = g0_total or 1.0
            denom1 = g1_total or 1.0
            self.pi[0] = gamma[0][0]
            self.pi[1] = gamma[0][1]
            if g0_total > 0.0:
                m0 = sum(gamma[i][0] * returns[i] for i in range(n)) / denom0
                v0 = sum(gamma[i][0] * (returns[i] - m0) * (returns[i] - m0) for i in range(n)) / denom0
                self.mu[0] = m0
                self.sig[0] = max(1e-6, v0)
            if g1_total > 0.0:
                m1 = sum(gamma[i][1] * returns[i] for i in range(n)) / denom1
                v1 = sum(gamma[i][1] * (returns[i] - m1) * (returns[i] - m1) for i in range(n)) / denom1
                self.mu[1] = m1
                self.sig[1] = max(1e-6, v1)

    def infer(self, returns: List[float]) -> Dict[str, float]:
        if not returns:
            return {
                "p_regime0": 0.5,
                "p_regime1": 0.5,
                "mu0": self.mu[0],
                "mu1": self.mu[1],
                "sig0": self.sig[0],
                "sig1": self.sig[1],
            }
        x = returns[-1]
        b0 = self.pi[0] * self._norm(x, self.mu[0], self.sig[0])
        b1 = self.pi[1] * self._norm(x, self.mu[1], self.sig[1])
        s = b0 + b1 or 1.0
        return {
            "p_regime0": b0 / s,
            "p_regime1": b1 / s,
            "mu0": self.mu[0],
            "mu1": self.mu[1],
            "sig0": self.sig[0],
            "sig1": self.sig[1],
        }


__all__ = ["SimpleHMM"]
