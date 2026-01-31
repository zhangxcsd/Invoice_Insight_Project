# VAT_Audit_Project

VAT 发票审计流水线 — 最小可运行 PoC

> 提示：自 2026-01 起核心逻辑已拆分为包 `vat_audit_pipeline`；`VAT_Invoice_Processor.py` 仅作为兼容入口，等价于运行 `python -m vat_audit_pipeline.main`。

## 概要
本项目提供一个轻量的发票处理流水线：
- 从 `Source_Data/` 目录递归读取税控系统导出的 Excel 文件（支持多个 sheet）；
- 将“明细表（information detail）”写入 ODS（临时中转表），并构建按年度分区的 DWD（标准表，去重）；
- 把被判为重复的原始记录保存到 LOG 表以便审计；
- 生成简单 ADS 检测（例如异常税率）；
- 输出辅助文件到 `Outputs/`（如 sheet 分类 manifest、导入汇总）。

## 关键行为（重要）
- 全量重建（默认）：每次运行脚本时会删除并重新构建 ODS 中间表，保证数据库与 `Source_Data/` 的镜像一致（新增/删除/修改都会反映）。
- Sheet 识别：优先**按 sheet 名模糊匹配**（默认规则匹配 `信息汇总|明细|发票明细` 作为明细表；`发票基础|合计|汇总` 作为发票级 header），当文件中未命中规则时会退回到表头关键列检测作为补充。匹配结果会输出到 `Outputs/ods_sheet_manifest_<timestamp>.csv` 以便人工核验。
- 导入汇总：脚本会统计扫描到的 Excel 数量、成功导入数、列扫描失败数与读取失败数，并写入 `Outputs/ods_import_summary_<timestamp>.csv`。
- 跳过临时/锁定文件（例如以 `~$` 开头的临时 Office 文件）。

## 环境要求

### Python 版本
- **最低版本**: Python 3.8
- **推荐版本**: Python 3.10 或更高
- **已测试版本**: Python 3.14

### 依赖包安装

**快速安装（推荐）**:
```powershell
# 安装所有依赖包
pip install -r requirements.txt

# 验证安装是否成功
python verify_dependencies.py
```

**主要依赖包**:
- `pandas>=2.0.0` - 数据处理核心库
- `numpy>=1.24.0` - 数值计算支持
- `openpyxl>=3.0.0` - Excel 2010+ (.xlsx) 文件支持
- `xlrd==1.2.0` - Excel 97-2003 (.xls) 文件支持
- `chardet>=5.0.0` - 文件编码自动检测
- `psutil>=5.9.0` - 系统资源监控
- `tqdm>=4.65.0` - 进度条显示

**详细说明**: 查看 [DEPENDENCIES.md](DEPENDENCIES.md) 获取完整的依赖安装指南、常见问题解决方案和离线安装方法。

## 运行方法
需要 Python 环境并安装依赖包（见上方"环境要求"）。

示例（等价任选其一）：

Windows PowerShell:

```powershell
# 兼容入口
python VAT_Invoice_Processor.py

# 新的包入口
python -m vat_audit_pipeline.main

# 新增：CLI（click）入口
python -m vat_audit_pipeline.main run -i Source_Data -c config.yaml -v
python -m vat_audit_pipeline.main analyze 2025 -c config.yaml
```

## 打包为 Windows 可执行文件
- 安装依赖（包含 PyInstaller）：运行 pip install -r [requirements.txt](requirements.txt) 与 pip install -r [requirements-dev.txt](requirements-dev.txt)
- 使用 [scripts/build_exe.ps1](scripts/build_exe.ps1) 打包（默认 --onedir，可加 -OneFile 生成单文件）：
  - PowerShell: pwsh scripts/build_exe.ps1 或 pwsh scripts/build_exe.ps1 -OneFile
