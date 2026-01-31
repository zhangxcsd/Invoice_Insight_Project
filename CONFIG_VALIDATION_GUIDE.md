# 配置参数校验功能说明

## 更新时间
2026-01-04

## 功能概述
新增配置参数校验逻辑，在程序启动时自动检查关键配置参数的合法性，发现问题时快速报错，避免后续运行时错误。

## 校验规则

### 应用级配置 (AppSettings)
通过 `validate_app_settings()` 函数校验：

| 参数 | 校验规则 | 错误提示 |
|------|---------|---------|
| `default_max_file_mb` | 必须 >= 10 | 过小会拒绝大多数正常文件 |

### 管道配置 (PipelineSettings)
通过 `validate_pipeline_config()` 函数校验：

| 参数 | 校验规则 | 错误提示 |
|------|---------|---------|
| `worker_count` | 必须 >= 1 | 不能为负数或零 |
| `csv_chunk_size` | 必须 >= 100 | 过小会导致频繁 I/O |
| `stream_chunk_size` | 必须 >= 1000 | 过小会影响流式处理性能 |
| `max_failure_sample_per_col` | 必须 >= 1 | 至少需要保留一个失败样本 |
| `input_dir` | 存在性检查（警告） | 不存在时给出警告并自动创建 |

## 实现位置

### 代码位置
- **文件**: `VAT_Invoice_Processor.py`
- **校验函数**:
  - `validate_app_settings()`: Line ~83
  - `validate_pipeline_config()`: Line ~1683

### 调用时机
1. **应用配置校验**: 在 `app_settings` 实例化后立即调用（Line ~111）
2. **管道配置校验**: 在 `pipeline_settings` 实例化后立即调用（Line ~1792）

## 使用示例

### 正常启动（配置合法）
```python
from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config

# 使用默认配置（所有参数都合法）
settings = PipelineSettings()
validate_pipeline_config(settings)  # ✅ 通过校验

# 程序日志输出:
# INFO: ✅ 配置参数校验通过
```

### 检测非法配置
```python
from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config

# 设置非法的 worker_count
settings = PipelineSettings()
settings.worker_count = -1

try:
    validate_pipeline_config(settings)
except ValueError as e:
    print(e)
    # 输出:
    # 配置参数校验失败：
    #   - worker_count 必须 >= 1，当前值: -1
```

### 同时检测多个错误
```python
settings = PipelineSettings()
settings.worker_count = 0           # 错误 1
settings.csv_chunk_size = 50        # 错误 2
settings.stream_chunk_size = 500    # 错误 3

try:
    validate_pipeline_config(settings)
except ValueError as e:
    print(e)
    # 输出:
    # 配置参数校验失败：
    #   - worker_count 必须 >= 1，当前值: 0
    #   - csv_chunk_size 必须 >= 100，当前值: 50（过小会导致频繁 I/O）
    #   - stream_chunk_size 必须 >= 1000，当前值: 500（过小会影响流式处理性能）
```

## 测试方法

### 运行自动化测试
```powershell
# 运行配置校验测试套件
python test_config_validation.py
```

测试覆盖：
- ✅ 合法的应用配置
- ✅ 非法的 max_file_mb (< 10)
- ✅ 非法的 worker_count (< 1)
- ✅ 非法的 csv_chunk_size (< 100)
- ✅ 非法的 stream_chunk_size (< 1000)
- ✅ 多个错误同时存在
- ✅ 合法的管道配置

### 手动测试
```powershell
# 测试非法配置
python -c "from VAT_Invoice_Processor import PipelineSettings, validate_pipeline_config; s=PipelineSettings(); s.worker_count=-1; validate_pipeline_config(s)"

# 预期输出：ValueError 异常
```

## 错误处理流程

```
程序启动
    ↓
加载配置类
    ↓
实例化配置对象
    ↓
调用校验函数
    ↓
检查所有参数 ──────────→ 发现错误 → 收集错误信息
    ↓ 全部合法                      ↓
记录日志: ✅ 通过           汇总错误并记录日志
    ↓                              ↓
继续执行                    抛出 ValueError
                                   ↓
                           程序终止（快速失败）
```

## 优势

### 1. 快速失败 (Fail Fast)
- 在程序启动阶段立即发现问题
- 避免运行时错误和数据损坏
- 减少调试时间

### 2. 清晰的错误信息
- 精确指出哪个参数不合法
- 说明为什么不合法
- 给出当前值和期望范围

### 3. 批量错误检测
- 一次性发现所有配置问题
- 不需要逐个修复后重试
- 提高配置调试效率

### 4. 防御性编程
- 主动防止无效配置
- 减少潜在的运行时错误
- 提高系统稳定性

## 扩展建议

### 未来可以添加的校验
1. **数据库路径校验**: 检查数据库目录是否可写
2. **内存限制校验**: 根据系统内存自动调整 chunk_size
3. **依赖检查**: 验证必要的 Python 包是否已安装
4. **配置兼容性**: 检查配置组合是否合理（如并行模式下 worker_count > 1）
5. **业务规则校验**: 验证特定业务场景的配置约束

### 与配置文件集成
```yaml
# config.yaml 示例
pipeline:
  worker_count: 4
  csv_chunk_size: 10000
  stream_chunk_size: 50000
  max_file_mb: 500

# 可以从配置文件加载并校验
settings = load_from_yaml('config.yaml')
validate_pipeline_config(settings)
```

## 相关文档
- [配置管理指南](README_CONFIG.md)
- [错误处理规范](ERROR_HANDLING_QUICK_REFERENCE.md)
- [测试指南](tests/README.md)

## 更新日志
- 2026-01-04: 初始版本
  - 添加 `validate_app_settings()` 函数
  - 添加 `validate_pipeline_config()` 函数
  - 创建测试套件 `test_config_validation.py`
  - 在配置初始化后自动调用校验
