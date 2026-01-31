from __future__ import annotations

import pytest

from vat_audit_pipeline.config.settings import PipelineSettings
from vat_audit_pipeline.config.validators import validate_pipeline_config


def test_invalid_stream_chunk_memory_percent():
    s = PipelineSettings()
    s.stream_chunk_memory_percent = 2
    with pytest.raises(ValueError):
        validate_pipeline_config(s)


def test_invalid_threshold_percent():
    s = PipelineSettings()
    s.memory_threshold_percent = 200
    with pytest.raises(ValueError):
        validate_pipeline_config(s)
