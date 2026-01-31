"""CLI entrypoint for VAT audit pipeline.

This module keeps a legacy-compatible `main()` function and also exposes
a click-based CLI (docx suggestion).
"""

from __future__ import annotations

import sqlite3

import click

from vat_audit_pipeline.core.pipeline import VATAuditPipeline


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """增值税发票审计流水线。"""

    if ctx.invoked_subcommand is None:
        main()


@cli.command()
@click.option("--input-dir", "-i", required=True, help="输入文件目录")
@click.option("--config", "-c", default="config.yaml", show_default=True, help="配置文件路径")
@click.option("--verbose", "-v", is_flag=True, help="详细输出模式")
def run(input_dir: str, config: str, verbose: bool) -> None:
    """运行审计流水线。"""

    pipeline = VATAuditPipeline(config_path=config, input_dir=input_dir, verbose=verbose)
    pipeline.run()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        return column in cols
    except Exception:
        return False


@cli.command()
@click.argument("year", type=int)
@click.option("--config", "-c", default="config.yaml", show_default=True, help="配置文件路径")
def analyze(year: int, config: str) -> None:
    """对指定年份做快速统计（基于已生成的台账表）。"""

    pipeline = VATAuditPipeline(config_path=config, input_dir=None, verbose=False)
    db_path = pipeline.runtime.db_path

    if not db_path.exists():
        raise click.ClickException(f"数据库文件不存在: {db_path}")

    detail_tbl = f"LEDGER_{pipeline.runtime.business_tag}_{year}_INVOICE_DETAIL"
    header_tbl = f"LEDGER_{pipeline.runtime.business_tag}_{year}_INVOICE_HEADER"

    with sqlite3.connect(db_path) as conn:
        click.echo(f"DB: {db_path}")

        for tbl in (detail_tbl, header_tbl):
            if not _table_exists(conn, tbl):
                click.echo(f"- {tbl}: (not found)")
                continue

            cnt = conn.execute(f"SELECT COUNT(1) FROM {tbl}").fetchone()[0]
            msg = f"- {tbl}: rows={cnt}"

            if _table_has_column(conn, tbl, "金额"):
                s = conn.execute(f"SELECT SUM(金额) FROM {tbl}").fetchone()[0]
                msg += f", SUM(金额)={s if s is not None else 0}"
            if _table_has_column(conn, tbl, "税额"):
                s = conn.execute(f"SELECT SUM(税额) FROM {tbl}").fetchone()[0]
                msg += f", SUM(税额)={s if s is not None else 0}"

            click.echo(msg)


def main() -> None:
    VATAuditPipeline().run()


if __name__ == "__main__":
    cli()