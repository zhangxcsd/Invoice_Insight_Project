# VATAuditPipeline 类快速参考

## 快速开始

### 完整执行
```python
from VAT_Invoice_Processor import VATAuditPipeline

pipeline = VATAuditPipeline()
pipeline.run()
```

### 单步调试
```python
pipeline = VATAuditPipeline()

# 步骤1：扫描Excel文件
excel_files = pipeline.scan_excel_files()

# 步骤2：扫描元数据（sheet分类、列识别）
files_meta = pipeline.scan_excel_metadata()

# 步骤3：初始化数据库
conn = pipeline.init_database()

# 步骤4：执行核心流程
# ... 调用 run_vat_audit_pipeline_legacy()

# 步骤5：清理资源
pipeline.clean_temp_files()
```

---

## 类的属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `process_time` | str | 处理时间戳 (YYYY-MM-DD HH:MM:SS) |
| `conn` | sqlite3.Connection | 数据库连接对象 |
| `excel_files` | list | Excel文件路径列表 |
| `files_meta` | dict | 文件元数据：{文件名: {sheet_info, detail_sheets, ...}} |
| `file_columns` | dict | 文件列集合：{文件名: [列名, ...]} |
| `sheet_manifest` | list | Sheet处理清单 |
| `error_logs` | list | 错误日志列表 |
| `temp_root` | str | 临时文件根目录 |

---

## 类的方法

### `__init__()` - 初始化

```python
pipeline = VATAuditPipeline()
```

**作用**:
- 生成处理时间戳
- 加载配置
- 初始化实例属性

**异常**: 配置加载失败时使用默认值

---

### `load_config()` - 加载配置

```python
pipeline.load_config()
```

**作用**:
- 从config.yaml加载配置
- 映射配置值到全局变量
- 创建必要目录
- 显示系统信息

**配置项**:
- business.tag → BUSINESS_TAG
- paths.input_dir → INPUT_DIR
- paths.database_dir → DB_DIR
- paths.output_dir → OUTPUT_DIR
- parallel.worker_count → WORKER_COUNT
- performance.csv_chunk_size → CSV_CHUNK_SIZE

**特点**:
- 配置失败自动降级到默认值
- 支持"auto"工作进程数（=CPU核心数）
- 显示系统可用内存和动态块大小

---

### `scan_excel_files()` - 扫描文件

```python
excel_files = pipeline.scan_excel_files()
# 返回: ['D:/path/file1.xlsx', 'D:/path/file2.xlsx', ...]
```

**作用**:
- 递归扫描INPUT_DIR下所有Excel文件
- 支持 .xls, .xlsx, .xlsm 格式
- 过滤临时文件（~$开头）

**返回值**: 文件路径列表

**日志**: "发现 N 个Excel文件"

---

### `scan_excel_metadata()` - 扫描元数据

```python
files_meta = pipeline.scan_excel_metadata()
```

**作用**:
- 读取每个Excel的所有sheet名称
- 提取sheet的列名称
- 按规则对sheet进行分类

**分类规则** (优先级顺序):

1. **特殊业务表** - 正则匹配
   - 铁路票 → RAILWAY
   - 建筑服务 → BUILDING_SERVICE
   - 不动产 → REAL_ESTATE_RENTAL
   - 机动车 → VEHICLE
   - 货物运输 → CARGO_TRANSPORT
   - 过路费 → TOLL

2. **信息汇总表** - sheet名包含"汇总"

3. **明细表** - sheet名包含"明细"或"基础信息"

4. **表头表** - sheet名包含"基础表"

5. **回退策略** - 按关键列识别

**返回值**: 元数据字典

```python
{
    '文件名1.xlsx': {
        'sheet_info': {'Sheet1': ['col1', 'col2'], ...},
        'detail_sheets': ['Sheet1'],
        'header_sheets': [],
        'summary_sheets': ['Sheet2'],
        'special_sheets': {}
    },
    ...
}
```

---

### `export_ods_manifest()` - 导出清单

```python
pipeline.export_ods_manifest(sheet_manifest, cast_stats, cast_failures)
```

**参数**:
- `sheet_manifest`: Sheet处理清单
- `cast_stats`: 类型转换统计
- `cast_failures`: 转换失败样本

**输出文件**:
- `ods_sheet_manifest_{timestamp}.csv`
- `ods_type_cast_manifest_{timestamp}.csv`
- `ods_type_cast_failures_{timestamp}.csv`

**特点**:
- 自动按列限制失败样本数
- 包含详细的统计信息
- 便于人工审查

---

### `clean_temp_files()` - 清理临时文件

```python
pipeline.clean_temp_files()
```

**作用**:
- 递归删除temp_root目录
- 失败时仅记录警告，不中断流程

**特点**:
- 不会删除重要数据
- 安全的清理机制
- 自动在run()末尾调用

---

### `init_database()` - 初始化数据库

```python
conn = pipeline.init_database()
```

**作用**:
- 创建SQLite连接
- 启用WAL模式（提升并发）
- 设置PRAGMA参数

**返回值**: sqlite3.Connection对象

**配置**:
- PRAGMA journal_mode=WAL
- PRAGMA synchronous=NORMAL

**特点**:
- 自动创建Database目录
- 连接失败时抛出异常

---

### `run()` - 运行流水线

```python
pipeline.run()
```

**工作流程**:
1. 扫描Excel文件
2. 扫描元数据（分类、列识别）
3. 初始化数据库
4. 导入ODS层（调用process_ods）
5. 加工DWD层（调用process_dwd）
6. 聚合ADS层（调用process_ads）
7. 导出清单（调用export_ods_manifest）
8. 清理临时文件（调用clean_temp_files）

