# 打包和分发指南 - 增值税发票审计系统 GUI 版

## 概述

本文档说明如何将 Python 程序打包成独立的 Windows 可执行文件（.exe），以便在没有安装 Python 环境的电脑上运行。

## 功能特点

✅ **图形化界面**

- 可视化参数配置
- 实时日志显示
- 进度条显示处理状态
- 友好的错误提示

✅ **无需 Python 环境**

- 打包成单一 .exe 文件
- 包含所有依赖
- 双击即可运行

✅ **完整功能**

- 支持所有命令行功能
- 并行处理配置
- 自动创建目录结构

---

## 快速开始

### 方法一：使用一键打包脚本（推荐）

```powershell
# 1. 打开 PowerShell，进入项目目录
cd d:\PythonCode\VAT_Audit_Project

# 2. 运行打包脚本
.\build_exe.ps1

# 3. 等待打包完成（首次约需 2-5 分钟）
# 完成后会在 Release/ 目录下生成发布包
```

**打包脚本选项：**

```powershell
.\build_exe.ps1           # 标准打包
.\build_exe.ps1 -Clean    # 清理后重新打包
.\build_exe.ps1 -Debug    # 调试模式（生成目录结构）
```

### 方法二：手动打包

```powershell
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 安装项目依赖
pip install -r requirements.txt

# 3. 执行打包
pyinstaller vat_gui.spec --clean --noconfirm

# 4. 打包完成后，可执行文件位于：
# dist\VAT_Invoice_Processor.exe
```

---

## 文件结构

### 开发目录结构

```
VAT_Audit_Project/
├── vat_gui.py              # GUI 主程序
├── vat_gui.spec            # PyInstaller 配置文件
├── build_exe.ps1           # 一键打包脚本
├── VAT_Invoice_Processor.py  # 原命令行入口（仍可用）
├── vat_audit_pipeline/     # 核心处理模块
├── config_default.yaml     # 默认配置文件
└── requirements.txt        # Python 依赖清单
```

### 发布包结构

```
Release/VAT_Audit_System_20260109_123456/
├── VAT_Invoice_Processor.exe  # 主程序（可执行文件）
├── config_default.yaml         # 配置文件模板
├── README.txt                  # 用户使用说明
├── Source_Data/                # 输入数据目录（空）
├── Outputs/                    # 输出结果目录（空）
└── Database/                   # 数据库目录（空）
```

---

## 使用指南

### 1. 运行 GUI 程序

**方式 A：打包后的 .exe**

```
双击 VAT_Invoice_Processor.exe
```

**方式 B：开发模式（需要 Python）**

```powershell
python vat_gui.py
```

### 2. 配置参数

在 GUI 界面中配置以下参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 输入目录 | 存放原始 Excel 数据文件 | `Source_Data/` |
| 输出目录 | 处理结果和报告输出位置 | `Outputs/` |
| 数据库目录 | SQLite 数据库文件存放位置 | `Database/` |
| 业务标签 | 用于表名前缀（可选） | 空 |
| 启用并行处理 | 多进程加速（推荐） | ✓ 启用 |
| 工作进程数 | 并行进程数量 | 4 |
| 详细日志 | DEBUG 级别日志 | ✗ 关闭 |

### 3. 开始处理

1. 点击 **"开始处理"** 按钮
2. 查看实时日志输出
3. 观察进度条进度
4. 等待处理完成
5. 点击 **"打开输出目录"** 查看结果

### 4. 查看日志

- **界面日志**：实时显示在 GUI 窗口下半部分
- **文件日志**：保存在 `Outputs/` 目录中
- **错误日志**：特殊错误会额外记录到 `error_logs/`

---

## PyInstaller 配置说明

### vat_gui.spec 文件

```python
# 关键配置项
datas = [
    ('config_default.yaml', '.'),  # 包含配置文件
]

hiddenimports = [
    'vat_audit_pipeline',          # 核心模块
    'pandas', 'numpy', 'openpyxl', # 数据处理库
    'tkinter',                      # GUI 库
    # ... 其他模块
]

# 单文件模式（默认）
exe = EXE(
    # ...
    name='VAT_Invoice_Processor',
    console=False,  # 不显示控制台窗口
    onefile=True,   # 单文件打包
)
```

### 打包模式选择

**单文件模式**（默认，推荐分发）

- ✓ 只生成一个 .exe 文件
- ✓ 方便分发和使用
- ✗ 启动稍慢（首次解压）
- ✗ 文件体积较大（~50-100 MB）

**目录模式**（适合调试）

- ✓ 启动速度快
- ✓ 便于调试
- ✗ 生成多个文件
- ✗ 需要整个文件夹一起分发

修改 `vat_gui.spec` 中的注释可以切换模式。

---

## 常见问题

### Q1: 打包后的 .exe 无法运行

**可能原因：**

1. 缺少依赖模块
2. 配置文件未包含
3. 路径问题

**解决方法：**

```powershell
# 1. 使用调试模式打包
.\build_exe.ps1 -Debug

# 2. 在命令行中运行，查看错误信息
.\dist\VAT_Invoice_Processor.exe

# 3. 检查 hiddenimports 是否包含所有模块
```

### Q2: 打包后文件太大

**减小体积的方法：**

1. 在 `vat_gui.spec` 中添加更多 `excludes`
2. 使用 UPX 压缩（已默认启用）
3. 考虑使用目录模式

