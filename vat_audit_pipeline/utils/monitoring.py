"""Resource monitoring helpers.

This module provides lightweight, optional observability utilities.
It is designed to be safe to import even when optional dependencies
(e.g. psutil) are not available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_import_psutil():
    try:
        import psutil  # type: ignore

        return psutil
    except Exception:
        return None


@dataclass
class ResourceMonitor:
    """Collects point-in-time samples of process and system resources."""

    memory_samples: List[Dict[str, Any]] = field(default_factory=list)
    cpu_samples: List[Dict[str, Any]] = field(default_factory=list)

    def sample_memory(self) -> Optional[Dict[str, Any]]:
        psutil = _safe_import_psutil()
        if psutil is None:
            return None

        process = psutil.Process()
        mem = process.memory_info()
        sample = {
            "rss_mb": mem.rss / 1024 / 1024,
            "vms_mb": mem.vms / 1024 / 1024,
            "percent": process.memory_percent(),
        }
        self.memory_samples.append(sample)
        return sample

    def sample_cpu(self) -> Optional[Dict[str, Any]]:
        psutil = _safe_import_psutil()
        if psutil is None:
            return None

        sample = {
            "system_percent": psutil.cpu_percent(interval=None),
            "logical_cores": psutil.cpu_count(logical=True),
        }
        self.cpu_samples.append(sample)
        return sample

    def _summarize_series(self, series: List[float]) -> Dict[str, float]:
        if not series:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        return {
            "min": float(min(series)),
            "max": float(max(series)),
            "avg": float(sum(series) / len(series)),
        }

    def generate_report(self) -> Dict[str, Any]:
        rss_series = [float(s.get("rss_mb", 0.0)) for s in self.memory_samples]
        cpu_series = [float(s.get("system_percent", 0.0)) for s in self.cpu_samples]

        return {
            "memory": {
                "rss_mb": self._summarize_series(rss_series),
                "samples": len(self.memory_samples),
            },
            "cpu": {
                "system_percent": self._summarize_series(cpu_series),
                "samples": len(self.cpu_samples),
            },
        }


def write_resource_report(report: Dict[str, Any], output_path: str | Path) -> str:
    """Write a JSON resource report to disk (best-effort)."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return str(path)