**特点**:
- 完整的错误处理
- 资源确保释放（finally）
- 详细的日志记录
- 单个文件失败不中断全局

**日志**:
```
============================================================
>>> 【增值税发票审计流程】启动于 2026-01-03 21:33:26
============================================================
[进度信息...]
...
>>> 流程圆满完成！DB文件在 Database 文件夹中。
```

---

## 配置参数速查

### 业务配置
```yaml
business:
  tag: "VAT_INV"                    # 数据库文件名前缀
  description: "增值税发票专项审计"
```

### 路径配置
```yaml
paths:
  input_dir: "Source_Data"
  database_dir: "Database"
  output_dir: "Outputs"
```

### 性能配置
```yaml
parallel:
  worker_count: "auto"        # 工作进程数
  dynamic_worker_adjustment: true

performance:
  csv_chunk_size: 10000
  stream_chunk_size: 50000
  stream_chunk_dynamic: true  # 根据内存动态调整
```

### 数据处理
```yaml
data_processing:
  max_failure_samples: 100
  tax_text_to_zero: true
  filter_empty_rows: true
  filter_nan_rows: true
```

---

## 常见用法

### 用法1：默认完整运行
```python
from VAT_Invoice_Processor import VATAuditPipeline

pipeline = VATAuditPipeline()
pipeline.run()
```

### 用法2：单个方法调试
```python
pipeline = VATAuditPipeline()

# 只扫描文件，不执行导入
files = pipeline.scan_excel_files()
meta = pipeline.scan_excel_metadata()

# 打印分类结果
for fname, m in meta.items():
    print(f"{fname}: {len(m['detail_sheets'])} 个明细表, "
          f"{len(m['header_sheets'])} 个表头表")
```

### 用法3：自定义扩展
```python
class MyVATAuditPipeline(VATAuditPipeline):
    def scan_excel_metadata(self):
        # 调用父类方法
        meta = super().scan_excel_metadata()
        
        # 自定义处理
        for fname, m in meta.items():
            # 添加自定义分类
            ...
        
        return meta

pipeline = MyVATAuditPipeline()
pipeline.run()
```

### 用法4：分步执行控制
```python
pipeline = VATAuditPipeline()

try:
    pipeline.scan_excel_files()
    print(f"文件数: {len(pipeline.excel_files)}")
    
    pipeline.scan_excel_metadata()
    print(f"元数据: {len(pipeline.files_meta)} 个文件")
    
    pipeline.init_database()
    print("数据库已初始化")
    
    # 这里可插入自定义逻辑
    
finally:
    pipeline.clean_temp_files()
```

---

## 错误处理

### 配置加载失败
```
⚠️ 配置文件加载失败，使用默认配置: [error message]
```
- 程序继续运行，使用硬编码的默认值
- 不是致命错误

### 文件扫描失败
```
未发现Excel文件，流程终止
```
- 检查Source_Data目录是否存在
- 检查是否有有效的Excel文件

### 元数据扫描失败
```
读取失败（列扫描） {filename}: {error}
```
- 单个文件失败不影响其他文件
- 该文件会被标记为失败

### 数据库连接失败
```
无法连接到数据库 {path}: {error}
```
- 检查Database目录是否有写权限
- 检查磁盘空间是否充足

---

## 测试

### 运行测试套件
```bash
python test_pipeline_class.py
```

**输出**:
```
✅ 类初始化 - 通过
✅ 配置加载 - 通过
✅ 目录结构 - 通过
✅ 文件扫描 - 通过
✅ 元数据扫描 - 通过
✅ 数据库初始化 - 通过

总计: 6/6 测试通过 🎉
```

---

## 性能提示

### 优化文件扫描
```python
# 不建议：在Source_Data中放过多子目录
# ❌ Source_Data/year1/month1/file.xlsx

# 建议：平坦结构
# ✅ Source_Data/file.xlsx
```

### 优化内存使用
```yaml
# config.yaml
performance:
  stream_chunk_dynamic: true  # 启用动态块大小
  csv_chunk_size: 20000       # 增加块大小
```

### 优化并行处理
```yaml
parallel:
  worker_count: 8             # 根据CPU核数调整
  dynamic_worker_adjustment: true
```

---

## 常见问题解答

**Q: 如何修改数据库文件名前缀？**  
A: 编辑 config.yaml，修改 `business.tag`

**Q: 如何改变工作进程数？**  
A: 编辑 config.yaml，修改 `parallel.worker_count`

**Q: 如何自定义Sheet分类？**  
A: 继承VATAuditPipeline，重写 `scan_excel_metadata()` 方法

**Q: 如何添加自定义处理步骤？**  
A: 继承VATAuditPipeline，重写 `run()` 方法

**Q: 测试失败怎么办？**  
A: 运行 `python test_pipeline_class.py -v` 查看详细错误信息

---

## 相关文件导航

| 文件 | 说明 |
|------|------|
| [VAT_Invoice_Processor.py](VAT_Invoice_Processor.py) | 主程序 |
| [test_pipeline_class.py](test_pipeline_class.py) | 测试套件 |
| [config.yaml](config.yaml) | 配置文件 |
| [config_manager.py](config_manager.py) | 配置管理器 |
| [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) | 重构详解 |
| [REFACTORING_COMPLETION_REPORT.md](REFACTORING_COMPLETION_REPORT.md) | 完成报告 |

---

**最后更新**: 2026-01-03  
**版本**: 1.0 (重构版)  
**状态**: 生产就绪 ✅
