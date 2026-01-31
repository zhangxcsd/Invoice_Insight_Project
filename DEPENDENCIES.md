# 依赖包安装指南

## 更新日期
2026-01-04

## Python 版本要求
- **最低版本**: Python 3.8
- **推荐版本**: Python 3.10 或更高
- **测试版本**: Python 3.14

## 快速安装

### Windows (PowerShell)
```powershell
# 1. 切换到项目目录
cd D:\PythonCode\VAT_Audit_Project

# 2. 安装所有依赖
pip install -r requirements.txt

# 3. 验证安装
python -c "import pandas, numpy, openpyxl, chardet, psutil, tqdm; print('✅ 所有依赖包安装成功！')"
```

### Linux/macOS (Bash)
```bash
# 1. 切换到项目目录
cd /path/to/VAT_Audit_Project

# 2. 安装所有依赖
pip3 install -r requirements.txt

# 3. 验证安装
python3 -c "import pandas, numpy, openpyxl, chardet, psutil, tqdm; print('✅ 所有依赖包安装成功！')"
```

## 依赖包详细说明

### 1. 核心数据处理库

#### pandas (>= 2.0.0)
- **用途**: DataFrame 操作、数据清洗、CSV/Excel 读写
- **功能**:
  - 读取和写入 Excel 文件
  - 数据类型转换和标准化
  - 数据过滤和聚合
  - SQL 数据库交互
- **安装**: `pip install pandas>=2.0.0`
- **验证**: `python -c "import pandas; print(pandas.__version__)"`

#### numpy (>= 1.24.0)
- **用途**: 数值计算、数组操作
- **功能**:
  - pandas 的底层依赖
  - 数值数组运算
  - 数学函数支持
- **安装**: `pip install numpy>=1.24.0`
- **验证**: `python -c "import numpy; print(numpy.__version__)"`

### 2. Excel 文件处理

#### openpyxl (>= 3.0.0)
- **用途**: 读写 .xlsx 文件（Excel 2010 及更高版本）
- **功能**:
  - 读取 xlsx 工作簿和工作表
  - 支持样式和格式
  - 写入 Excel 文件
- **安装**: `pip install openpyxl>=3.0.0`
- **验证**: `python -c "import openpyxl; print(openpyxl.__version__)"`

#### xlrd (== 1.2.0)
- **用途**: 读取 .xls 文件（Excel 97-2003）
- **功能**:
  - 读取旧版 Excel 文件
  - 工作表数据提取
- **重要**: 必须使用 1.2.0 版本以支持 .xls 格式
- **安装**: `pip install xlrd==1.2.0`
- **验证**: `python -c "import xlrd; print(xlrd.__version__)"`
- **注意事项**:
  - xlrd 2.0+ 移除了 .xls 支持，必须使用 1.2.0
  - 如果已安装 2.0+，需要先卸载：`pip uninstall xlrd`，再安装 1.2.0

### 3. 编码检测与处理

#### chardet (>= 5.0.0)
- **用途**: 自动检测文件编码
- **功能**:
  - 识别文件编码（GB2312, GBK, UTF-8, UTF-16 等）
  - 处理中文编码问题
  - 确保数据正确读取
- **安装**: `pip install chardet>=5.0.0`
- **验证**: `python -c "import chardet; print(chardet.__version__)"`

### 4. 系统监控与性能优化

#### psutil (>= 5.9.0)
- **用途**: 系统资源监控、进程管理
- **功能**:
  - CPU 使用率监控
  - 内存使用监控
  - 磁盘 I/O 统计
  - 进程信息获取
  - 动态调整处理参数
- **安装**: `pip install psutil>=5.9.0`
- **验证**: `python -c "import psutil; print(psutil.__version__)"`

#### tqdm (>= 4.65.0)
- **用途**: 进度条显示
- **功能**:
  - 文件处理进度提示
  - 多进程进度追踪
  - 改善用户体验
- **安装**: `pip install tqdm>=4.65.0`
- **验证**: `python -c "import tqdm; print(tqdm.__version__)"`

### 5. Python 标准库（无需安装）

以下库为 Python 标准库，随 Python 安装自动包含：

| 库名 | 用途 |
|------|------|
| `sqlite3` | SQLite 数据库支持 |
| `logging` | 日志系统 |
| `multiprocessing` | 多进程并行处理 |
| `os` | 操作系统接口 |
| `sys` | 系统特定参数和函数 |
| `re` | 正则表达式 |
| `datetime` | 日期时间处理 |
| `json` | JSON 数据处理 |
| `uuid` | 唯一标识符生成 |
| `threading` | 线程支持 |
| `tempfile` | 临时文件管理 |
| `shutil` | 文件操作工具 |
| `glob` | 文件路径匹配 |
| `atexit` | 程序退出处理 |
| `dataclasses` | 数据类支持 |
| `typing` | 类型注解支持 |
| `collections` | 集合类型扩展 |
| `contextlib` | 上下文管理器工具 |
| `enum` | 枚举类型支持 |

