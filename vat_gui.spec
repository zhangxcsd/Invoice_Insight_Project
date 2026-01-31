# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 - 增值税发票审计系统 GUI 版本

使用方法：
    pyinstaller vat_gui.spec

生成的文件位置：
    - 单文件模式: dist/VAT_Invoice_Processor.exe
    - 目录模式: dist/VAT_Invoice_Processor/VAT_Invoice_Processor.exe
"""

block_cipher = None

import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = Path.cwd()

# 需要包含的数据文件
datas = [
    # 配置文件
    (str(ROOT_DIR / 'config_default.yaml'), '.'),
    # 自定义配置
    (str(ROOT_DIR / 'config.yaml'), '.'),
    # 必要的工作目录
    (str(ROOT_DIR / 'Database'), 'Database'),
    (str(ROOT_DIR / 'Outputs'), 'Outputs'),
    (str(ROOT_DIR / 'Source_Data'), 'Source_Data'),
]

# 需要包含的隐藏导入（某些动态导入的模块）
hiddenimports = [
    'vat_audit_pipeline',
    'vat_audit_pipeline.config',
    'vat_audit_pipeline.config.settings',
    'vat_audit_pipeline.config.validators',
    'vat_audit_pipeline.core',
    'vat_audit_pipeline.core.pipeline',
    'vat_audit_pipeline.core.models',
    'vat_audit_pipeline.core.processors',
    'vat_audit_pipeline.core.processors.ods_processor',
    'vat_audit_pipeline.core.processors.dwd_processor',
    'vat_audit_pipeline.core.processors.ads_processor',
    'vat_audit_pipeline.dao',
    'vat_audit_pipeline.utils',
    'vat_audit_pipeline.utils.logging',
    'vat_audit_pipeline.utils.encoding',
    'vat_audit_pipeline.utils.normalization',
    'vat_audit_pipeline.utils.validators',
    'vat_audit_pipeline.utils.file_handlers',
    'vat_audit_pipeline.main',
    # 数据处理库
    'pandas',
    'numpy',
    'openpyxl',
    'xlrd',
    'chardet',
    'yaml',
    'psutil',
    'tqdm',
    'click',
    # tkinter 相关
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.filedialog',
    'tkinter.messagebox',
    # 标准库（明确列出以防遗漏）
    'sqlite3',
    'logging',
    'logging.handlers',
    'multiprocessing',
    'threading',
    'queue',
    'datetime',
    'json',
    'uuid',
    'tempfile',
    'shutil',
    'glob',
    'atexit',
]

# 分析入口文件
a = Analysis(
    ['vat_gui.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型包（减小体积）
        'matplotlib',
        'scipy',
        'IPython',
        'notebook',
        'jupyter',
        'pytest',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 收集所有文件
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ====== 选项 1: 单文件模式（推荐给最终用户） ======
# 优点：只有一个 .exe 文件，方便分发
# 缺点：启动稍慢（需要解压），体积较大
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VAT_Invoice_Processor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用 UPX 压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口（纯 GUI 模式）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'D:\PythonCode\VAT_Audit_Project\Release\icon.ico',
)

# ====== 选项 2: 目录模式（用于开发和调试） ======
# 取消下面的注释以使用目录模式
# 优点：启动快，便于调试
# 缺点：多个文件，需要整个文件夹一起分发
"""
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VAT_Invoice_Processor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'D:\PythonCode\VAT_Audit_Project\Release\icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VAT_Invoice_Processor',
)
"""
