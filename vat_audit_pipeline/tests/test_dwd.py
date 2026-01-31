"""Smoke test for DWD module import surface."""

from vat_audit_pipeline.core.processors.dwd_processor import process_dwd


def test_dwd_import_surface():
    assert callable(process_dwd)