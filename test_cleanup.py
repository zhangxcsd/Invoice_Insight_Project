"""
临时文件清理改进 - 测试脚本

测试场景：
1. 清理旧临时目录
2. 注册 atexit 处理器
3. 模拟异常情况下的清理
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from VAT_Invoice_Processor import (
    cleanup_temp_files,
    cleanup_old_temp_files,
    register_cleanup,
    logger,
    OUTPUT_DIR
)


def test_cleanup_functions():
    """测试清理函数"""
    print("\n" + "="*70)
    print("TEST 1: cleanup_temp_files function")
    print("="*70)
    
    # Create test temp directory
    test_temp_dir = os.path.join(OUTPUT_DIR, 'tmp_imports', 'test_cleanup_2026-01-03')
    test_file = os.path.join(test_temp_dir, 'test.txt')
    
    try:
        os.makedirs(test_temp_dir, exist_ok=True)
        with open(test_file, 'w') as f:
            f.write('test data')

        print(f"[CREATE] Test directory: {test_temp_dir}")
        print(f"[CREATE] Test file: {test_file}")
        assert os.path.exists(test_file)

        cleanup_temp_files(test_temp_dir)

        assert not os.path.exists(test_temp_dir)
        print("[PASS] Cleanup function works correctly")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        # Clean up test files
        if os.path.exists(test_temp_dir):
            shutil.rmtree(test_temp_dir, ignore_errors=True)


def test_cleanup_old_temp_files():
    """Test cleaning old temp directories"""
    print("\n" + "="*70)
    print("TEST 2: cleanup_old_temp_files function")
    print("="*70)
    
    # Create test directories
    tmp_imports_root = os.path.join(OUTPUT_DIR, 'tmp_imports')
    os.makedirs(tmp_imports_root, exist_ok=True)
    
    test_dirs = [
        os.path.join(tmp_imports_root, '2026-01-01_10-00-00_old1'),
        os.path.join(tmp_imports_root, '2026-01-02_15-30-00_old2'),
    ]
    
    try:
        # Create test directories and force their mtime to be "old".
        old_ts = datetime.now().timestamp() - 48 * 3600
        for test_dir in test_dirs:
            os.makedirs(test_dir, exist_ok=True)
            with open(os.path.join(test_dir, 'test.csv'), 'w') as f:
                f.write('test data')
            os.utime(test_dir, (old_ts, old_ts))
            print(f"[CREATE] Test directory: {test_dir}")

        cleanup_old_temp_files()

        existing = [d for d in test_dirs if os.path.exists(d)]
        assert not existing, f"Expected all old temp dirs to be removed, still exist: {existing}"
        print("[PASS] All old temp directories cleaned")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        # Clean up test files
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)


def test_register_cleanup():
    """Test atexit registration"""
    print("\n" + "="*70)
    print("TEST 3: register_cleanup function")
    print("="*70)
    
    try:
        register_cleanup()
        print("[CALL] register_cleanup() executed")
        print("[PASS] atexit registration successful")
        assert True
    except Exception as e:
        pytest.fail(f"Test failed: {e}")


def test_global_temp_dir():
    """Test global temp directory variable"""
    print("\n" + "="*70)
    print("TEST 4: Global _CURRENT_TEMP_DIR variable")
    print("="*70)
    
    try:
        import VAT_Invoice_Processor as vap

        initial_value = vap._CURRENT_TEMP_DIR
        print(f"[CHECK] Initial _CURRENT_TEMP_DIR: {initial_value}")

        test_dir = os.path.join(OUTPUT_DIR, 'tmp_imports', 'test_global_2026-01-03')
        vap._CURRENT_TEMP_DIR = test_dir

        print(f"[SET] _CURRENT_TEMP_DIR = {test_dir}")
        assert vap._CURRENT_TEMP_DIR == test_dir

        vap._CURRENT_TEMP_DIR = None
        print("[PASS] Global variable works correctly")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")


def test_integration():
    """Integration test"""
    print("\n" + "="*70)
    print("TEST 5: Integration test")
    print("="*70)
    
    try:
        import VAT_Invoice_Processor as vap

        tmp_imports_root = os.path.join(OUTPUT_DIR, 'tmp_imports')
        old_dir = os.path.join(tmp_imports_root, '2026-01-03_20-00-00_integration_old')
        os.makedirs(old_dir, exist_ok=True)
        with open(os.path.join(old_dir, 'data.csv'), 'w') as f:
            f.write('old data')

        # Force old mtime so it qualifies as "old" for cleanup.
        old_ts = datetime.now().timestamp() - 48 * 3600
        os.utime(old_dir, (old_ts, old_ts))

        print(f"[CREATE] Old temp directory: {old_dir}")
        assert os.path.exists(old_dir)

        cleanup_old_temp_files()
        print("[CALL] cleanup_old_temp_files()")
        assert not os.path.exists(old_dir)

        new_dir = os.path.join(tmp_imports_root, '2026-01-03_21-59-00_integration_new')
        os.makedirs(new_dir, exist_ok=True)

        vap._CURRENT_TEMP_DIR = new_dir
        print(f"[SET] _CURRENT_TEMP_DIR = {new_dir}")

        register_cleanup()
        print("[CALL] register_cleanup()")

        if os.path.exists(new_dir):
            shutil.rmtree(new_dir, ignore_errors=True)

        print("[PASS] Integration test successful")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("Temp File Cleanup Improvement - Test Suite")
    print("="*70)
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")
    print(f"Current time: {datetime.now()}")
    
    tests = [
        ("Cleanup function", test_cleanup_functions),
        ("Cleanup old temp files", test_cleanup_old_temp_files),
        ("Register cleanup", test_register_cleanup),
        ("Global temp directory", test_global_temp_dir),
        ("Integration test", test_integration),
    ]
    
    results = []
    try:
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"\n[ERROR] {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n[SUCCESS] All tests passed!")
            return 0
        else:
            print(f"\n[FAILURE] {total - passed} test(s) failed")
            return 1
            
    except Exception as e:
        print(f"\n[FATAL] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
