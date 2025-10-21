# EidollonaONE Cluster Module

This package provides a uniform interface for job execution across different compute backends. Jobs are described using the `JobSpec` schema and dispatched through provider-specific drivers. All interactions are audited to NDJSON logs under `logs/` to preserve SAFE posture.

## Components

- `cluster.job_spec` — validation helpers for the job specification dictionary.
- `cluster.cluster_control` — orchestration helpers that log to `logs/cluster_audit.ndjson`.
- `cluster.drivers.null_driver` — functional in-memory driver for local testing.
- `cluster.drivers.k8s_driver`, `slurm_driver`, `cloud_driver` — provider stubs awaiting integration.
- `cluster.presets` — ready-made helper for generating compliant specs.

## Usage

```python
from cluster import submit_job
from cluster.presets import minimal_null_job

spec = minimal_null_job("demo-job", gpu=2, hours=1.0)
result = submit_job(spec)
print(result["job_id"])
```
