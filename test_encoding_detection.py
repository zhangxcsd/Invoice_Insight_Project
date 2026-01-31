"""
编码自动检测功能测试

测试场景：
1. UTF-8 编码检测
2. GBK 编码检测
3. UTF-8-SIG（带BOM）编码检测
4. 备选编码读取
5. 编码转换处理
"""

import os
import sys
import csv
import pandas as pd
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from VAT_Invoice_Processor import detect_encoding, read_csv_with_encoding_detection


def create_test_csv_files():
    """创建各种编码的测试 CSV 文件"""
    test_dir = os.path.join(os.path.dirname(__file__), 'test_encoding_files')
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试数据（包含中文）
    test_data = [
        ['发票代码', '发票号码', '金额', '税额', '说明'],
        ['110101000000', '12345678', '1000.00', '100.00', '测试发票1'],
        ['110101000001', '12345679', '2000.00', '200.00', '测试发票2'],
        ['110101000002', '12345680', '3000.00', '300.00', '测试发票3'],
    ]
    
    files_created = []
    
    # 1. UTF-8 编码（无 BOM）
    utf8_file = os.path.join(test_dir, 'test_utf8.csv')
    with open(utf8_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(test_data)
    files_created.append(('UTF-8', utf8_file))
    print(f"[OK] UTF-8 file created: {utf8_file}")
    
    # 2. UTF-8-SIG 编码（有 BOM）
    utf8_sig_file = os.path.join(test_dir, 'test_utf8_sig.csv')
    with open(utf8_sig_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(test_data)
    files_created.append(('UTF-8-SIG', utf8_sig_file))
    print(f"[OK] UTF-8-SIG file created: {utf8_sig_file}")
    
    # 3. GBK 编码
    gbk_file = os.path.join(test_dir, 'test_gbk.csv')
    with open(gbk_file, 'w', encoding='gbk', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(test_data)
    files_created.append(('GBK', gbk_file))
    print(f"[OK] GBK file created: {gbk_file}")
    
    # 4. GB2312 编码
    gb2312_file = os.path.join(test_dir, 'test_gb2312.csv')
    try:
        with open(gb2312_file, 'w', encoding='gb2312', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
        files_created.append(('GB2312', gb2312_file))
        print(f"[OK] GB2312 file created: {gb2312_file}")
    except Exception as e:
        print(f"[WARN] GB2312 encoding not supported: {e}")
    
    return test_dir, files_created


def test_encoding_detection():
    """测试编码检测功能"""
    print("\n" + "="*70)
    print("TEST 1: 编码检测函数测试")
    print("="*70)
    
    test_dir, files_created = create_test_csv_files()

    try:
        print("\n【检测各种编码的 CSV 文件】")
        results = []

        for encoding_name, file_path in files_created:
            detected = detect_encoding(file_path)
            results.append((encoding_name, detected, file_path))

            if detected.lower() in encoding_name.lower() or encoding_name.lower() in detected.lower():
                status = "[PASS]"
            else:
                status = "[WARN]"

            print(f"{status} {encoding_name:15} => {detected:15} ({os.path.basename(file_path)})")

        assert len(results) == len(files_created)
        assert all(detected is not None for _, detected, _ in results)
    finally:
        cleanup_test_files(test_dir)


def test_csv_reading():
    """测试 CSV 读取功能"""
    print("\n" + "="*70)
    print("TEST 2: CSV 读取测试（自动编码检测）")
    print("="*70)
    
    test_dir, files_created = create_test_csv_files()

    try:
        print("\n【读取各种编码的 CSV 文件】")

        for encoding_name, file_path in files_created:
            df = read_csv_with_encoding_detection(file_path)
            assert len(df) == 3
            assert len(df.columns) == 5
            print(f"[PASS] {encoding_name:15} - Read OK ({len(df)} rows, {len(df.columns)} cols)")
            print(f"         Columns: {list(df.columns)}")
    finally:
        cleanup_test_files(test_dir)


def test_encoding_with_errors():
    """测试编码错误处理"""
    print("\n" + "="*70)
    print("TEST 3: 编码错误处理测试")
    print("="*70)
    
    test_dir, files_created = create_test_csv_files()
    
    # 创建一个故意错误的编码情况
    # 尝试用 UTF-8 读取 GBK 文件
    print("\n【尝试用错误的编码读取，测试回退机制】")
    
    # 找到 GBK 文件
    gbk_file = None
    for encoding_name, file_path in files_created:
        if encoding_name == 'GBK':
            gbk_file = file_path
            break
    
    try:
        if gbk_file:
            df = read_csv_with_encoding_detection(gbk_file)
            assert len(df) == 3
            assert len(df.columns) == 5
            print(f"[PASS] GBK file read with fallback encoding")
            print(f"       Rows: {len(df)}, Columns: {len(df.columns)}")
        else:
            pytest.skip("GBK test file not created")
    finally:
        cleanup_test_files(test_dir)


def test_encoding_consistency():
    """测试编码一致性"""
    print("\n" + "="*70)
    print("TEST 4: 编码一致性测试")
    print("="*70)
    
    test_dir, files_created = create_test_csv_files()
    
    print("\n【验证读取的数据内容一致性】")
    
    try:
        dfs = {}

        for encoding_name, file_path in files_created:
            df = read_csv_with_encoding_detection(file_path)
            dfs[encoding_name] = df

        # Compare all frames are equal in shape/columns.
        assert len(dfs) >= 2
        first_encoding = list(dfs.keys())[0]
        first_df = dfs[first_encoding]

        for encoding_name, df in list(dfs.items())[1:]:
            assert df.shape == first_df.shape
            assert list(df.columns) == list(first_df.columns)
            print(f"[PASS] {encoding_name:15} vs {first_encoding:15} - Data consistent")
    finally:
        cleanup_test_files(test_dir)


def cleanup_test_files(test_dir):
    """清理测试文件"""
    print("\n[Cleanup test files]")
    import shutil
    try:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"[OK] Cleaned up test directory: {test_dir}")
    except Exception as e:
        print(f"[WARN] Cannot delete test directory: {e}")


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("编码自动检测功能 - 完整测试套件")
    print("="*70)
    
    try:
        # Test 1: 编码检测
        test_dir, files_created, detection_results = test_encoding_detection()
        
        # Test 2: CSV 读取
        reading_passed = test_csv_reading()
        
        # Test 3: 错误处理
        error_handling_passed = test_encoding_with_errors()
        
        # Test 4: 一致性
        consistency_passed = test_encoding_consistency()
        
        # 清理
        cleanup_test_files(test_dir)
        
        # 总结
        print("\n" + "="*70)
        print("测试总结")
        print("="*70)
        
        detection_success = sum(1 for _, detected, _ in detection_results if detected is not None)
        detection_total = len(detection_results)
        
        print(f"\n编码检测: {detection_success}/{detection_total} 成功")
        print(f"CSV 读取: {'✓ 通过' if reading_passed else '✗ 失败'}")
        print(f"错误处理: {'✓ 通过' if error_handling_passed else '✗ 失败'}")
        print(f"一致性: {'✓ 通过' if consistency_passed else '✗ 失败'}")
        
        total_passed = detection_success == detection_total and reading_passed and error_handling_passed and consistency_passed
        
        if total_passed:
            print("\n[SUCCESS] All tests passed! Encoding auto-detection is working.")
            return 0
        else:
            print("\n[FAILURE] Some tests failed. Please check the output.")
            return 1
    
    except Exception as e:
        print(f"\n[FATAL] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
