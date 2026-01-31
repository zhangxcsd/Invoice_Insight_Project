"""配置参数校验功能测试

测试 VAT_Invoice_Processor.py 中新增的配置校验逻辑，验证其能够正确检测和拒绝非法配置。
"""

import sys
import os

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_valid_app_settings():
    """测试合法的应用配置"""
    print("\n=== 测试 1: 合法的应用配置 ===")
    from VAT_Invoice_Processor import AppSettings, validate_app_settings

    settings = AppSettings()
    settings.default_max_file_mb = 500
    validate_app_settings(settings)
    print("✅ 通过：合法的应用配置验证成功")


def test_invalid_max_file_mb():
    """测试不合法的 max_file_mb 配置"""
    print("\n=== 测试 2: 不合法的 max_file_mb (小于 10) ===")
    from VAT_Invoice_Processor import AppSettings, validate_app_settings

    settings = AppSettings()
    settings.default_max_file_mb = 5  # 不合法：小于 10
    with pytest.raises(ValueError):
        validate_app_settings(settings)


def test_invalid_worker_count():
    """测试不合法的 worker_count 配置"""
    print("\n=== 测试 3: 不合法的 worker_count (小于 1) ===")
    from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config

    settings = PipelineSettings()
    settings.worker_count = -1  # 不合法：负数
    with pytest.raises(ValueError):
        validate_pipeline_config(settings)


def test_invalid_csv_chunk_size():
    """测试不合法的 csv_chunk_size 配置"""
    print("\n=== 测试 4: 不合法的 csv_chunk_size (小于 100) ===")
    from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config

    settings = PipelineSettings()
    settings.csv_chunk_size = 50  # 不合法：小于 100
    with pytest.raises(ValueError):
        validate_pipeline_config(settings)


def test_invalid_stream_chunk_size():
    """测试不合法的 stream_chunk_size 配置"""
    print("\n=== 测试 5: 不合法的 stream_chunk_size (小于 1000) ===")
    from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config

    settings = PipelineSettings()
    settings.stream_chunk_size = 500  # 不合法：小于 1000
    with pytest.raises(ValueError):
        validate_pipeline_config(settings)


def test_multiple_errors():
    """测试多个错误同时存在的情况"""
    print("\n=== 测试 6: 多个错误同时存在 ===")
    from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config

    settings = PipelineSettings()
    settings.worker_count = 0  # 错误 1
    settings.csv_chunk_size = 50  # 错误 2
    settings.stream_chunk_size = 500  # 错误 3
    with pytest.raises(ValueError) as exc:
        validate_pipeline_config(settings)
    error_msg = str(exc.value)
    assert "worker_count" in error_msg
    assert "csv_chunk_size" in error_msg
    assert "stream_chunk_size" in error_msg


def test_valid_pipeline_settings():
    """测试合法的管道配置"""
    print("\n=== 测试 7: 合法的管道配置 ===")
    from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config

    settings = PipelineSettings()
    validate_pipeline_config(settings)
    print("✅ 通过：合法的管道配置验证成功")


if __name__ == "__main__":
    print("="*70)
    print("配置参数校验功能测试")
    print("="*70)
    
    tests = [
        test_valid_app_settings,
        test_invalid_max_file_mb,
        test_invalid_worker_count,
        test_invalid_csv_chunk_size,
        test_invalid_stream_chunk_size,
        test_multiple_errors,
        test_valid_pipeline_settings,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n💥 测试执行异常：{e}")
            results.append(False)
    
    print("\n" + "="*70)
    print(f"测试结果：{sum(results)}/{len(results)} 通过")
    print("="*70)
    
    if all(results):
        print("\n🎉 所有测试通过！配置校验功能工作正常。")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败，请检查配置校验逻辑。")
        sys.exit(1)