- 打包产物位于 dist/ 下：
  - onedir: dist/VAT_Invoice_Processor/（脚本已自动复制 [config.yaml](config.yaml)/[config_default.yaml](config_default.yaml) 并创建 [Source_Data/](Source_Data)/[Database/](Database)/[Outputs/](Outputs)）
  - onefile: dist/VAT_Invoice_Processor.exe（同目录会生成 [Source_Data/](Source_Data)/[Database/](Database)/[Outputs/](Outputs)，可直接放待处理 Excel）
- 分发时请整体复制 dist 生成的目录/文件到目标机器，在 [Source_Data/](Source_Data) 放入 Excel 数据后，直接双击或运行 exe 即可。

## 部署
- 生产环境依赖安装、目录权限与定时任务配置请见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 开发检查（lint/type）
- 安装开发依赖：`pip install -r requirements-dev.txt`
- 运行 ruff（风格/命名/导入/文档）：`ruff check .`
- 运行 mypy（类型提示快速扫）：`mypy VAT_Invoice_Processor.py config_manager.py utils`

## 数据库抽象层（DAO）
- 从 **Phase 5** 开始使用轻量级数据库抽象层避免 SQL 注入风险
- 所有数据库操作使用参数化查询（parameterized queries）
- 详见 [DATABASE_DAO_INTEGRATION_GUIDE.md](DATABASE_DAO_INTEGRATION_GUIDE.md) 与 `utils/database.py`
- 运行 DAO 单元测试：`pytest tests/test_database_dao.py -v`

## 统一错误处理系统 🚨
- 从 **Phase 6** 开始集成统一的错误处理机制
- **结构化异常**：14 个异常类，涵盖文件、数据库、数据、Excel 等场景
- **ErrorCollector**：集中收集、分类、统计和输出错误
- **丰富的上下文**：每个错误都包含完整的上下文信息和原始异常追踪
- 详见以下文档：
  - [ERROR_HANDLING_INTEGRATION_GUIDE.md](ERROR_HANDLING_INTEGRATION_GUIDE.md) - 详细集成指南
  - [ERROR_HANDLING_QUICK_REFERENCE.md](ERROR_HANDLING_QUICK_REFERENCE.md) - 快速参考
  - [ERROR_HANDLING_COMPLETION_REPORT.md](ERROR_HANDLING_COMPLETION_REPORT.md) - 实现报告
- 运行错误处理单元测试：`pytest tests/test_error_handling.py -v`

## 输出说明
- Database/: 包含 SQLite 数据库文件（`VAT_INV_Audit_Repo.db`），结构包括：
  - `ODS_VAT_INV_TEMP_TRANSIT`（临时明细表，运行后会被删除）
  - `ODS_VAT_INV_HEADER`（发票级 header 表，保存合计/票面级信息）
  - `DWD_VAT_INV_<yr>_STND`（按年度去重标准表）
  - `LOG_VAT_INV_<yr>_DEDUP`（重复记录轨迹）
  - `ADS_VAT_INV_TAX_ANOMALY`（异常税率检测结果）
- Outputs/:
  - `ods_sheet_manifest_<timestamp>.csv`：每个文件中每个 sheet 的分类（detail/header/ignored/error）和表头列
  - `ods_import_summary_<timestamp>.csv`：导入统计汇总（总数、成功、失败等）

## 可配置点（在脚本内）
- `DETAIL_RE` / `HEADER_RE`（正则）用于按 sheet 名识别；可按需添加关键词（例如加入“明细表”等）。
- 去重策略：当前 DWD 使用 `MIN(rowid)` 保留组内第一条记录。如需按时间保留最新一条，请修改去重 SQL（或使用窗口函数）。

## 注意事项
- 建议先在副本数据上运行并检查 `Outputs/` 中生成的 manifest，确认识别规则是否满足你的导出样式。
- 若导入过程中遇到列不一致，脚本已实现按列并集创建 ODS 表并对每个文件进行补齐；如需要更精细的 schema 管理可增设 manifest->schema 自动化流程。

## 并行导入与性能优化 🔧

