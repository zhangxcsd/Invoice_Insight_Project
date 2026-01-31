PR Title: Improve import robustness and sheet classification; add docs

Summary:
- Implement full-rebuild ODS import: delete ODS table on each run and rebuild from current `Source_Data/` (ensures deletions/changes in source are reflected).
- Add sheet-name-first classification (DETAIL_RE / HEADER_RE) to identify detail sheets and header sheets; fallback to header-key detection if no name match.
- Separate header data into `ODS_<BUSINESS>_HEADER` (invoice-level records) to avoid mixing with detail lines.
- Add manifest outputs: `ods_sheet_manifest_<ts>.csv` and `ods_import_summary_<ts>.csv` for verification and auditing.
- Skip temporary/lock Excel files (starting with `~$`) to avoid permission errors.
- Improve code comments and module-level README outlining usage and behavior.

Testing / How to Validate:
1. Place sample Excel exports into `Source_Data/` and run `python VAT_Invoice_Processor.py`.
2. Verify `Outputs/ods_sheet_manifest_*` lists sheet classifications and `Outputs/ods_import_summary_*` shows totals.
3. Inspect database tables in `Database/` to confirm `ODS_*`, `DWD_*`, `LOG_*`, and `ADS_*` are created.
4. Modify a sample file (delete a sheet or change column names) and re-run to ensure full-rebuild reflects changes.

Impact:
- Backwards compatible for typical usage, but note that ODS temporary table is rebuilt each run (intended behavior).

Notes:
- Regex patterns for sheet names are in code (`DETAIL_RE`, `HEADER_RE`); adjust as needed for different export conventions.
- Consider adding unit tests and a file manifest table for more robust incremental updates in future PRs.
