import pandas as pd
import os
import sqlite3
from VAT_Invoice_Processor import normalize_excel_date_col, normalize_numeric_col, normalize_tax_rate_col, cast_and_record


def test_normalize_excel_date_col():
    s = pd.Series(['2021-01-01', '2021/02/02', '01-03-2021', ''])
    parsed, method, converted, failed = normalize_excel_date_col(s)
    # At least one known date should be parsed and returned in yyyy-mm-dd format
    assert any(v in parsed.values for v in ['2021-01-01', '2021-02-02'])
    assert converted >= 1


def test_normalize_numeric_col():
    s = pd.Series(['1,234.56', '  1000 ', 'n/a', ''])
    parsed, converted, failed = normalize_numeric_col(s)
    assert parsed.iloc[0] == 1234.56
    assert converted >= 2


def test_normalize_tax_rate_col():
    s = pd.Series(['13%', '免税', '0', '3%','abc'])
    num, method, converted, failed, text_count, mask_text = normalize_tax_rate_col(s)
    assert converted >= 3  # '13%' '0' '3%'
    assert text_count == 1
    assert failed >= 1


def test_cast_and_record_creates_tax_numeric(tmp_path):
    df = pd.DataFrame({
        '发票代码': ['A1','A2'],
        '发票号码': ['001','002'],
        '开票日期': ['2021-01-01','2021-02-02'],
        '税率': ['免税','13%'],
        '金额': ['1000','2000']
    })
    cast_stats = []
    cast_failures = []
    df2 = cast_and_record(df.copy(), 'test.xlsx', '信息汇总表', cast_stats, cast_failures)
    assert '税率_数值' in df2.columns
    # 免税 -> NaN or 0 depending on TAX_TEXT_TO_ZERO; numeric should be parseable
    assert df2['税率_数值'].iloc[1] == 13.0


if __name__ == '__main__':
    import pytest
    pytest.main([os.path.abspath(__file__)])
