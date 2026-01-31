from __future__ import annotations

from types import SimpleNamespace

import vat_audit_pipeline.core.processors.ods_processor as ods


class DictConfig:
    def __init__(self, data: dict):
        self._data = data

    def get(self, *keys, default=None):
        cur = self._data
        for k in keys:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur


def test_should_use_streaming_large_file(monkeypatch):
    cfg = DictConfig(
        {
            "performance": {
                "memory_monitoring": {
                    "large_file_streaming_mb": 100,
                    "stream_switch_threshold_percent": 75,
                }
            }
        }
    )

    monkeypatch.setattr(ods.os.path, "getsize", lambda _: 150 * 1024 * 1024)

    class _VM:
        percent = 10
        available = 10 * 1024 * 1024 * 1024

    monkeypatch.setattr(ods, "psutil", SimpleNamespace(virtual_memory=lambda: _VM()), raising=False)

    assert ods.should_use_streaming_for_file("dummy.xlsx", cfg) is True


def test_should_use_streaming_low_memory_pressure(monkeypatch):
    cfg = DictConfig(
        {
            "performance": {
                "memory_monitoring": {
                    "large_file_streaming_mb": 100,
                    "stream_switch_threshold_percent": 75,
                }
            }
        }
    )

    monkeypatch.setattr(ods.os.path, "getsize", lambda _: 10 * 1024 * 1024)

    class _VM:
        percent = 10
        available = 10 * 1024 * 1024 * 1024

    monkeypatch.setattr(ods, "psutil", SimpleNamespace(virtual_memory=lambda: _VM()), raising=False)

    assert ods.should_use_streaming_for_file("dummy.xlsx", cfg) is False
