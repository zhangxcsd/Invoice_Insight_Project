import os
import time
from VAT_Invoice_Processor import logger, LOG_FILE


def test_log_file_created_and_contains_message(tmp_path):
    # Ensure log file does not exist initially
    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
    except Exception:
        pass
    # Emit a test log
    logger.info('pytest logging probe - logging up')
    # Flush
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    # Give filesystem a moment
    time.sleep(0.1)
    assert os.path.exists(LOG_FILE), f"Expected log file at {LOG_FILE}"
    # Check that the file contains our message
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'pytest logging probe - logging up' in content