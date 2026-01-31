from __future__ import annotations

from click.testing import CliRunner

import vat_audit_pipeline.main as vat_main


def test_cli_no_args_runs_legacy_main(monkeypatch):
    called = {"ok": False}

    def fake_main() -> None:
        called["ok"] = True

    monkeypatch.setattr(vat_main, "main", fake_main)

    runner = CliRunner()
    result = runner.invoke(vat_main.cli, [])

    assert result.exit_code == 0
    assert called["ok"] is True
