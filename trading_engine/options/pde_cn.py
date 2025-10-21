from __future__ import annotations

from typing import Callable, List, Literal, Optional, Tuple
import math

GridKind = Literal["call", "put", "custom"]


def crank_nicolson_euro(
    kind: GridKind,
    S0: float,
    K: float,
    r: float,
    q: float,
    sigma: float,
    T: float,
    *,
    Smax_mult: float = 4.0,
    M: int = 200,
    N: int = 200,
    payoff: Optional[Callable[[float], float]] = None,
) -> Tuple[float, List[float]]:
    """Finite-difference Crank–Nicolson solver for European payoffs."""

    Smax = Smax_mult * max(S0, K, 1.0)
    M = max(10, int(M))
    N = max(1, int(N))
    dS = Smax / M
    dt = T / N if N > 0 else 1e-6
    S = [i * dS for i in range(M + 1)]

    if kind == "call":
        V = [max(s - K, 0.0) for s in S]
    elif kind == "put":
        V = [max(K - s, 0.0) for s in S]
    else:
        if payoff is None:
            raise ValueError("custom payoff callable required")
        V = [max(0.0, payoff(s)) for s in S]

    for n in range(N):
        a: List[float] = []
        b: List[float] = []
        c: List[float] = []
        rhs = [0.0] * (M - 1)
        t = T - n * dt
        for i in range(1, M):
            si = S[i]
            sig2 = sigma * sigma * si * si
            A = 0.25 * dt * ((sig2 / (dS * dS)) - ((r - q) * si / dS))
            B = -0.5 * dt * ((sig2 / (dS * dS)) + r)
            C = 0.25 * dt * ((sig2 / (dS * dS)) + ((r - q) * si / dS))
            a.append(-A)
            b.append(1.0 - B)
            c.append(-C)
            rhs[i - 1] = A * V[i - 1] + (1.0 + B) * V[i] + C * V[i + 1]

        if kind == "call":
            V0 = 0.0
            Vmax = Smax * math.exp(-q * t) - K * math.exp(-r * t)
            rhs[0] -= (-a[0]) * V0
            rhs[-1] -= (-c[-1]) * Vmax
        elif kind == "put":
            V0 = K * math.exp(-r * t)
            Vmax = 0.0
            rhs[0] -= (-a[0]) * V0
            rhs[-1] -= (-c[-1]) * Vmax

        for i in range(1, M - 1):
            w = a[i] / b[i - 1]
            b[i] -= w * c[i - 1]
            rhs[i] -= w * rhs[i - 1]

        X = [0.0] * (M - 1)
        X[-1] = rhs[-1] / b[-1]
        for i in range(M - 3, -1, -1):
            X[i] = (rhs[i] - c[i] * X[i + 1]) / b[i]

        V = [0.0] + X + [0.0]

    i0 = min(M - 1, max(0, int(S0 / dS)))
    sL = S[i0]
    sR = S[i0 + 1] if i0 + 1 <= M else S[i0]
    vL = V[i0]
    vR = V[i0 + 1] if i0 + 1 <= M else V[i0]
    w = 0.0 if sR == sL else (S0 - sL) / (sR - sL)
    price = (1.0 - w) * vL + w * vR
    return price, V


__all__ = ["crank_nicolson_euro", "GridKind"]
