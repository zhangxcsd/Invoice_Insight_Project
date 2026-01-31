"""增值税发票审计系统 - 图形用户界面

© 2025-2026 ToAudit数智工坊
版权所有，保留所有权利

提供友好的 GUI 界面，用于：
1. 配置程序参数（输入目录、输出目录、数据库目录等）
2. 启动/停止数据处理流程
3. 实时显示程序运行进度和日志信息
4. 查看处理结果和错误报告

依赖：tkinter（Python 标准库，无需额外安装）
"""

import os
import sys
import multiprocessing

# ============ 防止子进程导入 tkinter ============
# 当 multiprocessing 生成子进程时，它会重新运行整个模块，但仅在主进程中执行 if __name__ == '__main__'
# 此处设置 multiprocessing 模式为 'spawn'（Windows 上默认），并调用 freeze_support
if sys.platform == 'win32':
    # Windows 上 freeze_support 是必需的
    multiprocessing.freeze_support()

# 在模块导入时就设置环境变量，防止 multiprocessing 子进程导入时创建 GUI
if 'MPLBACKEND' not in os.environ:
    os.environ['MPLBACKEND'] = 'Agg'
if 'TQDM_DISABLE' not in os.environ:
    os.environ['TQDM_DISABLE'] = '1'
if 'QT_QPA_PLATFORM' not in os.environ:
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import ctypes
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import tkinter.font as tkfont
import threading
import queue
import logging
from pathlib import Path
from datetime import datetime
import traceback

# 启用详细调试日志
DEBUG_GUI = True

def _debug_log(msg: str):
    """调试日志输出"""
    if DEBUG_GUI:
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[GUI-DEBUG {timestamp}] {msg}", flush=True)
        logging.debug(f"[GUI] {msg}")


class TextHandler(logging.Handler):
    """自定义日志处理器，将日志输出到 GUI 文本框"""
    
    def __init__(self, text_widget, queue_obj):
        super().__init__()
        self.text_widget = text_widget
        self.queue = queue_obj
        
    def emit(self, record):
        """发送日志记录到队列"""
        try:
            msg = self.format(record)
            self.queue.put(msg)
        except Exception:
            self.handleError(record)


