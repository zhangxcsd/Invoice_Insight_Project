# 生产环境部署指南

面向将 VAT 发票审计流水线部署到生产的最小步骤与检查清单。

## 1. 基本环境
- 操作系统：Windows 或 Linux（建议 64 位）。
- Python：3.10+，安装 `pip` 与 `venv`。
- 硬件：内存 ≥ 8GB；磁盘剩余空间 ≥ 源文件体积的 3 倍（Excel + SQLite + 临时 CSV）。
- 账户：使用专用服务账号运行，避免与个人账号混用。

## 2. 目录与权限
- 目录要求（可自定义，需在 `config.yaml` 中同步）：
  - `Source_Data/`：存放原始导出的 Excel/CSV。
  - `Database/`：存放 SQLite 数据库。
  - `Outputs/`：存放导出清单、日志、临时文件。
- 权限：为运行账号授予上述目录的读/写/删除权限；若使用 Windows 任务计划，确保计划任务以该账号运行。
- 网络盘注意事项：若路径位于网络盘或共享盘，建议预留本地缓存目录并在 `config.yaml` 中指向本地路径以降低 I/O 延迟。

## 3. 安装依赖
### 3.1 创建虚拟环境（推荐）
Windows PowerShell：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Linux/macOS：
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3.2 安装运行依赖
```bash
pip install -r requirements.txt
```
如需运行单元测试或基准脚本，安装开发依赖：
```bash
pip install -r requirements-dev.txt
```

## 4. 配置
1) 复制或编辑 `config.yaml`，重点字段：
   - `paths.*`：指向实际的输入/输出/数据库目录。
   - `parallel.worker_count`：生产建议先用 `"auto"`，再按机器核数微调。
   - `performance.io_throttle`：保持启用以避免高磁盘占用。
   - `logging.debug_enabled`：生产保持 `false`，避免大量调试输出。
2) 可运行 `python config_manager.py` 验证配置是否合法（失败会回落到默认配置并给出日志）。

## 5. 首次运行与验证
```bash
python VAT_Invoice_Processor.py
```
- 确认生成/更新：
  - 数据库：`Database/VAT_INV_Audit_Repo.db`（或你的业务标识）。
  - 输出：`Outputs/ods_sheet_manifest_<timestamp>.csv`、`Outputs/ods_import_summary_<timestamp>.csv`。
- 检查日志：`Outputs/vat_audit.log`（或 `config.yaml` 中自定义路径）。

## 6. 定时任务配置
### Windows 任务计划（任务计划程序）
1. 触发器：按需选择每日/每周运行时间。
2. 操作：`Program/script` 指向 python 可执行文件；`Add arguments` 填入 `VAT_Invoice_Processor.py`；`Start in` 设为仓库根目录。
3. 条件：关闭“空闲时停止”以避免长任务被中断。
4. 设置：勾选“无论用户是否登录都运行”并使用服务账号；允许按需运行。
5. 日志：确保 `Outputs/` 对任务账号可写；若需独立日志，可在 `config.yaml` 配置 `logging.log_file`。

### Linux cron 示例
在 crontab 中添加（每日 02:00 运行）：
```
0 2 * * * cd /path/to/VAT_Audit_Project && /path/to/python VAT_Invoice_Processor.py >> Outputs/vat_audit_cron.log 2>&1
```
- 确保环境变量（如 `PATH`、虚拟环境）在 cron 中可用；推荐使用绝对路径。

## 7. 运行健康检查
- 定期查看 `Outputs/ods_import_summary_*` 是否有失败条目。
- 若启用并行，监控日志中是否出现 I/O 限流提示；如频繁限流，可降低 `parallel.worker_count`。
- 可运行 `pytest tests/` 做冒烟回归（需安装开发依赖）。

## 8. 常见问题
- **权限错误**：检查运行账号是否对 `Source_Data/`、`Database/`、`Outputs/` 具备读写删除权限。
- **依赖缺失**：重新执行 `pip install -r requirements.txt`；若在离线环境，请提前准备 wheel 包并使用本地源安装。
- **长路径问题（Windows）**：在组策略或注册表中启用长路径支持，或将仓库放在较短路径下。

完成以上步骤后，即可在生产环境稳定运行并通过计划任务实现定时导入。