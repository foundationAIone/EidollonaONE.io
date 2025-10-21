"""
EidollonaONE Cluster Module
Drivers: null (sim), k8s (stub), slurm (stub), cloud (stub)
Public API: quote_job, submit_job, get_status, cancel_job
"""
from .cluster_control import quote_job, submit_job, get_status, cancel_job

__all__ = [
	"quote_job",
	"submit_job",
	"get_status",
	"cancel_job",
]
