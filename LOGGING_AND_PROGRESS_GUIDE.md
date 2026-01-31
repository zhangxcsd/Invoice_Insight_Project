"""
日志分级和进度条可视化使用指南

本模块展示如何使用新增的DEBUG日志级别和tqdm进度条。
"""

# ============================================================================
# 1. 启用DEBUG日志
# ============================================================================

# 方式1：编辑config.yaml
"""
logging:
  debug_enabled: true    # 改为true启用DEBUG级别

运行程序，日志将输出详细信息，包括：
- 文件/目录操作
- Sheet分类细节
- 变量值和数据形状
- 函数调用信息（行号、函数名）
"""

# 方式2：在代码中设置（临时）
"""
from VAT_Invoice_Processor import ENABLE_DEBUG, logger
import logging

# 动态设置DEBUG
if some_condition:
    logger.setLevel(logging.DEBUG)
"""

# ============================================================================
# 2. 日志级别说明
# ============================================================================

"""
DEBUG    - 调试信息，仅开发环境使用
         示例：[DEBUG] Sheet[发票明细]列数=42
              [DEBUG] WORKER_COUNT=15
              
INFO     - 常规信息和进度
         示例：元数据扫描完成：10 个文件
              发现 10 个Excel文件
              
WARNING  - 警告（不影响程序）
         示例：读取工作表 Sheet1 表头失败: xxx
              配置文件加载失败，使用默认配置
              
ERROR    - 错误（可能影响结果）
         示例：删除旧表失败: xxx
              处理ODS层失败: xxx
"""

# ============================================================================
# 3. DEBUG日志格式
# ============================================================================

"""
启用DEBUG时，日志包含更多信息：

INFO 格式:  2026-01-03 21:33:25 INFO [vat_audit] 元数据扫描完成：10 个文件

DEBUG 格式: 2026-01-03 21:33:25 [DEBUG] [vat_audit:scan_excel_metadata:1925] 
            [扫描元数据] 开始处理文件: file1.xlsx, 包含 2 个sheet
            
包含的信息：
- 时间戳
- 日志级别
- 模块名和函数名:行号
- 消息内容
"""

# ============================================================================
# 4. 使用ProgressLogger创建进度条
# ============================================================================

from VAT_Invoice_Processor import ProgressLogger

# 示例1：简单的进度条
with ProgressLogger(total=100, desc="处理数据") as pbar:
    for i in range(100):
        # 做一些工作
        time.sleep(0.01)
        
        # 每10个项目输出一条日志
        if i % 10 == 0:
            pbar.update(10, msg=f"已处理 {i+10} 条记录")

# 输出样式：
"""
处理数据: 45%|████▌     | 45/100 [00:00<00:01, 50.00items/s]
已处理 50 条记录
"""

# 示例2：处理文件列表
files = ['file1.xlsx', 'file2.xlsx', 'file3.xlsx']
with ProgressLogger(total=len(files), desc="导入文件") as pbar:
    for file in files:
        # 处理文件
        result = process_file(file)
        
        # 输出结果
        pbar.update(1, msg=f"✅ 导入 {file}: {result['rows']} 行")

# ============================================================================
# 5. 使用_debug_var输出调试变量
# ============================================================================

from VAT_Invoice_Processor import _debug_var

# 示例1：输出列表
excel_files = ['file1.xlsx', 'file2.xlsx', 'file3.xlsx', 'file4.xlsx']
_debug_var("excel_files", excel_files)
# 输出：[DEBUG] excel_files: 长度=4, 值=['file1.xlsx', 'file2.xlsx', 'file3.xlsx']...

# 示例2：输出字典
files_meta = {
    'file1.xlsx': {'detail_sheets': ['Sheet1']},
    'file2.xlsx': {'detail_sheets': ['Sheet1', 'Sheet2']}
}
_debug_var("files_meta", files_meta)
# 输出：[DEBUG] files_meta: 长度=2, 键=['file1.xlsx', 'file2.xlsx']

# 示例3：输出DataFrame
import pandas as pd
df = pd.read_csv('data.csv')
_debug_var("df", df)
# 输出：[DEBUG] df: shape=(1000, 15), 列=['col1', 'col2', ..., 'col15']

# 示例4：输出标量值
count = 42
_debug_var("count", count)
# 输出：[DEBUG] count=42

# 示例5：带前缀输出
_debug_var("rows_processed", 1000, prefix="  ")
# 输出：  [DEBUG] rows_processed=1000

# ============================================================================
# 6. 日志输出到文件
# ============================================================================

