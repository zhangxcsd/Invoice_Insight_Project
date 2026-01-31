import os
import json
from VAT_Invoice_Processor import write_error_logs


def test_write_error_logs_writes_csv_and_json(tmp_path):
    errors = [
        {'file': 'a.xlsx', 'sheet': 'S1', 'stage': 'read', 'error_type': 'FileNotFoundError', 'message': 'not found'},
        {'file': 'b.xlsx', 'sheet': 'S2', 'stage': 'cast', 'error_type': 'ValueError', 'message': 'bad value'}
    ]
    csv_p, json_p = write_error_logs(errors, '2026-01-02 03:00:00', output_dir=str(tmp_path))
    assert os.path.exists(csv_p)
    assert os.path.exists(json_p)
    with open(json_p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert data[0]['file'] == 'a.xlsx'
    # ensure suggestion field exists and for FileNotFoundError contains expected hint
    assert 'suggestion' in data[0]
    assert '检查文件路径' in data[0]['suggestion'] or '存在' in data[0]['suggestion']