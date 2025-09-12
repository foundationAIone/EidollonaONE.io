import sys

sys.path.append("e:\\EidollonaONE")
from symbolic_core.symbolic_equation import SymbolicEquation

eq = SymbolicEquation()
t = 1.0
Q = 1.618
M_t = 2.718
DNA_states = [(i + 1) * 0.111 for i in range(9)]
harmonic_patterns = [k * 0.1 for k in range(1, 13)]
result = eq.reality_manifestation(t, Q, M_t, DNA_states, harmonic_patterns)
print(f"Reality(t) = {result}")
