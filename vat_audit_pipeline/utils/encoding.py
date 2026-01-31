"""Encoding utilities for the package.

This module is the canonical implementation. The legacy module
`utils.encoding_utils` re-exports symbols from here for compatibility.

Important: to keep backward compatibility with existing code/tests,
`detect_encoding()` returns a string encoding name.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd

logger = logging.getLogger("vat_audit")


def detect_encoding(file_path: str, sample_size: int = 10000) -> str:
	"""Detect file encoding using chardet with simple alias normalization."""

	try:
		import chardet

		with open(file_path, "rb") as f:
			raw_data = f.read(sample_size)
		result = chardet.detect(raw_data) or {}
		detected_encoding = result.get("encoding")
		confidence = result.get("confidence", 0)
		if detected_encoding:
			detected_encoding = str(detected_encoding).lower()
			encoding_aliases = {
				"ascii": "utf-8",
				"utf-8-sig": "utf-8-sig",
				"utf8": "utf-8",
				"utf_8": "utf-8",
				"gbk": "gbk",
				"gb2312": "gbk",
				"gb18030": "gbk",
				"cp936": "gbk",
				"cjk": "gbk",
			}
			for alias, standard in encoding_aliases.items():
				if alias in detected_encoding:
					detected_encoding = standard
					break
			logger.debug(
				f"编码检测: {os.path.basename(file_path)} → {detected_encoding} (置信度 {confidence*100:.1f}%)"
			)
			return detected_encoding
		logger.warning(f"无法检测编码 {file_path}，使用默认 utf-8-sig")
		return "utf-8-sig"
	except Exception as e:
		logger.warning(f"编码检测异常 {file_path}: {e}，使用默认 utf-8-sig")
		return "utf-8-sig"


def read_csv_with_encoding_detection(
	file_path: str,
	encoding: Optional[str] = None,
	**kwargs,
) -> pd.DataFrame:
	"""Read CSV with auto encoding detection and fallbacks."""

	if encoding is None:
		encoding = detect_encoding(file_path)
	try:
		return pd.read_csv(file_path, encoding=encoding, **kwargs)
	except UnicodeDecodeError as e:
		logger.warning(f"使用 {encoding} 读取失败: {e}，尝试备选编码...")
		alternative_encodings = ["gbk", "utf-8", "utf-8-sig", "gb2312", "cp936"]
		for alt_enc in alternative_encodings:
			if alt_enc == encoding:
				continue
			try:
				logger.debug(f"尝试备选编码: {alt_enc}")
				df = pd.read_csv(file_path, encoding=alt_enc, **kwargs)
				logger.info(f"使用备选编码 {alt_enc} 成功读取: {os.path.basename(file_path)}")
				return df
			except UnicodeDecodeError:
				continue
			except Exception:
				continue
		logger.error(f"所有编码都失败，使用 errors='replace' 跳过无法解码的字符: {file_path}")
		return pd.read_csv(file_path, encoding=encoding, errors="replace", **kwargs)
	except Exception as e:
		logger.error(f"读取 CSV 失败 {file_path}: {e}")
		raise


__all__ = [
	"detect_encoding",
	"read_csv_with_encoding_detection",
]
