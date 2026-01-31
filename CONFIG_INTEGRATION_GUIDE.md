# 配置集中化管理示例
# 展示如何在VAT_Invoice_Processor.py中集成config_manager

## 步骤1：在文件开头导入配置管理器（已完成）
```python
# 导入配置管理器
try:
    from config_manager import get_config
    config = get_config()
    CONFIG_LOADED = True
except Exception as e:
    print(f"⚠️  配置文件加载失败，使用默认配置: {e}")
    config = None
    CONFIG_LOADED = False
```

## 步骤2：替换硬编码的配置常量

### 原代码（1045-1073行）：
```python
BUSINESS_TAG = "VAT_INV"
MAX_FAILURE_SAMPLE_PER_COL = 100
TAX_TEXT_TO_ZERO = True
ENABLE_PARALLEL_IMPORT = True
WORKER_COUNT = max(1, multiprocessing.cpu_count() - 1)
CSV_CHUNK_SIZE = 10000
STREAM_CHUNK_SIZE = 50000

INPUT_DIR = os.path.join(BASE_DIR, "Source_Data")
DB_DIR = os.path.join(BASE_DIR, "Database")
OUTPUT_DIR = os.path.join(BASE_DIR, "Outputs")
```

### 新代码（使用配置管理器）：
```python
# 从config.yaml加载配置，或使用默认值
if CONFIG_LOADED and config:
    BUSINESS_TAG = config.business_tag
    MAX_FAILURE_SAMPLE_PER_COL = config.max_failure_samples
    TAX_TEXT_TO_ZERO = config.tax_text_to_zero
    ENABLE_PARALLEL_IMPORT = config.parallel_enabled
    WORKER_COUNT = config.worker_count
    CSV_CHUNK_SIZE = config.csv_chunk_size
    STREAM_CHUNK_SIZE = config.stream_chunk_size
    logger.info("✅ 从config.yaml加载配置成功")
    
    INPUT_DIR = os.path.join(BASE_DIR, config.input_dir)
    DB_DIR = os.path.join(BASE_DIR, config.database_dir)
    OUTPUT_DIR = os.path.join(BASE_DIR, config.output_dir)
else:
    # 使用默认配置
    BUSINESS_TAG = "VAT_INV"
    MAX_FAILURE_SAMPLE_PER_COL = 100
    TAX_TEXT_TO_ZERO = True
    ENABLE_PARALLEL_IMPORT = True
    WORKER_COUNT = max(1, multiprocessing.cpu_count() - 1)
    CSV_CHUNK_SIZE = 10000
    STREAM_CHUNK_SIZE = 50000
    logger.warning("⚠️  使用默认配置（config.yaml未加载）")
    
    INPUT_DIR = os.path.join(BASE_DIR, "Source_Data")
    DB_DIR = os.path.join(BASE_DIR, "Database")
    OUTPUT_DIR = os.path.join(BASE_DIR, "Outputs")
```

## 配置使用效果

### ✅ 优势：
1. **无需改代码**：修改config.yaml即可调整所有配置
2. **集中管理**：所有配置在一个文件中，易于查看和维护
3. **向后兼容**：config.yaml不存在时自动使用默认值
4. **类型安全**：配置管理器提供类型检查和验证
5. **易于扩展**：新增配置项只需在yaml和config_manager中添加

### 📝 配置示例：

修改业务标识：
```yaml
business:
  tag: "CUSTOM_TAG"  # 修改这里即可，无需改动代码
```

调整性能参数：
```yaml
performance:
  csv_chunk_size: 20000      # 增大chunk提升速度
  stream_chunk_size: 100000  # 根据内存调整
```

修改worker数量：
```yaml
parallel:
  worker_count: 8  # 固定8个进程，或使用"auto"自动检测
```

### 🔧 当前实现状态：
- ✅ config.yaml 创建完成
- ✅ config_manager.py 创建完成
- ✅ VAT_Invoice_Processor.py 已部分集成
- ⏳ 需要手动替换1045-1073行的配置代码

### 📋 手动替换步骤：
1. 打开 VAT_Invoice_Processor.py
2. 找到第1045行附近（搜索"BUSINESS_TAG ="）
3. 删除旧的硬编码配置（约30行）
4. 粘贴上述"新代码"部分
5. 保存并测试

### ✅ 测试配置加载：
```bash
python config_manager.py
# 预期输出：
# 业务标识: VAT_INV
# 工作进程数: 15
# CSV块大小: 10000
# 日志级别: INFO
# ✅ 配置加载成功
```
