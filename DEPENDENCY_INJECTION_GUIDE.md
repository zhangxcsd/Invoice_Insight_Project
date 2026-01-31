# 依赖注入与配置集中化指南

## 概述

为了提高可测试性和可维护性，将所有配置和运行时状态集中到 `PipelineSettings` 对象中，通过依赖注入传递给 worker 和辅助函数。

## 核心概念

### 1. PipelineSettings（已实现）

集中所有运行时设置的数据类：

```python
from vat_audit_pipeline.utils.sheet_processing import PipelineSettings

# 默认设置
settings = PipelineSettings()

# 从 config_manager 加载
from config_manager import get_config
config = get_config()
settings = PipelineSettings.from_config(config)

# 获取数据库路径
db_path = settings.get_database_path(base_dir)
```

**包含的配置**：
- `business_tag`, `input_dir`, `database_dir`, `output_dir`（业务和路径）
- `enable_parallel`, `worker_count`（并行）
- `csv_chunk_size`, `stream_chunk_size`（性能）
- `memory_threshold_percent`, `stream_switch_threshold_percent`（内存）
- `io_throttle_enabled`, `io_throttle_busy_percent`（I/O 限流）
- `max_failure_samples`, `tax_text_to_zero`（数据处理）
- `debug_mode`（DEBUG）

### 2. build_pipeline_settings()（已实现）

初始化 PipelineSettings 的便捷函数：

```python
from VAT_Invoice_Processor import build_pipeline_settings

settings = build_pipeline_settings(config, base_dir)
# 自动：
# - 从 config 对象加载配置
# - 路径从相对转绝对
# - 确保目录存在
```

### 3. 注入模式

将 `settings` 对象传递给 worker 和辅助函数（取代分散的全局变量读取）：

**旧模式（全局变量）**：
```python
def process_file_worker(args):
    file, meta, ... = args
    # 依赖全局变量：BUSINESS_TAG, CONFIG_LOADED, config, TAX_TEXT_TO_ZERO ...
    target_table = f"ODS_{BUSINESS_TAG}_TEMP_TRANSIT"
    df = cast_and_record(df, fname, sheet, ..., tax_text_to_zero=TAX_TEXT_TO_ZERO)
```

**新模式（依赖注入）**：
```python
def process_file_worker(args, settings: PipelineSettings):
    file, meta, ... = args
    # settings 已注入，清晰明了
    target_table = f"ODS_{settings.business_tag}_TEMP_TRANSIT"
    df = cast_and_record(df, fname, sheet, ..., tax_text_to_zero=settings.tax_text_to_zero)
```

## 迁移步骤

### Step 1: 初始化 PipelineSettings（在 VATAuditPipeline 中）

```python
class VATAuditPipeline:
    def __init__(self):
        self.load_config()  # 现有的配置加载
        
        # 新增：构建 PipelineSettings
        self.settings = build_pipeline_settings(config, BASE_DIR)
        
        # 验证配置
        logger.info(f"Pipeline Settings: business_tag={self.settings.business_tag}, "
                   f"input_dir={self.settings.input_dir}, debug_mode={self.settings.debug_mode}")
```

### Step 2: 更新 worker 函数签名

原来：
```python
def process_file_worker_with_queue(args):
    file, meta, temp_dir_root, process_time, detail_columns, ..., df_queue, use_csv_fallback = args
```

改为：
```python
def process_file_worker_with_queue(args, settings: PipelineSettings):
    file, meta, temp_dir_root, process_time, detail_columns, ..., df_queue, use_csv_fallback = args
    # 现在可以用 settings.business_tag 替代全局 BUSINESS_TAG
    # 现在可以用 settings.debug_mode 替代全局 DEBUG_MODE
```

### Step 3: 更新 multiprocessing.Pool.apply_async 调用

原来：
```python
pool.apply_async(process_file_worker_with_queue, (args_tuple,))
```

改为：
```python
pool.apply_async(process_file_worker_with_queue, (args_tuple, self.settings))
```

或使用 partial：
```python
from functools import partial
worker_fn = partial(process_file_worker_with_queue, settings=self.settings)
pool.apply_async(worker_fn, (args_tuple,))
```

## 现有全局变量映射

| 全局变量 | PipelineSettings 字段 |
|---------|-------------------|
| `BUSINESS_TAG` | `settings.business_tag` |
| `INPUT_DIR` | `settings.input_dir` |
| `DB_DIR` | `settings.database_dir` |
| `OUTPUT_DIR` | `settings.output_dir` |
| `DEBUG_MODE` | `settings.debug_mode` |
| `TAX_TEXT_TO_ZERO` | `settings.tax_text_to_zero` |
| `ENABLE_PARALLEL_IMPORT` | `settings.enable_parallel` |
| `WORKER_COUNT` | `settings.worker_count` |
| `CSV_CHUNK_SIZE` | `settings.csv_chunk_size` |
| `STREAM_CHUNK_SIZE` | `settings.stream_chunk_size` |

## 单元测试示例

```python
from vat_audit_pipeline.utils.sheet_processing import PipelineSettings
from VAT_Invoice_Processor import build_pipeline_settings

def test_process_single_sheet_with_custom_settings():
    # 创建自定义设置
    settings = PipelineSettings(
        business_tag="TEST_INV",
        debug_mode=True,
        tax_text_to_zero=False,
        max_failure_samples=50
    )
    
    # 调用 worker 传入设置
    handler = get_sheet_handler(sheet_name, meta, ..., settings.business_tag)
    rows, classification, csv_path = process_single_sheet(
        ..., settings=settings, ...
    )
    
    # 验证
    assert classification in ['detail', 'header', 'summary', 'ignored', 'error']
```

## 后续优化

- [ ] 将 `process_file_worker` 和 `process_file_worker_with_queue` 的其他参数合并到 `WorkerArgs` 数据类
- [ ] 为 `settings` 添加验证方法（`validate()`）
- [ ] 在 VATAuditPipeline 中懒加载 settings（仅在需要时构建）
- [ ] 支持 settings 的序列化/反序列化用于日志和审计