- 新增并行导入 PoC（默认启用），配置项位于 `config.yaml`（经 `config_manager` 加载）或包内默认设置：
  - `ENABLE_PARALLEL_IMPORT`：True/False（切换并行/串行导入）
  - `WORKER_COUNT`：并行 worker 数量（默认 CPU-1）
  - `CSV_CHUNK_SIZE` / `STREAM_CHUNK_SIZE`：合并与流式读取的块大小阈值
- 实现细节：每个 worker 读取单个 Excel 并将分类过、类型化后的 sheet 写为临时 CSV（默认目录 `Outputs/tmp_imports/<timestamp>/`），主进程按表合并 CSV 到 SQLite，并在合并时启用 `PRAGMA journal_mode=WAL` 与 `PRAGMA synchronous=OFF` 以提升写入吞吐。

### 临时文件清理 🧹

为确保稳定的资源使用，实现了三层自动清理机制：

1. **启动时清理旧临时目录** - `cleanup_old_temp_files()`
   - 扫描 `Outputs/tmp_imports/` 中的旧目录
   - 删除除当前运行外的所有临时文件
   - 避免长期累积磁盘占用

2. **运行时全局追踪** - `_CURRENT_TEMP_DIR`
   - 记录当前运行的临时目录
   - 支持精确清理当前会话产生的文件

3. **程序退出自动清理** - `atexit` 注册
   - 注册清理处理器处理正常退出、异常、Ctrl+C 等所有场景
   - 保证临时文件无论如何都会被清理

**验证**：运行 `python test_cleanup.py` 查看 5 个清理功能测试（全部通过 ✓）

详见 [TEMP_FILES_CLEANUP_SUMMARY.md](TEMP_FILES_CLEANUP_SUMMARY.md) 获取实现细节。

### 编码自动检测 🌐

新增**自动编码检测**功能，支持多种文件编码（UTF-8、GBK、GB2312 等）：

- **chardet 库集成**：自动识别文件编码
- **备选编码机制**：编码识别失败时自动尝试备选编码
- **透明化处理**：无需用户指定编码，系统自动适配
- **支持的编码**：
  - UTF-8 / UTF-8-SIG (with BOM)
  - GBK / GB2312 (Chinese)
  - CP936 (Windows Chinese)
  - 其他 30+ 种编码

**核心函数**：
```python
from VAT_Invoice_Processor import detect_encoding, read_csv_with_encoding_detection

# 检测编码
encoding = detect_encoding('file.csv')

# 自动检测并读取 CSV
df = read_csv_with_encoding_detection('file.csv')

# 或指定编码
df = read_csv_with_encoding_detection('file.csv', encoding='gbk')
```

**验证**：运行 `python test_encoding_detection.py` 查看 4 个编码测试（全部通过 ✓）

详见 [ENCODING_DETECTION_GUIDE.md](ENCODING_DETECTION_GUIDE.md) 获取完整文档。

### 内存监控与自动流式处理 🧠

- **监控与阈值**：新增 `performance.memory_monitoring` 配置块，可设置 `memory_threshold_percent`（告警阈值）、`stream_switch_threshold_percent`（触发流式处理阈值）、`large_file_streaming_mb`（大文件直接流式的尺寸）。
- **自动切换**：当系统内存占用超过阈值或文件体积过大时，worker 会跳过 `pd.read_excel` 全量载入，直接走 `stream_read_and_write_csv` 流式路径，避免 OOM。
- **依赖说明**：功能依赖 `psutil`（已加入 requirements），请安装/更新依赖后运行。
- **快速配置示例**（节选）：

```yaml
performance:
  memory_monitoring:
    enabled: true
    memory_threshold_percent: 80
    stream_switch_threshold_percent: 75
    large_file_streaming_mb: 100
```

> 运行时可在日志中看到“根据内存状态已设置流式处理模式”提示，确认已进入受控流式路径。

## 日志与诊断 📋

