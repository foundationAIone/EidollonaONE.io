import time

from cluster.cluster_control import cancel_job, get_status, quote_job, submit_job


def _base_spec() -> dict:
    return {
        "job": "test-1",
        "provider": "null",
        "resources": {"gpu": 1, "hours": 0.1, "mem_gb": 1},
        "data": {"task": "echo"},
        "output": {},
        "caps": {"cost_usd_max": 10},
        "audit": {"operator": "pytest", "gate": "ALLOW"},
    }


def test_null_driver_round_trip():
    spec = _base_spec()
    quote = quote_job(spec)
    assert quote["driver"] == "null"

    submission = submit_job(spec)
    job_id = submission["job_id"]

    final = None
    for _ in range(10):
        status = get_status("null", job_id)
        if status["status"] == "succeeded":
            final = status
            break
        time.sleep(0.5)

    assert final is not None, "job did not complete"
    cancel = cancel_job("null", job_id)
    assert cancel["status"] in ("canceled", "succeeded")
