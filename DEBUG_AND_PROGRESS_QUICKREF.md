# DEBUG 日志和进度条快速参考

## 启用 DEBUG 日志

编辑 `config.yaml`：
```yaml
logging:
  debug_enabled: true    # 改为 true
```

## 日志级别说明

| 级别 | 用途 | 示例输出 |
|------|------|---------|
| DEBUG | 调试信息（仅开发用） | `[DEBUG] Sheet[明细] 列数=42` |
| INFO | 常规进度和结果 | `元数据扫描完成：10 个文件` |
| WARNING | 警告（可能有问题） | `读取表头失败，使用默认值` |
| ERROR | 错误（需要处理） | `处理失败: xxx` |

## 日志输出示例

**DEBUG 启用时：**
```
2026-01-03 21:33:25 [DEBUG] [vat_audit:scan_excel_metadata:1952] Sheet[发票明细] 列数=42
2026-01-03 21:33:25 [DEBUG] [vat_audit:scan_excel_metadata:1953] 文件汇总: 明细=3, 表头=2, 汇总=1, 特殊=0
```

**DEBUG 禁用时：**
```
2026-01-03 21:33:25 元数据扫描完成：6 个sheet，10 列
```

## 常用代码片段

### 输出调试变量
```python
from VAT_Invoice_Processor import _debug_var

_debug_var("excel_files", excel_files)  # 自动检测类型和长度
_debug_var("count", 42)                  # 标量值
_debug_var("df", dataframe)              # DataFrame
```

### 创建进度条
```python
from VAT_Invoice_Processor import ProgressLogger

with ProgressLogger(total=100, desc="处理中") as pbar:
    for item in items:
        process(item)
        pbar.update(1)
```

### 输出进度消息
```python
with ProgressLogger(total=100, desc="处理中") as pbar:
    for i, item in enumerate(items):
        process(item)
        if i % 10 == 0:
            pbar.update(10, msg=f"已处理 {i+10} 条")
```

## config.yaml 相关配置

```yaml
logging:
  # 启用 DEBUG 级别日志
  debug_enabled: true/false
  
  # 最低日志级别
  log_level: "DEBUG"  # 必须是 DEBUG 才能显示 DEBUG 消息
  
  # 是否输出到文件
  log_to_file: true
  
  # 日志文件名（输出到 Outputs/ 目录）
  log_file: "vat_audit.log"
  
  # 单个日志文件最大字节数（超过后自动轮换）
  max_bytes: 10485760  # 10MB
  
  # 保留的备份文件数
  backup_count: 5
```

## ProgressLogger 类方法

```python
class ProgressLogger:
    def __init__(total, desc, use_tqdm=True):
        """创建进度条"""
        
    def update(n=1, msg=None):
        """更新进度，可选输出消息"""
        
    def set_description(desc):
        """中途改变进度条描述"""
        
    def close():
        """关闭进度条"""
        
    # 上下文管理器
    with ProgressLogger(...) as pbar:
        ...
```

## _debug_var 函数

```python
def _debug_var(name, value, prefix=""):
    """
    条件输出调试变量（仅当 ENABLE_DEBUG=True 时）
    
    自动处理：
    - 列表/元组: 显示长度和前3个元素
    - 字典: 显示长度和键
    - DataFrame: 显示形状和列名
    - 其他: 原样显示
    
    示例：
    _debug_var("rows", df_list)  # [DEBUG] rows: 长度=1000, 值=[...]
    _debug_var("config", cfg_dict)  # [DEBUG] config: 长度=5, 键=[...]
    """
```

## 日志文件位置

- 日志文件：`Outputs/vat_audit.log`
- 备份文件：`Outputs/vat_audit.log.1`, `.log.2`, 等

## 常见场景

### 调试导入问题
1. 启用 DEBUG：`config.yaml` → `debug_enabled: true`
2. 运行程序
3. 查看日志中的 sheet 分类和列数信息

### 优化性能
1. 启用 DEBUG，运行一遍
2. 查看处理的行数、列数、worker 数量
3. 编辑 `config.yaml` 的相关参数
4. 禁用 DEBUG，再运行一遍测试性能

### 验证数据质量
1. 启用 DEBUG
2. 查看每个 sheet 的统计信息
3. 检查类型转换的细节
4. 查看临时文件等中间过程

## 性能提示

- **生产环境**：禁用 DEBUG（`debug_enabled: false`）
- **调试环境**：启用 DEBUG（`debug_enabled: true`）
- **日志轮换**：日志超过 `max_bytes` 自动轮换到 `.1`, `.2` 等
- **进度条**：更新频率不要过高，建议批量更新

## 故障排除

| 问题 | 检查项 |
|------|--------|
| DEBUG 日志没输出 | 1. `debug_enabled: true` 2. `log_level: "DEBUG"` |
| 日志没输出到文件 | 1. `log_to_file: true` 2. 检查 `Outputs/` 目录权限 |
| 进度条显示错误 | 1. `total` 值正确 2. 正确调用 `update()` |
| 日志文件过大 | 减少 `max_bytes` 或 `backup_count` |

## 相关文档

- [详细指南](LOGGING_AND_PROGRESS_GUIDE.md)
- [配置说明](README_CONFIG.md)
- [快速开始](QUICKSTART_CONFIG.md)

---
最后更新：2026-01-03 | 版本：2.0