"""
配置日志文件输出（config.yaml）：

logging:
  log_to_file: true              # 启用文件日志
  log_file: "vat_audit.log"      # 日志文件名
  max_bytes: 10485760            # 10MB 后轮换
  backup_count: 5                # 保留5个备份文件

日志文件位置：Outputs/vat_audit.log

轮换规则：
- 当日志文件超过10MB时，自动重命名为 vat_audit.log.1
- 之前的 .1 重命名为 .2，以此类推
- 最多保留5个备份文件
"""

# ============================================================================
# 7. 完整示例：生产环境 vs 调试环境
# ============================================================================

"""
【生产环境（config.yaml）】
logging:
  log_level: "INFO"
  debug_enabled: false
  log_to_file: true
  
结果：
- 仅输出 INFO/WARNING/ERROR 信息
- 日志简洁，不包含调试细节
- 不输出行号和函数名
- 文件大小受控制

【调试环境（config.yaml）】
logging:
  log_level: "DEBUG"
  debug_enabled: true
  log_to_file: true
  
结果：
- 输出所有DEBUG日志
- 包含文件/sheet/变量/行号等详细信息
- 日志文件会比较大
- 便于诊断问题
"""

# ============================================================================
# 8. 常见调试场景
# ============================================================================

"""
【场景1：诊断导入失败】
1. 编辑config.yaml，设置 debug_enabled: true
2. 运行程序
3. 查看日志输出：
   - 哪些sheet被识别为什么类型
   - 每个文件有多少列
   - 哪个sheet/文件导入失败
   - 具体的错误信息
4. 根据信息修复问题

【场景2：优化性能】
1. 启用DEBUG
2. 查看关键变量：
   - Worker数量
   - Chunk大小
   - 处理的行数
3. 根据日志调整config.yaml中的参数
4. 重新运行并对比性能

【场景3：验证数据质量】
1. 启用DEBUG
2. 查看每个sheet的列数和行数
3. 验证数据是否被正确分类
4. 检查类型转换的细节
"""

# ============================================================================
# 9. 进度条的实际应用
# ============================================================================

import time
from VAT_Invoice_Processor import ProgressLogger

def example_with_progress():
    """展示在实际处理中使用进度条"""
    
    # 模拟处理文件列表
    excel_files = [f'file_{i}.xlsx' for i in range(10)]
    
    # 创建进度条
    with ProgressLogger(total=len(excel_files), desc="导入Excel文件") as progress:
        for file in excel_files:
            # 模拟处理
            time.sleep(0.1)
            
            # 处理结果
            rows = 1000 + len(file) * 100
            
            # 更新进度条并输出日志
            progress.update(1, msg=f"✅ {file}: {rows} 行已导入")
    
    print("\n✅ 所有文件处理完成")

# 输出示例：
"""
导入Excel文件: 60%|██████    | 6/10 [00:00<00:00, 10.00items/s]
✅ file_3.xlsx: 1300 行已导入
✅ file_4.xlsx: 1400 行已导入
导入Excel文件: 100%|██████████| 10/10 [00:01<00:00, 10.00items/s]

✅ 所有文件处理完成
"""

# ============================================================================
# 10. 性能提示
# ============================================================================

"""
【优化日志性能】
- DEBUG模式下会有更多日志输出，轻微影响性能
- 生产环境建议关闭DEBUG
- 即使启用DEBUG，日志输出也是异步的，不会阻塞主程序

【优化进度条性能】
- 进度条更新频率不要太高（避免频繁的I/O）
- 每处理一定数量的项目再更新一次
- 使用 pbar.update(n) 批量更新而不是每次update(1)

【日志文件管理】
- 定期检查 Outputs/vat_audit.log* 文件大小
- 如果日志太多，在config.yaml中减少backup_count
- 或增加max_bytes来减少轮换频率
"""

# ============================================================================
# 11. 故障排除
# ============================================================================

"""
【问题1：日志没有输出到文件】
- 检查 log_to_file 是否为 true
- 检查 Outputs/ 目录是否存在且有写权限
- 查看 log_file 参数是否正确

【问题2：DEBUG日志没有显示】
- 检查 debug_enabled 是否为 true
- 检查 log_level 是否为 DEBUG
- 查看代码中是否使用了 logger.debug() 或 _debug_var()
- 注意：DEBUG日志仅在 ENABLE_DEBUG=True 时输出

【问题3：进度条显示错误】
- 检查是否在循环中正确调用 update()
- 确保 total 值与实际处理数相符
- 使用 with 语句确保进度条正确关闭

【问题4：日志文件过大】
- 减少 max_bytes（更频繁地轮换）
- 减少 backup_count（保留更少的备份）
- 关闭 log_to_file 或使用较低的日志级别
"""

if __name__ == "__main__":
    print(__doc__)
