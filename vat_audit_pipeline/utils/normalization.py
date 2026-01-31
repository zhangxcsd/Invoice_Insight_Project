"""Data normalization helpers for the package.

This module is the canonical implementation. The legacy module
`utils.data_normalization` re-exports symbols from here for compatibility.
"""

from __future__ import annotations

import pandas as pd


def normalize_excel_date_col(ser):
	"""Parse Excel-like date columns and return (parsed, method, converted, failed)."""

	try:
		dt = pd.to_datetime(ser, errors="coerce")
		converted = dt.notna().sum()
		if converted >= 0.7 * len(ser):
			return dt.dt.strftime("%Y-%m-%d"), "pd.to_datetime", int(converted), int(len(ser) - converted)
	except Exception:
		pass
	if pd.api.types.is_numeric_dtype(ser):
		try:
			dt1 = pd.to_datetime(ser, unit="d", origin="1899-12-30", errors="coerce")
			if dt1.notna().sum() >= 0.5 * len(ser):
				converted = int(dt1.notna().sum())
				return dt1.dt.strftime("%Y-%m-%d"), "excel_1899-12-30", converted, int(len(ser) - converted)
		except Exception:
			pass
		try:
			dt2 = pd.to_datetime(ser, unit="d", origin="1904-01-01", errors="coerce")
			converted = int(dt2.notna().sum())
			return dt2.dt.strftime("%Y-%m-%d"), "excel_1904-01-01", converted, int(len(ser) - converted)
		except Exception:
			pass
	try:
		dtf = pd.to_datetime(ser.astype(str).str.strip(), errors="coerce")
		converted = int(dtf.notna().sum())
		return dtf.dt.strftime("%Y-%m-%d"), "final_str_parse", converted, int(len(ser) - converted)
	except Exception:
		return ser, "none", 0, int(len(ser))


def normalize_numeric_col(ser):
	"""Clean numeric strings (commas, percent sign) then parse to numeric."""

	s = ser.astype(str).str.replace(",", "").str.replace("，", "")
	s = s.str.replace("%", "")
	num = pd.to_numeric(s, errors="coerce")
	converted = int(num.notna().sum())
	return num, converted, int(len(ser) - converted)


def normalize_tax_rate_col(ser):
	"""Parse tax rate values including text tokens like 免税/不征税."""

	s = ser.fillna("").astype(str).str.strip()
	text_tokens = ["免税", "不征税", "免征"]
	mask_text = s.isin(text_tokens)
	s_clean = s.str.rstrip("%").str.replace(",", "").str.replace("％", "").str.strip()
	num = pd.to_numeric(s_clean, errors="coerce")
	converted = int(num.notna().sum())
	text_count = int(mask_text.sum())
	failed = int(((~num.notna()) & (~mask_text) & s.ne("") & ~s.isna()).sum())
	return num, "tax_parse", converted, failed, text_count, mask_text


def cast_and_record(df, fname, sheet, cast_stats, cast_failures, tax_text_to_zero: bool = True):
	"""Normalize common columns and log stats/failures."""

	date_cols = ["开票日期"]
	num_cols = ["金额", "税额", "单价", "数量", "价税合计", "税率"]

	for c in date_cols:
		if c in df.columns:
			parsed, method, converted, failed = normalize_excel_date_col(df[c])
			mask_failed = pd.isna(parsed) & df[c].notna() & df[c].astype(str).str.strip().ne("")
			if mask_failed.any():
				for idx, val in df.loc[mask_failed, c].items():
					row = {"file": fname, "sheet": sheet, "column": c, "row_index": int(idx), "orig_value": str(val)}
					if "发票代码" in df.columns:
						row["发票代码"] = str(df.at[idx, "发票代码"])
					if "发票号码" in df.columns:
						row["发票号码"] = str(df.at[idx, "发票号码"])
					cast_failures.append(pd.DataFrame([row]))
			df[c] = parsed
			cast_stats.append(
				{
					"file": fname,
					"sheet": sheet,
					"column": c,
					"method": method,
					"total": len(df),
					"converted": converted,
					"failed": failed,
				}
			)

	for c in num_cols:
		if c in df.columns:
			if c == "税率":
				parsed_num, method, converted, failed, text_count, mask_text = normalize_tax_rate_col(df[c])
				if tax_text_to_zero and mask_text.any():
					parsed_num = parsed_num.copy()
					parsed_num[mask_text] = 0
					cast_stats.append(
						{
							"file": fname,
							"sheet": sheet,
							"column": "税率_数值",
							"method": "map_tax_text_to_zero",
							"total": len(df),
							"converted": int(mask_text.sum()),
							"failed": 0,
						}
					)
				df["税率_数值"] = parsed_num
				cast_stats.append(
					{
						"file": fname,
						"sheet": sheet,
						"column": "税率_数值",
						"method": method,
						"total": len(df),
						"converted": int(converted),
						"failed": int(failed),
					}
				)
				if text_count > 0:
					cast_stats.append(
						{
							"file": fname,
							"sheet": sheet,
							"column": "税率",
							"method": "tax_text_tokens",
							"total": len(df),
							"converted": int(text_count),
							"failed": int(len(df) - text_count - converted),
						}
					)
			else:
				parsed_num, converted, failed = normalize_numeric_col(df[c])
				df[c] = parsed_num
				cast_stats.append(
					{
						"file": fname,
						"sheet": sheet,
						"column": c,
						"method": "numeric_parse",
						"total": len(df),
						"converted": int(converted),
						"failed": int(failed),
					}
				)

	return df


__all__ = [
	"normalize_excel_date_col",
	"normalize_numeric_col",
	"normalize_tax_rate_col",
	"cast_and_record",
]
