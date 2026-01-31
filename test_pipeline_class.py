"""
VATAuditPipeline 类使用示例和测试脚本
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import pytest

from VAT_Invoice_Processor import VATAuditPipeline
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_class_initialization():
    """测试类初始化"""
    print("\n" + "="*60)
    print("测试1：类初始化")
    print("="*60)
    
    try:
        pipeline = VATAuditPipeline()
        logger.info("✅ 类初始化成功")
        assert pipeline is not None
        assert hasattr(pipeline, "process_time")
    except Exception as e:
        pytest.fail(f"类初始化失败: {e}")


def test_file_scanning():
    """测试文件扫描"""
    print("\n" + "="*60)
    print("测试2：文件扫描")
    print("="*60)
    
    try:
        pipeline = VATAuditPipeline()
        excel_files = pipeline.scan_excel_files()
        assert isinstance(excel_files, list)
    except Exception as e:
        pytest.fail(f"文件扫描失败: {e}")


def test_metadata_scanning():
    """测试元数据扫描"""
    print("\n" + "="*60)
    print("测试3：元数据扫描")
    print("="*60)
    
    try:
        pipeline = VATAuditPipeline()
        excel_files = pipeline.scan_excel_files()

        if not excel_files:
            pytest.skip("没有 Excel 文件，跳过元数据扫描")

        files_meta = pipeline.scan_excel_metadata()
        assert isinstance(files_meta, dict)
    except Exception as e:
        pytest.fail(f"元数据扫描失败: {e}")


def test_database_initialization():
    """测试数据库初始化"""
    print("\n" + "="*60)
    print("测试4：数据库初始化")
    print("="*60)
    
    try:
        pipeline = VATAuditPipeline()
        conn = pipeline.init_database()
        assert conn is not None

        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        assert version
        conn.close()
    except Exception as e:
        pytest.fail(f"数据库初始化失败: {e}")


def test_config_loading():
    """测试配置加载"""
    print("\n" + "="*60)
    print("测试5：配置加载验证")
    print("="*60)
    
    try:
        from config_manager import get_config

        cfg = get_config()
        assert cfg is not None
        assert hasattr(cfg, "business_tag")
    except Exception as e:
        # Keep test non-fatal, but ensure the exception is visible.
        pytest.fail(f"配置加载失败: {e}")


def test_directory_structure():
    """测试目录结构"""
    print("\n" + "="*60)
    print("测试6：目录结构检查")
    print("="*60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dirs_to_check = {
        'Source_Data': os.path.join(base_dir, 'Source_Data'),
        'Database': os.path.join(base_dir, 'Database'),
        'Outputs': os.path.join(base_dir, 'Outputs'),
    }

    for _, dir_path in dirs_to_check.items():
        assert os.path.exists(dir_path)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print(" " * 20 + "VATAuditPipeline 类测试套件")
    print("="*80)
    
    tests = [
        ("类初始化", test_class_initialization),
        ("配置加载", test_config_loading),
        ("目录结构", test_directory_structure),
        ("文件扫描", test_file_scanning),
        ("元数据扫描", test_metadata_scanning),
        ("数据库初始化", test_database_initialization),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 汇总
    print("\n" + "="*80)
    print("测试汇总".center(80))
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:.<30} {status}")
    
    print("="*80)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！类结构正常")
    else:
        print(f"⚠️  有 {total - passed} 项测试失败，请检查错误信息")
    
    print("="*80)
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