- 日志：脚本现在使用标准 Python `logging`（模块 logger 名为 `vat_audit`），支持控制台输出与文件输出（默认文件：`Outputs/vat_audit.log`）。默认日志级别为 `INFO`，可在脚本顶部修改 `LOG_LEVEL`、`LOG_TO_FILE`、`LOG_FILE` 等配置。

### 📊 新增：DEBUG 日志和进度条可视化 (v2.0) ✨

最新版本新增了两项关键功能提升开发体验和运行透明度：

#### 1️⃣ DEBUG 日志级别
- 新增 DEBUG 级别，包含文件名、函数名、行号等详细信息
- 创建 `_debug_var()` 函数智能输出调试变量（自动格式化）
- 生产安全：DEBUG 默认禁用，可通过 `config.yaml` 灵活启用

#### 2️⃣ 进度条可视化  
- 集成 tqdm 库提供美观的实时进度条显示
- 创建 `ProgressLogger` 类支持进度消息输出
- 自动处理无法获取总数的情况

**快速开始**：
1. 查看 [DEBUG_AND_PROGRESS_QUICKREF.md](DEBUG_AND_PROGRESS_QUICKREF.md) - 一页快速参考
2. 编辑 `config.yaml`，设置 `debug_enabled: true` 启用 DEBUG（可选）
3. 运行 `python test_debug_simple.py` 验证功能

**详细文档**：
- [LOGGING_AND_PROGRESS_GUIDE.md](LOGGING_AND_PROGRESS_GUIDE.md) - 详细教程（15+ 示例）
- [DEBUG_FIX_SUMMARY.md](DEBUG_FIX_SUMMARY.md) - 实现细节
- [COMPLETION_REPORT.md](COMPLETION_REPORT.md) - 完整报告

---

- 诊断：当发生异常（读取/类型化/合并等阶段）会同时：
  - 记录结构化错误条目（`file`/`sheet`/`stage`/`error_type`/`message`），并在流程结束时导出为 `Outputs/process_error_logs_<timestamp>.csv`；
  - 将异常以日志形式写入 `vat_audit.log`（便于回溯），并在 DEBUG 级别下包含更多调试信息。
- 如何验证：
  - 运行脚本后检查 `Outputs/vat_audit.log`（或更改 `LOG_FILE` 路径）；
  - 使用 `scripts/check_indexes.py` / `Outputs/` 中的 manifest 与 `process_error_logs` 来定位问题。

- 如何验证与基准测试：
  - 安装开发依赖：`pip install -r requirements-dev.txt`
  - 运行单元测试：`pytest tests/`
  - 运行基准脚本：`python scripts/benchmark_import.py`（脚本会在 `Source_Data/` 中创建样本并依次运行以测不同文件量下的耗时）

> 注意：并行实现会在 `Outputs/tmp_imports` 下生成临时 CSV，默认不自动删除以方便调试；如需自动清理可编辑脚本以在合并完成后删除该目录。

## 联系与贡献
请在提交 PR 时包含变更说明与测试说明。欢迎贡献改进匹配规则、增加单元测试或将后端迁移到更强的数据库（如 Postgres）。

## 事务与索引优化 ✅

- 最近改进：为减少频繁的隐式提交（尤其在大量 `to_sql` 写入时），脚本已在合并临时 CSV 到 SQLite 时对每个目标表使用显式事务（`BEGIN IMMEDIATE` / `COMMIT`），并在非并行路径中按文件批量提交，以显著降低写入开销并提升吞吐。
- 索引：在 DWD（`DWD_{BUSINESS_TAG}_{yr}_STND`）和生成的 LEDGER 表上创建了针对常用查询键的索引（如 `发票代码, 发票号码`, `数电发票号码`, `开票日期`），以加速后续聚合与查找。
- 验证：索引会在脚本运行过程中自动创建，使用 `scripts/check_indexes.py` 可列出当前数据库中的索引。

建议：在处理非常大的数据集时，先以小批量文件跑一次，确认 `WORKER_COUNT`、`CSV_CHUNK_SIZE` 与 `STREAM_CHUNK_SIZE` 的默认值是否合适，再放大规模运行。
