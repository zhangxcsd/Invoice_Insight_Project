# Python 编码规范（VAT_Audit_Project）

面向本仓库的轻量风格约定，覆盖命名、注释、日志、类型标注等。遵循 PEP 8 / PEP 257，保持简洁、可读、可维护。

## 命名与结构
- 模块与文件：`snake_case.py`；类：`CamelCase`；函数/变量：`snake_case`；常量：`UPPER_SNAKE_CASE`。
- 仅在有业务含义时使用缩写（如 VAT、ODS、DWD）；否则避免生造缩写。
- 一个文件聚焦一个主题；公共工具放入 `utils/`，主流程留在 `VAT_Invoice_Processor.py`。

## 类型标注与接口
- 公共函数/方法必须补全类型标注；返回 `None` 也要显式标注。
- 优先使用 `pathlib.Path` 表示路径，或在参数名中标注 `_path`/`dir` 表意。
- 容器使用泛型：`list[str]`、`dict[str, Any]`；避免裸 `list`/`dict`。

## Docstring 与注释
- 模块/类/函数使用 PEP 257 风格三引号，包含目的、关键业务背景、输入/输出/异常。
- 对新人友好：在复杂逻辑前给一行高信噪比注释，解释“为什么”（业务/性能原因），避免复述代码“做了什么”。
- 文档语言：对业务概念用中文阐述，可搭配少量英文关键词（如 WAL、chunk）。

## 日志与错误
- 使用模块级 `logger`，消息包含文件/表名/关键参数；INFO 记录业务进度，DEBUG 记录调试细节，WARNING/ERROR 记录异常。
- 不吞异常：捕获后写入结构化错误日志，并保留上下文（file, sheet, stage, error_type）。
- 用户可控：严禁打印敏感数据；路径和表名可打印，原始票据内容谨慎。

## 配置与常量
- 运行时配置全部来自 `config.yaml`（经 `config_manager` 验证），代码中不硬编码路径/阈值。
- 常量集中定义，便于查找；避免魔法数字散落。
- 优先通过配置开关控制实验特性（并行、DEBUG、流式读取等）。

## 导入与依赖
- 标准库 -> 第三方 -> 本地模块分组，组内按字母排序，空行分隔。
- 新增第三方依赖前，先写入 `requirements.txt` / `requirements-dev.txt` 并在 PR 说明理由。

## 测试与验证
- 单元测试放在 `tests/`，命名 `test_*.py`，可使用 pytest。
- 新逻辑至少提供冒烟测试或脚本示例；涉及 I/O 的函数可用临时目录/内存表隔离。

## 提交与文档
- 每次新增脚本或入口，更新 `README.md`/`DEPLOYMENT.md` 说明运行方法与输入输出。
- 变更公共接口或配置字段时，更新 `config.yaml` 注释与 `CONFIG_INTEGRATION_GUIDE.md`（如有）。

## 常见反模式（避免）
- 复杂一行链式操作；倾向小函数分解。
- 过度注释或重复注释（复述代码）；注释应解释意图或业务原因。
- 静默失败：`except Exception: pass` 需改为记录警告/错误。
