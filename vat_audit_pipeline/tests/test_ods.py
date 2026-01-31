"""Smoke test for ODS module import surface."""

from vat_audit_pipeline.core.processors.ods_processor import process_ods


def test_ods_import_surface():
    assert callable(process_ods)