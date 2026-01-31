from __future__ import annotations

import sqlite3

from vat_audit_pipeline.core.context import ProcessingContext


def test_processing_context_opens_and_closes(tmp_path):
    db_path = tmp_path / "test.db"

    ctx = ProcessingContext(str(db_path), config=None)
    with ctx as opened:
        assert opened.conn is not None
        opened.conn.execute("CREATE TABLE IF NOT EXISTS t(x INTEGER)")
        opened.conn.execute("INSERT INTO t(x) VALUES (1)")
        opened.conn.commit()

    assert ctx.conn is None

    # DB should be readable after context exit
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(1) FROM t").fetchone()[0]
        assert row == 1