```python
excludes=[
    'matplotlib', 'scipy', 'IPython',  # 排除不需要的大型库
    'notebook', 'jupyter', 'pytest',
]
```

### Q3: 打包时报错 "ModuleNotFoundError"

**解决方法：**

```powershell
# 1. 确保所有依赖已安装
pip install -r requirements.txt

# 2. 更新 PyInstaller
pip install --upgrade pyinstaller

# 3. 在 vat_gui.spec 的 hiddenimports 中添加缺失模块
```

### Q4: 界面显示异常或中文乱码

**解决方法：**

1. 确保系统区域设置为中文
2. 检查字体支持
3. 在代码中明确指定编码：

   ```python
   # vat_gui.py 开头添加
   # -*- coding: utf-8 -*-
   ```

### Q5: 运行时提示缺少配置文件

**解决方法：**

```powershell
# 确保 config_default.yaml 在以下位置之一：
# 1. 与 .exe 同目录
# 2. 项目根目录
# 3. 检查 vat_gui.spec 中的 datas 配置
```

---

## 性能优化

### 1. 减小启动时间

- 使用目录模式而非单文件模式
- 减少不必要的模块导入
- 优化 `hiddenimports` 列表

### 2. 减小文件体积

```python
# vat_gui.spec 中添加
excludes=[
    'matplotlib',  # ~50 MB
    'scipy',       # ~30 MB
    'IPython',     # ~20 MB
    'notebook',
    'jupyter',
]
```

### 3. 提高打包速度

```powershell
# 使用缓存（第二次打包更快）
pyinstaller vat_gui.spec

# 不清理缓存
pyinstaller vat_gui.spec --noconfirm
```

---

## 分发指南

### 1. 准备发布包

```powershell
# 使用自动脚本
.\build_exe.ps1

# 或手动创建
mkdir Release\VAT_Audit_System
copy dist\VAT_Invoice_Processor.exe Release\VAT_Audit_System\
copy config_default.yaml Release\VAT_Audit_System\
mkdir Release\VAT_Audit_System\Source_Data
mkdir Release\VAT_Audit_System\Outputs
mkdir Release\VAT_Audit_System\Database
```

### 2. 创建安装包（可选）

可以使用以下工具创建专业的安装程序：

- **Inno Setup**（免费，推荐）
- **NSIS**（免费）
- **InstallShield**（商业）

### 3. 用户交付清单

- [ ] VAT_Invoice_Processor.exe
- [ ] 配置文件模板
- [ ] 使用说明文档
- [ ] 示例数据（可选）
- [ ] 目录结构说明

---

## 技术细节

### GUI 框架选择：tkinter

**优点：**

- Python 标准库，无需额外依赖
- 跨平台支持
- 体积小，打包后增加不多
- 成熟稳定

**替代方案：**

- PyQt5/PySide6：更现代，但体积大（+100MB）
- wxPython：功能丰富，但依赖复杂
- Kivy：适合触摸屏，但学习曲线陡

### 日志系统

使用 `logging` 模块 + 自定义 `TextHandler`：

```python
class TextHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        self.queue.put(msg)  # 线程安全的队列
```

### 多线程处理

- **主线程**：GUI 界面和事件循环
- **工作线程**：数据处理任务
- **通信机制**：`queue.Queue`（线程安全）

---

## 开发者指南

### 修改 GUI 界面

编辑 `vat_gui.py`：

```python
def _create_widgets(self):
    # 添加新的控件
    ttk.Label(config_frame, text="新参数:").grid(...)
    self.new_var = tk.StringVar()
    ttk.Entry(config_frame, textvariable=self.new_var).grid(...)
```

### 添加新功能

```python
def _new_feature(self):
    """新功能的实现"""
    try:
        # 功能逻辑
        logging.info("执行新功能...")
        result = do_something()
        logging.info(f"完成：{result}")
    except Exception as e:
        logging.error(f"错误：{e}")
```

### 调试技巧

```powershell
# 1. 开发模式运行（看到完整错误信息）
python vat_gui.py

# 2. 打包时启用控制台（临时修改 vat_gui.spec）
exe = EXE(
    # ...
    console=True,  # 改为 True
)

# 3. 使用日志文件
# 在 vat_gui.py 中添加文件处理器
file_handler = logging.FileHandler('debug.log')
logging.root.addHandler(file_handler)
```

---

## 附录

### A. 依赖清单

参见 [requirements.txt](requirements.txt)

核心依赖：

- pandas >= 2.0.0
- openpyxl >= 3.0.0
- pyyaml >= 6.0.1
- pyinstaller >= 6.0.0（仅打包时需要）

### B. 相关文档

- [README.md](README.md) - 项目整体说明
- [QUICKSTART.md](QUICKSTART.md) - 快速入门指南
- [CONFIG_SUMMARY.md](CONFIG_SUMMARY.md) - 配置说明

### C. 版本历史

- **v1.0** (2026-01-09)
  - ✓ 初始 GUI 版本
  - ✓ 支持参数配置
  - ✓ 实时日志显示
  - ✓ 进度条支持
  - ✓ PyInstaller 打包

---

## 联系与支持

如有问题或建议，请：

1. 查看程序日志
2. 参考本文档的"常见问题"章节
3. 联系技术支持

---

**文档版本：** 1.0  
**更新日期：** 2026-01-09  
**适用版本：** VAT_Audit_Project v1.0.1