class VATAuditGUI:
    """增值税发票审计系统 GUI 主窗口"""
    
    def __init__(self, root):
        _debug_log(f"VATAuditGUI.__init__ 开始, root={root}")
        self.root = root
        self.root.title("增值税发票审计系统 v1.0.1")
        self.root.geometry("1000x700")
        _debug_log("窗口标题和尺寸已设置")
        
        # 设置窗口图标（如果存在）
        try:
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass
        
        # 初始化变量
        self.processing = False
        self.log_queue = queue.Queue()
        
        # 默认路径
        self.default_paths = {
            'input_dir': str(Path.cwd() / "Source_Data"),
            'output_dir': str(Path.cwd() / "Outputs"),
            'database_dir': str(Path.cwd() / "Database"),
        }
        
        # 创建菜单栏
        self._create_menubar()
        
        # 创建 GUI 组件
        self._create_widgets()
        self._setup_logging()
        
        # 启动日志更新循环
        self.root.after(100, self._update_log_display)
        
        # 窗口关闭时的清理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _create_menubar(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        help_menu.add_command(label="工作进程数说明", command=self._show_worker_count_help)
        help_menu.add_command(label="业务标签使用指南", command=self._show_business_tag_help)
        help_menu.add_command(label="并行处理配置", command=self._show_parallel_config_help)
        help_menu.add_separator()
        help_menu.add_command(label="关于本程序", command=self._show_about)
    
    def _show_worker_count_help(self):
        """显示工作进程数帮助"""
        help_text = """
【工作进程数（Worker Count）说明】

工作进程数控制并行导入时同时处理多少个 Excel 文件。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 快速参考：

worker=1（串行处理）
  • CPU: 单核 (~30-50%)
  • 内存: 最低 (200-300 MB)
  • 速度: 最慢
  • 日志: 清晰有序 ✓
  • 场景: 调试、资源紧张的机器

worker=4（均衡配置，推荐）
  • CPU: 4核 (~80-120%)
  • 内存: 中等 (600-900 MB)
  • 速度: 适中 (4倍加速)
  • 日志: 略有交错
  • 场景: 生产环境标准配置

worker=8（高并发）
  • CPU: 8核 (~150-200%)
  • 内存: 较高 (1.2-1.8 GB)
  • 速度: 最快 (但收益递减)
  • 日志: 混乱不堪
  • 场景: 高性能硬件 + 大批量文件

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 选择建议：

  • 2核 CPU + 机械硬盘   → worker=1
  • 4-8核 CPU + SSD      → worker=4（推荐）
  • 8+ 核 CPU + NVMe     → worker=8

通用公式：worker_count = CPU核心数 - 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 自适应机制：

系统会自动监控磁盘繁忙度，当≥75%时自动降级：
  例：设置 worker=8，磁盘繁忙 85%
  → 自动调整为 worker=4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
详细文档请查看 README.md 中的
"工作进程数（Worker Count）配置指南"章节

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 版权与联系：31918424@qq.com
        """
        messagebox.showinfo("工作进程数说明", help_text)
    
    def _show_business_tag_help(self):
        """显示业务标签帮助"""
        help_text = """
【业务标签（Business Tag）使用指南】

业务标签为数据库、表和临时文件添加前缀，
支持多个业务单位共享一套系统且彼此隔离数据。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 应用场景：

  1. 多个分子公司/分支机构共用一套系统
  2. 按年度隔离发票审计数据
  3. 便于数据备份、迁移与合并

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 工作原理（标签会影响以下位置）：

  1. 数据库文件名
     无标签: Database/VAT_INV_Audit_Repo.db
     有标签: Database/ACME_2026_Audit_Repo.db

  2. 表名前缀
     无标签: ODS_VAT_INV_2024_HEADER
     有标签: ODS_ACME_2026_2024_HEADER

  3. 临时文件夹
     Outputs/tmp_imports_<TAG>_<timestamp>/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ 三种设置方式：

  方式1【推荐】：在本 GUI 中直接输入
    • 在"业务标签"输入框中填写
    • 例如：ACME_2026、BRANCH_SH 等

  方式2：编辑配置文件 config.yaml
    business:
      tag: "ACME_2026"

  方式3：环境变量（仅限 Python 直接运行）
    $env:VAT_BUSINESS_TAG="ACME_2026"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 约束与注意：

  • 只能包含字母、数字和下划线
  • 不同标签生成完全独立的数据库
  • 无法通过变更标签"追溯"历史数据
  • 若要合并数据，需自行编写 SQL 脚本

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
详细文档请查看 README.md 中的
"业务标签（Business Tag）"章节

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 版权与联系：31918424@qq.com
        """
        messagebox.showinfo("业务标签使用指南", help_text)
    
    def _show_parallel_config_help(self):
        """显示并行处理配置帮助"""
        help_text = """
【并行处理配置说明】

系统支持多种方式控制并行导入的行为。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎛️ 主要配置项：

1. 【启用并行处理】（复选框）
   • 勾选：使用多进程并行导入（推荐）
   • 不勾选：串行处理（调试用）

2. 【工作进程数】（数字输入框）
   • 默认值：4
   • 范围：1-16（可修改）
   • 见"工作进程数说明"菜单了解详情

3. 【详细日志】（复选框）
   • 勾选：启用 DEBUG 级别日志
   • 内容丰富但可能较多，不勾选时仅显示 INFO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 配置文件（config.yaml）中的高级参数：

  runtime:
    enable_parallel_import: true
    worker_count: 4

  performance:
    io_throttle:
      enabled: true
      busy_threshold_percent: 75
      reduce_factor: 0.5
      min_workers: 1

    memory_monitoring:
      enabled: true
      memory_threshold_percent: 80
      stream_switch_threshold_percent: 75

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 常见配置组合：

  【调试模式】
    • 启用并行处理：否
    • 工作进程数：1
    • 详细日志：是
    → 清晰的日志，便于排查问题

  【生产环境】
    • 启用并行处理：是
    • 工作进程数：4
    • 详细日志：否
    → 均衡的性能和资源消耗

  【大批量处理】
    • 启用并行处理：是
    • 工作进程数：8（根据 CPU 调整）
    • 详细日志：否
    → 最大性能，但内存占用较高

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
详细文档请查看：
  • README.md - 完整配置说明
  • config.yaml 文件注释 - 参数说明

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 版权与联系：31918424@qq.com
        """
        messagebox.showinfo("并行处理配置", help_text)
    
    def _show_about(self):
        """显示关于对话框"""
        about_text = """
增值税发票审计系统
VAT Invoice Audit Pipeline v1.0.1

📊 功能说明：
  • 从 Excel 文件自动导入增值税发票数据
  • 支持多表工作表自动分类和识别
  • 按年度构建标准化数据仓库
  • 检测异常税率并生成审计报告
  • 支持多分公司/多年度数据隔离

🔧 主要特性：
  • 高效的并行导入（多进程加速）
  • 自动编码检测（支持 GBK/UTF-8 等）
  • 内存监控和流式处理（防止 OOM）
  • 完整的错误追踪和日志记录
  • 灵活的业务标签隔离机制

📚 文档和帮助：
  • 使用"帮助"菜单了解各项功能
  • 查看 README.md 获取详细文档
  • 查看 config.yaml 了解配置参数

⚙️ 系统要求：
  • Python 3.8 或更高版本
  • pandas, openpyxl, chardet 等依赖

📧 问题反馈：
  • 查看 Outputs/vat_audit.log 诊断问题
  • 启用"详细日志"获取更多调试信息

📧 版权与联系：31918424@qq.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© 2025-2026 ToAudit数智工坊
        """
        messagebox.showinfo("关于本程序", about_text)
    
    def _create_widgets(self):
        """创建所有 GUI 组件"""
        
        # 主容器 - 使用 PanedWindow 分割上下区域
        main_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ========== 上半部分：参数配置区域 ==========
        config_frame = ttk.LabelFrame(main_paned, text="配置参数", padding=10)
        main_paned.add(config_frame, weight=1)
        
        # 输入目录
        ttk.Label(config_frame, text="输入目录（Source_Data）:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_dir_var = tk.StringVar(value=self.default_paths['input_dir'])
        ttk.Entry(config_frame, textvariable=self.input_dir_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(config_frame, text="浏览...", command=lambda: self._browse_directory(self.input_dir_var)).grid(row=0, column=2)
        
        # 输出目录
        ttk.Label(config_frame, text="输出目录（Outputs）:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value=self.default_paths['output_dir'])
        ttk.Entry(config_frame, textvariable=self.output_dir_var, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(config_frame, text="浏览...", command=lambda: self._browse_directory(self.output_dir_var)).grid(row=1, column=2)
        
        # 数据库目录
        ttk.Label(config_frame, text="数据库目录（Database）:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.database_dir_var = tk.StringVar(value=self.default_paths['database_dir'])
        ttk.Entry(config_frame, textvariable=self.database_dir_var, width=60).grid(row=2, column=1, padx=5)
        ttk.Button(config_frame, text="浏览...", command=lambda: self._browse_directory(self.database_dir_var)).grid(row=2, column=2)
        
        # 业务标签
        ttk.Label(config_frame, text="业务标签（可选）:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.business_tag_var = tk.StringVar(value="")
        ttk.Entry(config_frame, textvariable=self.business_tag_var, width=30).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # 高级选项框架
        advanced_frame = ttk.LabelFrame(config_frame, text="高级选项", padding=5)
        advanced_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # 并行处理
        self.parallel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="启用并行处理", variable=self.parallel_var).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # 工作进程数
        ttk.Label(advanced_frame, text="工作进程数:").grid(row=0, column=1, padx=(20, 5))
        self.worker_count_var = tk.IntVar(value=4)
        ttk.Spinbox(advanced_frame, from_=1, to=16, textvariable=self.worker_count_var, width=10).grid(row=0, column=2)
        
        # 详细日志
        self.verbose_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="详细日志（DEBUG 级别）", variable=self.verbose_var).grid(row=0, column=3, padx=(20, 5))
        
        # 按钮区域
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="▶ 开始处理", command=self._start_processing, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹ 停止", command=self._stop_processing, width=15, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="清空日志", command=self._clear_log, width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="打开输出目录", command=self._open_output_dir, width=15).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(config_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(config_frame, textvariable=self.status_var, foreground="blue")
        status_label.grid(row=7, column=0, columnspan=3, sticky=tk.W)
        
        # ========== 下半部分：日志显示区域 ==========
        log_frame = ttk.LabelFrame(main_paned, text="运行日志", padding=5)
        main_paned.add(log_frame, weight=2)
        
        # 创建滚动文本框（使用更适合中文显示的字体）
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, font=("Microsoft YaHei UI", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志颜色标签
        self.log_text.tag_config('ERROR', foreground='red')
        self.log_text.tag_config('WARNING', foreground='orange')
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('DEBUG', foreground='gray')
        self.log_text.tag_config('SUCCESS', foreground='green', font=('Consolas', 9, 'bold'))
        
    def _browse_directory(self, var):
        """浏览并选择目录"""
        directory = filedialog.askdirectory(initialdir=var.get(), parent=self.root)
        if directory:
            var.set(directory)
            
    def _setup_logging(self):
        """配置日志系统"""
        # 获取根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 添加 GUI 处理器
        gui_handler = TextHandler(self.log_text, self.log_queue)
        gui_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
        gui_handler.setFormatter(formatter)
        root_logger.addHandler(gui_handler)
        
        # 添加文件日志处理器
        try:
            log_file = Path.cwd() / f"VAT_GUI_Debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            _debug_log(f"日志文件已创建: {log_file}")
        except Exception as e:
            _debug_log(f"创建日志文件失败: {e}")
        
        # 初始欢迎消息
        logging.info("=" * 60)
        logging.info("增值税发票审计系统已就绪")
        logging.info("=" * 60)
        
    def _update_log_display(self):
        """定期从队列中获取日志并显示"""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        finally:
            # 每 100ms 检查一次
            self.root.after(100, self._update_log_display)
            
    def _append_log(self, msg):
        """添加日志到文本框"""
        # 确定日志级别并应用颜色
        tag = 'INFO'
        if '[ERROR]' in msg or 'ERROR' in msg:
            tag = 'ERROR'
        elif '[WARNING]' in msg or 'WARNING' in msg:
            tag = 'WARNING'
        elif '[DEBUG]' in msg:
            tag = 'DEBUG'
        elif '成功' in msg or '完成' in msg or 'SUCCESS' in msg:
            tag = 'SUCCESS'
            
        self.log_text.insert(tk.END, msg + '\n', tag)
        self.log_text.see(tk.END)  # 自动滚动到底部
        
    def _set_status(self, text: str):
        """线程安全地更新状态文本"""
        try:
            self.root.after(0, lambda: self.status_var.set(text))
        except Exception:
            # 回退：直接设置（仅在主线程）
            self.status_var.set(text)
        
    def _set_progress(self, value: float):
        """线程安全地更新进度"""
        try:
            self.root.after(0, lambda: self.progress_var.set(value))
        except Exception:
            self.progress_var.set(value)
        
    def _restore_ui_state_on_finish(self):
        """线程安全地恢复按钮和状态"""
        def _do_restore():
            self.processing = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.status_var.get() == "正在处理...":
                self.status_var.set("就绪")
        try:
            self.root.after(0, _do_restore)
        except Exception:
            _do_restore()
        
    def _clear_log(self):
        """清空日志显示"""
        self.log_text.delete(1.0, tk.END)
        logging.info("日志已清空")
        
    def _open_output_dir(self):
        """打开输出目录"""
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            os.startfile(output_dir)
        else:
            _debug_log("准备显示 messagebox.showwarning")
            messagebox.showwarning("目录不存在", f"输出目录不存在：\n{output_dir}", parent=self.root)
            _debug_log("messagebox.showwarning 已关闭")
            
    def _validate_inputs(self):
        """验证输入参数"""
        input_dir = self.input_dir_var.get()
        
        if not input_dir:
            messagebox.showerror("输入错误", "请指定输入目录！", parent=self.root)
            return False
            
        if not os.path.exists(input_dir):
            result = messagebox.askyesno("目录不存在", 
                                        f"输入目录不存在：\n{input_dir}\n\n是否创建该目录？", parent=self.root)
            if result:
                os.makedirs(input_dir, exist_ok=True)
            else:
                return False
                
        # 创建输出和数据库目录（如果不存在）
        for dir_var in [self.output_dir_var, self.database_dir_var]:
            dir_path = dir_var.get()
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                
        return True
        
    def _start_processing(self):
        """开始处理流程"""
        if not self._validate_inputs():
            return
            
        # 更新 UI 状态
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("正在处理...")
        self.progress_var.set(0)
        
        # 在新线程中运行处理流程
        thread = threading.Thread(target=self._run_processing, daemon=True)
        thread.start()
        
    def _run_processing(self):
        """实际的处理流程（在后台线程中运行）"""
        _debug_log(f"_run_processing 启动, 线程={threading.current_thread().name}")
        try:
            logging.info("=" * 60)
            logging.info("开始处理发票数据...")
            logging.info("=" * 60)
            _debug_log("准备导入 pipeline 模块")
            
            # 设置多进程启动方法（Windows 必须用 spawn 避免重新导入问题）
            import multiprocessing
            try:
                multiprocessing.set_start_method('spawn', force=True)
                _debug_log("multiprocessing 启动方法设置为 spawn")
            except RuntimeError:
                _debug_log("multiprocessing 启动方法已设置")
            
            # 在调用流水线前，设置环境覆盖（由Pipeline读取）
            os.environ["VAT_INPUT_DIR"] = self.input_dir_var.get()
            os.environ["VAT_OUTPUT_DIR"] = self.output_dir_var.get()
            os.environ["VAT_DATABASE_DIR"] = self.database_dir_var.get()
            if self.business_tag_var.get():
                os.environ["VAT_BUSINESS_TAG"] = self.business_tag_var.get()
            _debug_log(f"环境覆盖: INPUT={os.environ.get('VAT_INPUT_DIR')}, OUTPUT={os.environ.get('VAT_OUTPUT_DIR')}, DB={os.environ.get('VAT_DATABASE_DIR')}, TAG={os.environ.get('VAT_BUSINESS_TAG')}")

            _debug_log("导入 pipeline 模块")
            # 导入处理模块
            from vat_audit_pipeline.main import main as pipeline_main
            _debug_log("pipeline 模块导入完成")
            
            # 命令行参数对当前 main() 不生效，保留日志用途
            args = [
                '--input', self.input_dir_var.get(),
                '--output', self.output_dir_var.get(),
                '--database', self.database_dir_var.get(),
            ]
            
            if self.business_tag_var.get():
                args.extend(['--business-tag', self.business_tag_var.get()])
                
            if self.parallel_var.get():
                args.append('--parallel')
                args.extend(['--workers', str(self.worker_count_var.get())])
            else:
                args.append('--no-parallel')
                
            if self.verbose_var.get():
                args.append('--verbose')
                
            # 更新进度（模拟）
            self._set_progress(10)
            
            # 保存原始 sys.argv
            original_argv = sys.argv.copy()
            
            try:
                # 修改 sys.argv 以传递参数
                sys.argv = ['vat_gui.py'] + args
                _debug_log(f"准备执行 pipeline_main, argv={sys.argv}")
                
                # 执行主流程
                pipeline_main()
                _debug_log("pipeline_main 执行完成")
                
                # 处理成功
                self._set_progress(100)
                self._set_status("处理完成！")
                logging.info("=" * 60)
                logging.info("✓ 所有数据处理完成！")
                logging.info("✓ 请查看输出目录中的结果。")
                logging.info("=" * 60)
                
            finally:
                # 恢复 sys.argv
                sys.argv = original_argv
                
        except Exception as e:
            _debug_log(f"捕获异常: {type(e).__name__}: {e}")
            self._set_progress(0)
            self._set_status("处理失败")
            logging.error(f"处理过程中发生错误：{e}")
            logging.debug(traceback.format_exc())
            _debug_log("异常处理完成")
            
        finally:
            _debug_log("_run_processing finally 块")
            # 恢复 UI 状态（线程安全）
            self._restore_ui_state_on_finish()
            _debug_log("_run_processing 完全结束")
                
    def _stop_processing(self):
        """停止处理流程"""
        if messagebox.askyesno("确认停止", "确定要停止当前处理吗？\n\n注意：停止后可能导致数据不完整。", parent=self.root):
            self.processing = False
            self.status_var.set("用户已停止")
            logging.warning("用户请求停止处理")
            # 注意：实际停止需要在 pipeline 中实现信号处理
            
    def _on_closing(self):
        """窗口关闭时的处理"""
        if self.processing:
            if messagebox.askokcancel("退出确认", "程序正在处理数据，确定要退出吗？", parent=self.root):
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """GUI 程序入口"""
    # 双重保险：如果 somehow 到达这里但不是主进程，立即返回
    if multiprocessing.current_process().name != 'MainProcess':
        return
    
    # 在最开始就设置环境变量，防止子进程/模块导入时创建 GUI
    os.environ['MPLBACKEND'] = 'Agg'  # 禁用 matplotlib GUI
    os.environ['TQDM_DISABLE'] = '1'  # 完全禁用 tqdm
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # 减少文件 I/O
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # 禁用 Qt GUI
    
    # 设置日志文件
    log_file = Path.cwd() / f"VAT_GUI_Debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    _debug_log("=" * 60)
    _debug_log(f"GUI main() 启动 - 进程: {multiprocessing.current_process().name}")
    _debug_log(f"日志文件: {log_file}")
    _debug_log(f"当前 Tk._default_root = {getattr(tk, '_default_root', None)}")
    
    try:
        # 启用 Windows 高 DPI 感知，保证字体清晰
        _debug_log("设置 DPI 感知")
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            _debug_log("SetProcessDpiAwareness(2) 成功")
        except Exception as e:
            _debug_log(f"SetProcessDpiAwareness 失败: {e}")
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                _debug_log("SetProcessDPIAware() 成功")
            except Exception as e2:
                _debug_log(f"SetProcessDPIAware 失败: {e2}")

        # 创建主窗口
        _debug_log("准备创建 tk.Tk() 实例")
        root = tk.Tk()
        _debug_log(f"tk.Tk() 创建完成, id={id(root)}, title={root.title()}")

        # 设置默认根，避免隐式创建额外 Tk 窗体
        _debug_log("设置 tk._default_root")
        try:
            tk._default_root = root
            _debug_log(f"tk._default_root 已设置为 {id(root)}")
        except Exception as e:
            _debug_log(f"设置 _default_root 失败: {e}")

        # 应用更适合中文显示的默认字体
        try:
            preferred = "Microsoft YaHei UI"
            families = set(tkfont.families(root))
            family = preferred if preferred in families else "Segoe UI"
            for name in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont"):
                f = tkfont.nametofont(name)
                f.configure(family=family, size=10)
        except Exception:
            pass
        
        # 设置主题（尝试使用现代主题）
        try:
            style = ttk.Style()
            available_themes = style.theme_names()
            if 'vista' in available_themes:
                style.theme_use('vista')
            elif 'clam' in available_themes:
                style.theme_use('clam')
        except:
            pass
            
        # 创建应用实例
        _debug_log("创建 VATAuditGUI 实例")
        app = VATAuditGUI(root)
        _debug_log("VATAuditGUI 实例创建完成")
        
        # 运行主循环
        _debug_log("启动 mainloop")
        root.mainloop()
        _debug_log("mainloop 已退出")
        
    except Exception as e:
        # 使用原生 Windows MessageBox，避免隐式 Tk 窗体
        try:
            msg = f"GUI 启动失败：\n{str(e)}\n\n{traceback.format_exc()}"
            ctypes.windll.user32.MessageBoxW(0, msg, "启动失败", 0x00000010)
        except Exception:
            print("GUI 启动失败:", e)
            print(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    # 只有主进程在运行此脚本时才会执行这个块
    # 子进程通过 multiprocessing.spawn 会重新运行脚本，但不会进入此块
    
    import os
    from datetime import datetime
    
    # 记录进程信息用于调试
    current_process = multiprocessing.current_process()
    log_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    trace_log = os.path.join(log_dir, f"process_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    try:
        with open(trace_log, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            f.write(f"[{timestamp}] 主进程启动: {current_process.name} (PID: {os.getpid()})\n")
            f.flush()
    except:
        pass
    
    # 启动 GUI
    main()
