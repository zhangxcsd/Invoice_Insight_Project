"""
配置系统测试脚本
验证config.yaml和config_manager的正确性
"""
import sys
from pathlib import Path

import pytest

def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("测试1: 配置文件加载")
    print("=" * 60)
    
    try:
        from config_manager import get_config

        config = get_config()
        print("✅ 配置管理器导入成功")
        print("✅ 配置文件加载成功")
        assert config is not None
    except FileNotFoundError as e:
        pytest.fail(f"配置文件不存在: {e}")
    except Exception as e:
        pytest.fail(f"配置加载失败: {e}")

def test_config_values(config):
    """测试配置值读取"""
    print("\n" + "=" * 60)
    print("测试2: 配置值读取")
    print("=" * 60)
    
    tests = [
        ("业务标识", config.business_tag, "VAT_INV"),
        ("工作进程数", config.worker_count, int),
        ("CSV块大小", config.csv_chunk_size, 10000),
        ("流式块大小", config.stream_chunk_size, 50000),
        ("日志级别", config.log_level, "INFO"),
        ("并行导入", config.parallel_enabled, True),
        ("免税映射为0", config.tax_text_to_zero, True),
    ]
    
    passed = 0
    failed = 0
    
    for name, value, expected in tests:
        if isinstance(expected, type):
            if isinstance(value, expected):
                print(f"✅ {name}: {value} ({type(value).__name__})")
                passed += 1
            else:
                print(f"❌ {name}: 类型错误，期望{expected.__name__}，实际{type(value).__name__}")
                failed += 1
        else:
            if value == expected:
                print(f"✅ {name}: {value}")
                passed += 1
            else:
                print(f"❌ {name}: 期望{expected}，实际{value}")
                failed += 1
    
    print(f"\n通过: {passed}/{len(tests)}, 失败: {failed}/{len(tests)}")
    assert failed == 0

def test_nested_config_access(config):
    """测试嵌套配置访问"""
    print("\n" + "=" * 60)
    print("测试3: 嵌套配置访问")
    print("=" * 60)
    
    tests = [
        ("business.tag", ['business', 'tag'], "VAT_INV"),
        ("paths.input_dir", ['paths', 'input_dir'], "Source_Data"),
        ("logging.log_level", ['logging', 'log_level'], "INFO"),
        ("parallel.worker_count", ['parallel', 'worker_count'], int),
    ]
    
    passed = 0
    for name, keys, expected in tests:
        value = config.get(*keys)
        if isinstance(expected, type):
            if isinstance(value, expected):
                print(f"✅ {name}: {value}")
                passed += 1
            else:
                print(f"❌ {name}: 类型不匹配")
        else:
            if value == expected:
                print(f"✅ {name}: {value}")
                passed += 1
            else:
                print(f"❌ {name}: {value} != {expected}")
    
    print(f"\n通过: {passed}/{len(tests)}")
    assert passed == len(tests)

def test_config_file_exists():
    """测试配置文件是否存在"""
    print("\n" + "=" * 60)
    print("测试4: 文件完整性检查")
    print("=" * 60)
    
    files = {
        'config.yaml': '配置文件',
        'config_manager.py': '配置管理器',
        'VAT_Invoice_Processor.py': '主程序',
    }
    
    all_exist = True
    for filename, desc in files.items():
        if Path(filename).exists():
            print(f"✅ {desc} ({filename}) 存在")
        else:
            print(f"❌ {desc} ({filename}) 不存在")
            all_exist = False

    assert all_exist

def test_sheet_classification(config):
    """测试sheet分类配置"""
    print("\n" + "=" * 60)
    print("测试5: Sheet分类规则")
    print("=" * 60)
    
    detail_patterns = config.detail_patterns
    header_patterns = config.header_patterns
    special_sheets = config.special_sheets
    
    print(f"✅ 明细表规则: {len(detail_patterns)} 条")
    print(f"   {', '.join(detail_patterns)}")
    print(f"✅ 汇总表规则: {len(header_patterns)} 条")
    print(f"   {', '.join(header_patterns)}")
    print(f"✅ 特殊表映射: {len(special_sheets)} 个")
    for sheet, suffix in list(special_sheets.items())[:3]:
        print(f"   {sheet} → {suffix}")
    if len(special_sheets) > 3:
        print(f"   ... 共{len(special_sheets)}个")
    
    assert len(detail_patterns) > 0 and len(header_patterns) > 0

def test_column_mapping(config):
    """测试列名映射配置"""
    print("\n" + "=" * 60)
    print("测试6: 列名映射配置")
    print("=" * 60)
    
    date_cols = config.date_columns
    numeric_cols = config.numeric_columns
    tax_cols = config.tax_rate_columns
    tax_tokens = config.tax_text_tokens
    
    print(f"✅ 日期列: {len(date_cols)} 个")
    print(f"   {', '.join(date_cols)}")
    print(f"✅ 数值列: {len(numeric_cols)} 个")
    print(f"   {', '.join(numeric_cols)}")
    print(f"✅ 税率列: {len(tax_cols)} 个")
    print(f"   {', '.join(tax_cols)}")
    print(f"✅ 税率文本标记: {len(tax_tokens)} 个")
    print(f"   {', '.join(tax_tokens)}")
    
    assert all([date_cols, numeric_cols, tax_cols, tax_tokens])

def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "配置系统完整性测试" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 测试1: 文件存在性
    file_test = test_config_file_exists()
    
    if not file_test:
        print("\n❌ 文件完整性检查失败，无法继续测试")
        return False
    
    # 测试2: 配置加载
    config = test_config_loading()
    
    if config is None:
        print("\n❌ 配置加载失败，测试终止")
        return False
    
    # 测试3-7: 各项配置测试
    test_results = [
        test_config_values(config),
        test_nested_config_access(config),
        test_sheet_classification(config),
        test_column_mapping(config),
    ]
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    total_tests = len(test_results) + 2  # +2 for file and loading tests
    passed_tests = sum([file_test, config is not None] + test_results)
    
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！配置系统工作正常。")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} 个测试失败，请检查配置。")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
