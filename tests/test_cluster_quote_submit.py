from __future__ import annotations

import time

from cluster.cluster_control import get_status, quote_job, submit_job


def test_null_driver_flow():
    spec = {
        "job": "unit",
        "provider": "null",
        "resources": {"gpu": 4, "hours": 1, "mem_gb": 64},
        "data": {},
        "output": {},
        "caps": {"cost_usd_max": 100},
        "audit": {"operator": "tester", "gate": "ALLOW"},
    }
    quote = quote_job(spec)
    assert "cost_usd_est" in quote

    result = submit_job(spec)
    job_id = result["job_id"]
    assert job_id

    done = False
    for _ in range(8):
        status = get_status("null", job_id)
        if status["status"] in ("succeeded", "failed", "canceled"):
            done = True
            break
        time.sleep(0.6)
    assert done
