"""
DEBUG 日志和进度条功能简化测试

运行命令:
    python test_debug_simple.py
"""

import sys
import time
import pandas as pd
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from VAT_Invoice_Processor import (
    logger, _debug_var, ProgressLogger, 
    ENABLE_DEBUG, config
)


def test_all():
    """运行所有测试"""
    print("\n" + "="*70)
    print("VAT 审计系统 - DEBUG 日志和进度条功能测试")
    print("="*70)
    
    print("\n当前配置:")
    print(f"  DEBUG 模式: {'启用' if ENABLE_DEBUG else '禁用'}")
    print(f"  日志级别: {logging.getLevelName(logger.level)}")
    print(f"  日志输出: {'启用' if config.get('logging', 'log_to_file') else '禁用'}")
    print(f"  日志文件: {config.get('logging', 'log_file', default='unknown')}")
    
    print("\n" + "-"*70)
    print("测试 1: _debug_var 函数")
    print("-"*70)
    
    # 测试标量
    _debug_var("count", 42)
    _debug_var("price", 99.99)
    _debug_var("enabled", True)
    
    # 测试列表
    files = ['file1.xlsx', 'file2.xlsx', 'file3.xlsx']
    _debug_var("excel_files", files)
    
    # 测试字典
    meta = {'file1': 3, 'file2': 5}
    _debug_var("metadata", meta)
    
    # 测试 DataFrame
    df = pd.DataFrame({
        'id': [1, 2, 3],
        'value': [100, 200, 300],
        'date': pd.date_range('2024-01-01', periods=3)
    })
    _debug_var("dataframe", df)
    
    print("\n[OK] 测试 1 完成")
    
    print("\n" + "-"*70)
    print("测试 2: 进度条 (ProgressLogger)")
    print("-"*70)
    
    # 简单进度条
    with ProgressLogger(total=30, desc="处理中") as pbar:
        for i in range(30):
            time.sleep(0.01)
            if i % 10 == 0 and i > 0:
                pbar.update(10, msg=f"已处理 {i} 条")
    
    print("[OK] 测试 2 完成")
    
    print("\n" + "-"*70)
    print("测试 3: 日志级别")
    print("-"*70)
    
    logger.debug("这是 DEBUG 消息")
    logger.info("这是 INFO 消息")
    logger.warning("这是 WARNING 消息")
    logger.error("这是 ERROR 消息")
    
    print("[OK] 测试 3 完成")
    
    print("\n" + "-"*70)
    print("测试 4: 综合场景")
    print("-"*70)
    
    items = ['item_1', 'item_2', 'item_3', 'item_4', 'item_5']
    logger.info(f"开始处理 {len(items)} 个项目")
    _debug_var("待处理项目", items)
    
    with ProgressLogger(total=len(items), desc="导入") as pbar:
        for item in items:
            time.sleep(0.05)
            pbar.update(1, msg=f"[OK] {item}")
    
    logger.info("所有项目处理完成")
    print("[OK] 测试 4 完成")
    
    print("\n" + "="*70)
    print("所有测试通过!")
    print("="*70)
    
    print("\n下一步:")
    print("1. config.yaml 中修改 debug_enabled")
    print("2. 运行: python VAT_Invoice_Processor.py")
    print("3. 查看日志: Outputs/vat_audit.log")
    print("\n更多信息:")
    print("- DEBUG_AND_PROGRESS_QUICKREF.md")
    print("- LOGGING_AND_PROGRESS_GUIDE.md")


if __name__ == "__main__":
    try:
        test_all()
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