## 常见问题与解决方案

### 问题 1: xlrd 版本冲突

**症状**: 
```
xlrd.biffh.XLRDError: Excel xlsx file; not supported
```

**原因**: xlrd 2.0+ 版本不支持 .xls 文件

**解决方案**:
```powershell
pip uninstall xlrd
pip install xlrd==1.2.0
```

### 问题 2: 缺少 tqdm 模块

**症状**:
```
ModuleNotFoundError: No module named 'tqdm'
```

**解决方案**:
```powershell
pip install tqdm>=4.65.0
```

### 问题 3: pandas 版本过低

**症状**:
```
AttributeError: module 'pandas' has no attribute 'XXX'
```

**解决方案**:
```powershell
pip install --upgrade pandas>=2.0.0
```

### 问题 4: 安装权限问题

**症状**:
```
PermissionError: [Errno 13] Permission denied
```

**解决方案**:
```powershell
# Windows: 使用管理员权限运行 PowerShell
# 或使用用户安装
pip install --user -r requirements.txt
```

### 问题 5: pip 版本过低

**症状**:
```
WARNING: You are using pip version XX.X.X; however, version YY.Y.Y is available.
```

**解决方案**:
```powershell
python -m pip install --upgrade pip
```

## 虚拟环境推荐

为避免依赖冲突，强烈建议使用虚拟环境：

### 使用 venv（推荐）

```powershell
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证安装
python -c "import pandas, numpy, openpyxl; print('环境配置成功！')"
```

### 使用 conda

```bash
# 1. 创建 conda 环境
conda create -n vat_audit python=3.10

# 2. 激活环境
conda activate vat_audit

# 3. 安装依赖
pip install -r requirements.txt
```

## 依赖包大小估算

| 包名 | 大小（约） | 下载时间（10Mbps） |
|------|-----------|-------------------|
| pandas | ~50 MB | ~40 秒 |
| numpy | ~30 MB | ~25 秒 |
| openpyxl | ~5 MB | ~4 秒 |
| xlrd | ~1 MB | ~1 秒 |
| chardet | ~2 MB | ~2 秒 |
| psutil | ~1 MB | ~1 秒 |
| tqdm | ~1 MB | ~1 秒 |
| **总计** | **~90 MB** | **~75 秒** |

## 离线安装

如果需要在无网络环境下安装：

```powershell
# 1. 在有网络的机器上下载依赖包
pip download -r requirements.txt -d packages/

# 2. 将 packages/ 目录复制到目标机器

# 3. 在目标机器上安装
pip install --no-index --find-links=packages/ -r requirements.txt
```

## 验证脚本

创建 `verify_dependencies.py` 验证所有依赖：

```python
import sys

def check_dependency(name, version_attr='__version__'):
    try:
        module = __import__(name)
        version = getattr(module, version_attr, 'unknown')
        print(f"✅ {name:15} {version}")
        return True
    except ImportError:
        print(f"❌ {name:15} 未安装")
        return False

print("="*50)
print("依赖包检查")
print("="*50)

dependencies = [
    'pandas',
    'numpy',
    'openpyxl',
    'xlrd',
    'chardet',
    'psutil',
    'tqdm',
]

results = [check_dependency(dep) for dep in dependencies]

print("="*50)
if all(results):
    print("✅ 所有依赖包已正确安装")
    sys.exit(0)
else:
    print("❌ 部分依赖包缺失，请运行: pip install -r requirements.txt")
    sys.exit(1)
```

运行验证：
```powershell
python verify_dependencies.py
```

## 更新依赖

定期更新依赖包以获取安全补丁和新功能：

```powershell
# 更新所有依赖到最新兼容版本
pip install --upgrade -r requirements.txt

# 查看可更新的包
pip list --outdated
```

## 技术支持

如果遇到依赖安装问题：
1. 查看本文档的"常见问题与解决方案"部分
2. 检查 Python 版本是否 >= 3.8
3. 确保 pip 已更新到最新版本
4. 查看项目 README.md 获取更多信息

## 版本历史

- **v1.1** (2026-01-04): 
  - 添加 numpy 到 requirements.txt
  - 添加 tqdm 依赖说明
  - 完善安装验证步骤
- **v1.0** (2026-01-03): 初始版本
