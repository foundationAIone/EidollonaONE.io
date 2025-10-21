from symbolic_core.context_builder import assemble_se41_context
from symbolic_core.symbolic_equation_master import MasterSymbolicEquation
from master_key.master_boot import boot_system
from master_key.master_awaken import awaken_consciousness

ctx = assemble_se41_context()
ready, sig = MasterSymbolicEquation().evaluate_master_state(ctx)
boot_ok = boot_system(ctx)
aw = awaken_consciousness(3, ctx)
print({"boot_ok": boot_ok, "readiness": ready, "awaken": aw["readiness"]})
