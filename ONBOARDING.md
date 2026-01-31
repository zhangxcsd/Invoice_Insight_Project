# 新人上手指南（VAT_Audit_Project）

面向刚入门的 Python 学习者，帮助理解业务背景、代码入口与安全改动点。

## 1. 业务背景
- 目标：对增值税发票导出（Excel/CSV）做清洗、入库、去重与简单审计。
- 数据流：`Source_Data/` 原始文件 → ODS（临时表）→ DWD（按年份去重标准表）→ LOG（去重轨迹）→ ADS（异常税率示例）。
- 输出：`Outputs/` 目录包含导入 manifest、错误日志、调试抽样（DEBUG 模式）。

## 2. 快速运行
```bash
python VAT_Invoice_Processor.py
```
- 配置：`config.yaml`（有详细注释）。修改路径或并行参数后重新运行即可生效。
- 验证：运行后查看 `Outputs/ods_sheet_manifest_*.csv` 与 `Outputs/vat_audit.log`。

## 3. 代码地图
- `VAT_Invoice_Processor.py`：主入口，封装扫描→导入→去重→导出全流程的 `VATAuditPipeline`。
- `config_manager.py`：加载与验证配置（合并 `config_default.yaml`）。
- `utils/`：通用工具（编码检测、数据类型化、日志/进度）。
- `scripts/`：基准/检查脚本示例。

## 4. 推荐阅读顺序
1) `README.md` / `DEPLOYMENT.md`：了解整体目标与部署步骤。
2) `config.yaml`：熟悉可调参数（路径、并行、性能、日志）。
3) `VAT_Invoice_Processor.py`：重点关注
   - 顶部注释：流程概览
   - `VATAuditPipeline.load_config`：配置如何进入代码
   - `scan_excel_files`：输入过滤
   - `process_file_worker*`：文件→CSV/队列→SQLite 的核心逻辑
   - `build_dwd_tables` / `export_manifests`：去重与输出

## 5. 安全改动建议
  - 保持函数粒度小（便于测试和回退）。
  - 添加/更新 docstring，解释“为什么要这样处理”（业务或性能原因）。
  - 运行 `pytest`（如安装了 dev 依赖）或最少用小样本文件跑一遍主程序。

## 6. 开发自检（lint / type）
- 安装开发依赖：`pip install -r requirements-dev.txt`
- 风格与命名检查：`ruff check .`
- 类型快速扫：`mypy VAT_Invoice_Processor.py config_manager.py utils`

## 7. 常见问题
- 性能/内存问题：在 `config.yaml` 调低 `parallel.worker_count`，开启 `performance.io_throttle`，或增大 `performance.stream_chunk_*`。

祝学习顺利，如遇不清楚的业务概念，可在 docstring 注释中搜索“业务背景”关键词。
