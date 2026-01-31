from __future__ import annotations

import json

from vat_audit_pipeline.utils.monitoring import ResourceMonitor, write_resource_report


def test_write_resource_report(tmp_path):
    monitor = ResourceMonitor()
    report = monitor.generate_report()
    out = tmp_path / "r.json"
    p = write_resource_report(report, out)

    assert p.endswith("r.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "memory" in data
    assert "cpu" in data
