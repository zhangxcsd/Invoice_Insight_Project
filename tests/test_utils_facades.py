from __future__ import annotations


def test_utils_facades_importable():
    from vat_audit_pipeline.utils import encoding, logging, normalization, sheet_processing  # noqa: F401

    assert hasattr(logging, "PerformanceTimer")
    assert hasattr(encoding, "read_csv_with_encoding_detection")
    assert hasattr(normalization, "cast_and_record")
    assert hasattr(sheet_processing, "get_sheet_handler")


def test_legacy_utils_shims_importable():
    from utils import encoding_utils, logging_utils, data_normalization, sheet_processing  # noqa: F401

    assert hasattr(logging_utils, "PerformanceTimer")
    assert hasattr(encoding_utils, "read_csv_with_encoding_detection")
    assert hasattr(data_normalization, "cast_and_record")
    assert hasattr(sheet_processing, "get_sheet_handler")
