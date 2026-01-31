import os
import shutil
import time
import pandas as pd
from VAT_Invoice_Processor import run_vat_audit_pipeline

# 轻量基准：复制现有 sample.xlsx 多份到 Source_Data/tmp_n 并运行流水线计时

def create_copies(src, dst_dir, n):
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(dst_dir, exist_ok=True)
    for i in range(n):
        shutil.copy(src, os.path.join(dst_dir, f'sample_{i}.xlsx'))

if __name__ == '__main__':
    src_sample = os.path.join('Source_Data','sample_template.xlsx')
    if not os.path.exists(src_sample):
        # create a small template
        df = pd.DataFrame({'发票代码':['T1','T2'],'发票号码':['001','002'],'开票日期':['2021-01-01','2021-01-02'],'税率':['13%','免税'],'金额':['100','200']})
        os.makedirs('Source_Data', exist_ok=True)
        df.to_excel(src_sample, index=False)
    for n in [1, 5, 10]:
        tmp_dir = os.path.join('Source_Data', f'tmp_bench_{n}')
        create_copies(src_sample, tmp_dir, n)
        print(f"Running benchmark with {n} files...")
        t0 = time.perf_counter()
        run_vat_audit_pipeline()
        t1 = time.perf_counter()
        print(f"Elapsed: {t1-t0:.2f}s")
        # cleanup
        shutil.rmtree(tmp_dir)
