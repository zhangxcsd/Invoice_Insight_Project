"""
测试DEBUG日志和进度条功能

用法：
    python test_debug_logging.py          # 测试所有功能
    python test_debug_logging.py --quick  # 快速测试
"""

import sys
import os
import time
import pandas as pd
import logging
from pathlib import Path

# 设置编码以支持中文输出
if sys.stdout.encoding != 'utf-8':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from VAT_Invoice_Processor import (
    logger, _debug_var, ProgressLogger, 
    create_progress_bar, ENABLE_DEBUG, config
)


def test_debug_var():
    """测试 _debug_var 函数"""
    print("\n" + "="*70)
    print("测试1：_debug_var 函数")
    print("="*70)
    
    # 标量值
    print("\n测试标量值：")
    _debug_var("count", 42)
    _debug_var("price", 99.99)
    _debug_var("enabled", True)
    
    # 列表
    print("\n测试列表：")
    files = ['file1.xlsx', 'file2.xlsx', 'file3.xlsx', 'file4.xlsx']
    _debug_var("excel_files", files)
    
    # 字典
    print("\n测试字典：")
    metadata = {
        'file1': {'sheets': 3, 'rows': 1000},
        'file2': {'sheets': 2, 'rows': 500}
    }
    _debug_var("metadata", metadata)
    
    # DataFrame
    print("\n测试 DataFrame：")
    df = pd.DataFrame({
        'invoice_id': [1, 2, 3, 4, 5],
        'amount': [100, 200, 300, 400, 500],
        'date': pd.date_range('2024-01-01', periods=5),
        'category': ['A', 'B', 'A', 'C', 'B']
    })
    _debug_var("invoice_data", df)
    
    print("\n✓ 测试1 完成")


def test_progress_bar():
    """测试进度条"""
    print("\n" + "="*70)
    print("测试2：进度条（ProgressLogger）")
    print("="*70)
    
    # 测试1：简单计数
    print("\n简单进度条（计数）：")
    with ProgressLogger(total=50, desc="处理数据") as pbar:
        for i in range(50):
            time.sleep(0.01)
            if i % 10 == 0 and i > 0:
                pbar.update(10, msg=f"已处理 {i} 条记录")
    
    # 测试2：处理列表
    print("\nFile 处理进度条：")
    items = [f"item_{i}" for i in range(20)]
    with ProgressLogger(total=len(items), desc="导入项目") as pbar:
        for item in items:
            time.sleep(0.02)
            if items.index(item) % 5 == 0:
                pbar.update(5, msg=f"✅ 成功导入 {item}")
    
    print("\n✅ 测试2 完成")


def test_logging_levels():
    """测试不同的日志级别"""
    print("\n" + "="*70)
    print("测试3：日志级别")
    print("="*70)
    
    print("\n当前 DEBUG 启用状态:", "✅ 启用" if ENABLE_DEBUG else "❌ 禁用")
    print("当前日志级别:", logging.getLevelName(logger.level))
    
    # 各种级别的日志
    logger.debug("这是一条 DEBUG 日志 - 仅在启用DEBUG时显示")
    logger.info("这是一条 INFO 日志 - 总是显示")
    logger.warning("这是一条 WARNING 日志 - 总是显示")
    logger.error("这是一条 ERROR 日志 - 总是显示")
    
    print("\n✅ 测试3 完成")


def test_configuration():
    """测试配置读取"""
    print("\n" + "="*70)
    print("测试4：配置管理")
    print("="*70)
    
    print("\n配置信息：")
    print(f"  debug_enabled: {config.debug_enabled}")
    print(f"  log_to_file: {config.get('logging', 'log_to_file', default=False)}")
    print(f"  log_file: {config.get('logging', 'log_file', default='unknown')}")
    print(f"  log_level: {config.get('logging', 'log_level', default='INFO')}")
    
    print("\n✅ 测试4 完成")


def test_combined_workflow():
    """测试综合工作流"""
    print("\n" + "="*70)
    print("测试5：综合工作流（模拟实际处理）")
    print("="*70)
    
    # 模拟处理 Excel 文件
    excel_files = ['invoice_2024_01.xlsx', 'invoice_2024_02.xlsx', 'invoice_2024_03.xlsx']
    
    logger.info(f"开始处理 {len(excel_files)} 个 Excel 文件")
    _debug_var("待处理文件", excel_files)
    
    with ProgressLogger(total=len(excel_files), desc="导入 Excel") as pbar:
        for i, file in enumerate(excel_files):
            # 模拟读取文件
            time.sleep(0.1)
            
            # 生成模拟数据
            rows = 1000 + i * 100
            sheets = 3 + i
            
            # 输出日志
            logger.info(f"处理文件: {file}")
            _debug_var("行数", rows)
            _debug_var("Sheet数", sheets)
            
            # 更新进度
            pbar.update(1, msg=f"✅ {file} ({rows} 行, {sheets} 个sheet)")
    
    logger.info("✅ 所有文件处理完成")
    
    print("\n✅ 测试5 完成")


def main():
    """主测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试DEBUG日志和进度条')
    parser.add_argument('--quick', action='store_true', help='快速测试（跳过耗时操作）')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("VAT 审计系统 - DEBUG 日志和进度条功能测试")
    print("="*70)
    print(f"\n当前时间: {pd.Timestamp.now()}")
    print(f"DEBUG 模式: {'启用' if ENABLE_DEBUG else '禁用'}")
    print(f"日志级别: {logging.getLevelName(logger.level)}")
    
    if not ENABLE_DEBUG:
        print("\n提示：DEBUG 未启用")
        print("   要启用 DEBUG，请编辑 config.yaml，设置:")
        print("   logging:")
        print("     debug_enabled: true")
        print("\n继续运行测试...")
    
    try:
        # 测试 _debug_var
        test_debug_var()
        
        # 测试进度条
        if not args.quick:
            test_progress_bar()
        else:
            print("\n跳过进度条测试（快速模式）")
        
        # 测试日志级别
        test_logging_levels()
        
        # 测试配置
        test_configuration()
        
        # 综合测试
        if not args.quick:
            test_combined_workflow()
        else:
            print("\n跳过综合测试（快速模式）")
        
        print("\n" + "="*70)
        print("✅ 所有测试通过！")
        print("="*70)
        print("\n下一步：")
        print("1. 启用 DEBUG：编辑 config.yaml，设置 debug_enabled: true")
        print("2. 运行主程序：python VAT_Invoice_Processor.py")
        print("3. 查看日志：检查 Outputs/vat_audit.log")
        print("\n更多信息：")
        print("- DEBUG_AND_PROGRESS_QUICKREF.md - 快速参考")
        print("- LOGGING_AND_PROGRESS_GUIDE.md - 详细指南")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
