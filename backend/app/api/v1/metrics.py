import time

import psutil
from fastapi import APIRouter

router = APIRouter(prefix="/metrics", tags=["metrics"])

_start_time = time.time()

_metrics: dict = {
    "requests_total": 0,
    "requests_by_status": {},
    "requests_by_endpoint": {},
    "jobs_submitted": 0,
    "jobs_completed": 0,
    "jobs_failed": 0,
}


@router.get("")
def metrics():
    """Prometheus-compatible metrics endpoint"""
    process = psutil.Process()
    mem = process.memory_info()
    return {
        "uptime_seconds": round(time.time() - _start_time, 2),
        "memory_rss_mb": round(mem.rss / 1024 / 1024, 2),
        "memory_vms_mb": round(mem.vms / 1024 / 1024, 2),
        "cpu_percent": process.cpu_percent(),
        "open_files": len(process.open_files()),
        "threads": process.num_threads(),
        **_metrics,
    }


def increment_requests(status: int, endpoint: str):
    _metrics["requests_total"] += 1
    _metrics["requests_by_status"][str(status)] = (
        _metrics["requests_by_status"].get(str(status), 0) + 1
    )
    _metrics["requests_by_endpoint"][endpoint] = (
        _metrics["requests_by_endpoint"].get(endpoint, 0) + 1
    )
