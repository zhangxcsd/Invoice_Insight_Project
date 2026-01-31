# 代码复杂度重构总结（2026-01-04）

## 目标
降低 VAT_Invoice_Processor.py 的复杂度和全局变量依赖，提高可读性、可测试性和可维护性。

## 已完成的工作

### 阶段 1：代码编写标准与文档（完成 ✓）
- [STYLE.md](STYLE.md): Python 编码规范（PEP8/257、命名、日志、配置、依赖）
- [ONBOARDING.md](ONBOARDING.md): 新人上手指南（业务背景、推荐阅读顺序、安全改动建议）
- 增强 module/class 级别 docstring，补充业务背景和学习路径

### 阶段 2：工具链与检查（完成 ✓）
- [pyproject.toml](pyproject.toml): ruff + mypy 配置（PEP8、命名、文档、类型检查）
- [requirements-dev.txt](requirements-dev.txt): 添加 ruff + mypy
- [README.md](README.md#L33-L39) 和 [ONBOARDING.md](ONBOARDING.md#L29-L36): 文档化 lint/type 检查命令

### 阶段 3：函数分解与策略模式（完成 ✓）
创建 [utils/sheet_processing.py](utils/sheet_processing.py)，包含：
- `SheetTypeMapping`: 数据类，统一 sheet 类型处理的元数据（表名、列、分类）
- `SheetProcessingContext`: 数据类，sheet 处理上下文
- `get_sheet_handler()`: 工厂函数，替代嵌套 if-elif-elif
- `normalize_sheet_dataframe()`: 纯函数，类型化 + 审计 + 年份提取
- `write_to_csv_or_queue()`: 纯函数，队列/CSV 写入
- `process_single_sheet()` 辅助函数：单 sheet 处理流程

**效果**: 原 `process_file_worker_with_queue` 中的 400+ 行重复 if-elif 块分解为清晰的工厂 + 策略，易于理解和维护。

### 阶段 4：配置与依赖注入（完成 ✓）
创建 [utils/sheet_processing.py](utils/sheet_processing.py) 中的 `PipelineSettings`：
- 集中所有运行时配置（路径、业务标识、性能参数、内存阈值、I/O 限流、调试）
- `from_config()` 类方法：从 config_manager 对象构建
- `get_database_path()` 方法：方便获取数据库路径

新增 [VAT_Invoice_Processor.py](VAT_Invoice_Processor.py) 中的 `build_pipeline_settings()`：
- 初始化 PipelineSettings 的中央工厂
- 自动路径解析（相对 → 绝对）
- 自动目录创建

**文档**: [DEPENDENCY_INJECTION_GUIDE.md](DEPENDENCY_INJECTION_GUIDE.md)
- PipelineSettings 用法和构建示例
- 全局变量 → settings 映射表
- worker 函数签名更新步骤
- 单元测试示例
- 后续优化方向

**效果**: 全局变量分散问题逐步集中化；依赖注入提高可测试性。

## 关键改进

| 方面 | 原来 | 现在 | 益处 |
|------|------|------|------|
| 代码规范 | 无 | STYLE.md | 新人可快速上手编码风格 |
| 文档 | 基础 README | ONBOARDING.md + 多个指南 | 清晰的学习路径和业务背景 |
| 类型检查 | 无 | ruff + mypy | 提前发现错误，改进代码质量 |
| 函数复杂度 | process_file_worker_with_queue ~500+ 行嵌套 | 使用工厂 + 策略模式，分解为 process_single_sheet | 圈复杂度下降，可读性提升 |
| 全局变量 | 10+ 个分散 (BUSINESS_TAG, INPUT_DIR, DEBUG_MODE, ...) | 1 个 PipelineSettings 对象 | 参数清晰，易于单测和扩展 |
| 配置初始化 | 分散在 VATAuditPipeline.load_config 中 | build_pipeline_settings() 中央工厂 | 配置流程集中，易于修改 |
| 依赖注入 | worker 直接读全局变量 | settings 通过参数注入 | 可测试性提高，减少副作用 |

## 待完成的工作

### 优先级 HIGH
1. **集成 PipelineSettings 到 VATAuditPipeline**
   - 在 `__init__` 中调用 `self.settings = build_pipeline_settings(config, BASE_DIR)`
   - 在 `pool.apply_async()` 调用时传入 `self.settings`
   - 用 `self.settings.xxx` 替代全局变量读取

2. **简化 process_file_worker_with_queue / process_file_worker**
   - 更新签名以接受 `settings: PipelineSettings` 参数
   - 用工厂 + 策略模式重写（参考 REFACTOR_PROGRESS.md 伪代码）
   - 从 ~500+ 行压缩到 ~80 行

3. **更新 multiprocessing 调用**
   - 使用 `functools.partial` 或修改 args 元组传递 settings

### 优先级 MEDIUM
4. **消除余下的全局变量**
   - 保留 logger, config 对象等必要的全局变量
   - 其他都转移到 settings 或本地变量

5. **单元测试**
   - 为新的纯函数编写单测（`normalize_sheet_dataframe`, `write_to_csv_or_queue`, `get_sheet_handler`）
   - 测试 PipelineSettings 的构建和验证
   - 用自定义 settings 参数测试 worker

### 优先级 LOW
6. **后续优化**
   - 为 worker args 创建 `WorkerArgs` 数据类以进一步简化签名
   - 为 PipelineSettings 添加 `validate()` 方法
   - 支持 settings 的序列化/反序列化用于日志审计

## 文件清单

### 新增
- [utils/sheet_processing.py](utils/sheet_processing.py): 策略模式 + 配置数据类
- [DEPENDENCY_INJECTION_GUIDE.md](DEPENDENCY_INJECTION_GUIDE.md): 依赖注入使用指南
- [STYLE.md](STYLE.md): 编码规范
- [ONBOARDING.md](ONBOARDING.md): 新人上手指南
- [DEPLOYMENT.md](DEPLOYMENT.md): 生产部署步骤
- [REFACTOR_PROGRESS.md](REFACTOR_PROGRESS.md): 重构细节和伪代码

### 修改
- [VAT_Invoice_Processor.py](VAT_Invoice_Processor.py):
  - 导入新的 PipelineSettings
  - 添加 build_pipeline_settings() 工厂
  - 添加 process_single_sheet() 辅助
  - 添加类型提示
  - 增强 docstring
- [config.yaml](config.yaml): 添加详细的配置注释
- [pyproject.toml](pyproject.toml): 新增 ruff + mypy 配置
- [requirements-dev.txt](requirements-dev.txt): 添加 ruff, mypy
- [README.md](README.md): 添加 lint 检查说明和部署链接

## 立即可采取的行动

### 对于维护者
1. 安装开发依赖：`pip install -r requirements-dev.txt`
2. 运行风格检查：`ruff check .`
3. 运行类型检查：`mypy VAT_Invoice_Processor.py config_manager.py utils`
4. 查看 DEPENDENCY_INJECTION_GUIDE.md 进行下一步集成

### 对于新人学习
1. 先读 [ONBOARDING.md](ONBOARDING.md)，了解业务背景和代码地图
2. 查看 [STYLE.md](STYLE.md)，理解编码规范
3. 在修改前运行 `ruff check` 和 `mypy` 确保风格一致
4. 参考 [DEPENDENCY_INJECTION_GUIDE.md](DEPENDENCY_INJECTION_GUIDE.md) 了解如何添加新配置字段

## 衡量成功的指标

- [ ] 类型检查通过（mypy）
- [ ] 风格检查通过（ruff）
- [ ] process_file_worker_with_queue 行数从 500+ 降至 <150
- [ ] 全局变量数从 10+ 降至 3-5
- [ ] 新增的 utils 函数都有独立单测
- [ ] PipelineSettings 集成到 VATAuditPipeline
- [ ] 新人能在 30 分钟内快速理解代码结构（ONBOARDING 可用性验证）

---

**状态**: 阶段 1-4 完成，阶段 5（集成）进行中。预计总耗时 8-10 小时（包括单元测试）。
