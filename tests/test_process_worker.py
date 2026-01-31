import os
import pandas as pd
import tempfile
from VAT_Invoice_Processor import process_file_worker


def create_sample_excel(path):
    df_summary = pd.DataFrame({
        '发票代码':['C1','C2'],'发票号码':['001','002'],'开票日期':['2021-01-01','2021-01-02'],'税率':['13%','0']
    })
    df_header = pd.DataFrame({
        '发票代码':['H1'],'发票号码':['010'],'开票日期':['2021-01-01'],'金额':['100.0'],'税率':['免税']
    })
    with pd.ExcelWriter(path) as w:
        df_summary.to_excel(w, sheet_name='信息汇总表', index=False)
        df_header.to_excel(w, sheet_name='发票基础信息', index=False)


def test_process_file_worker(tmp_path):
    tmp = tmp_path
    sample = tmp / 'sample.xlsx'
    create_sample_excel(str(sample))
    meta = {'sheet_info': {'信息汇总表':['发票代码','发票号码','开票日期','税率'], '发票基础信息':['发票代码','发票号码','开票日期','金额','税率']}, 'detail_sheets':[], 'header_sheets':['发票基础信息'], 'summary_sheets':['信息汇总表'], 'special_sheets':{}}
    temp_dir = str(tmp / 'out')
    os.makedirs(temp_dir, exist_ok=True)
    res = process_file_worker((str(sample), meta, temp_dir, '2026-01-01 00:00:00', set(['发票代码','发票号码','开票日期','税率']), set(['发票代码','发票号码','开票日期','金额','税率']), set(['发票代码','发票号码','开票日期','税率']), {}))
    assert 'sheet_manifest' in res
    assert any(e['classification']=='summary' for e in res['sheet_manifest'])
    # temp csvs should be generated
    assert any(os.path.exists(t['path']) for t in res.get('temp_csvs',[]))

if __name__ == '__main__':
    import pytest
    pytest.main([str(__file__)])
