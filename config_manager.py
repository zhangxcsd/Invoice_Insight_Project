"""
配置管理模块
负责加载和管理 config.yaml 配置文件
"""
import os
import sys
import yaml
import multiprocessing
from pathlib import Path
from copy import deepcopy


def _get_base_dir() -> Path:
    """Resolve base directory; frozen builds use the .exe location."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).parent


class Config:
    """配置管理类 - 单例模式"""
    _instance = None
    _config_data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config_data is None:
            self.load_config()
    
    def load_config(self, config_path=None, default_path=None, overrides: dict | None = None):
        """加载配置文件，支持与默认配置深度合并，并执行严格校验。

        overrides: 可选的覆盖字典（与默认/用户配置深度合并），用于 CLI 场景。
        """
        base_dir = _get_base_dir()

        if config_path:
            config_path = Path(config_path)
            if not config_path.is_absolute():
                config_path = base_dir / config_path
        else:
            config_path = base_dir / "config.yaml"

        if default_path:
            default_path = Path(default_path)
            if not default_path.is_absolute():
                default_path = base_dir / default_path
        else:
            default_path = base_dir / "config_default.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        default_data = self._load_yaml(default_path) if default_path.exists() else {}
        user_data = self._load_yaml(config_path)

        merged = self._deep_merge(default_data, user_data)
        if overrides:
            merged = self._deep_merge(merged, overrides)
        self._config_data = merged

        # 处理特殊配置值
        self._process_config()
        # 验证必需的配置项与数值合法性
        self._validate_config(base_dir)
    
    def _validate_config(self, base_dir: Path):
        """验证配置完整性与数值合法性，快速失败。"""
        required_sections = ['business', 'paths', 'parallel', 'performance', 'data_processing']
        for section in required_sections:
            if section not in self._config_data:
                raise ValueError(f"配置文件缺少必需部分: {section}")

        # worker_count 必须为正整数
        wc = self._config_data['parallel'].get('worker_count')
        if not isinstance(wc, int) or wc < 1:
            raise ValueError(f"parallel.worker_count 非法值: {wc}，必须为 >=1 的整数 (或在配置中使用 'auto')")

        # 目录必须存在
        for key in ['input_dir', 'database_dir', 'output_dir']:
            raw_path = self._config_data['paths'].get(key)
            if not raw_path:
                raise ValueError(f"paths.{key} 未配置")
            abs_path = self._resolve_dir(raw_path, base_dir)
            if not abs_path.exists() or not abs_path.is_dir():
                raise ValueError(f"paths.{key} 路径不存在或不是目录: {abs_path}")

        # 数值项必须为正
        for name in ['csv_chunk_size', 'stream_chunk_size']:
            v = self._config_data['performance'].get(name)
            if not isinstance(v, int) or v <= 0:
                raise ValueError(f"performance.{name} 非法值: {v}，必须为正整数")

        mmp = self._config_data.get('performance', {}).get('memory_monitoring', {}) or {}
        for num_key in ['memory_threshold_percent', 'stream_switch_threshold_percent']:
            v = mmp.get(num_key)
            if v is not None and (not isinstance(v, (int, float)) or v <= 0):
                raise ValueError(f"performance.memory_monitoring.{num_key} 非法值: {v}，必须为正数")

    def _resolve_dir(self, path_value, base_dir: Path) -> Path:
        p = Path(path_value)
        if not p.is_absolute():
            p = base_dir / p
        return p.resolve()

    def _load_yaml(self, path: Path):
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return data
    
    def _process_config(self):
        """处理特殊配置值"""
        # 处理worker_count的"auto"值
        if self._config_data['parallel']['worker_count'] == 'auto':
            self._config_data['parallel']['worker_count'] = max(1, multiprocessing.cpu_count() - 1)

    def _deep_merge(self, base: dict, override: dict):
        """递归合并字典，override 覆盖 base，保持互不污染。"""

        result = deepcopy(base)
        for k, v in (override or {}).items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = deepcopy(v)
        return result
    
    def get(self, *keys, default=None):
        """获取配置值，支持多级键访问
        
        例如: config.get('parallel', 'enabled')
        """
        value = self._config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    # ===== 便捷访问属性 =====
    
    @property
    def business_tag(self):
        return self.get('business', 'tag', default='VAT_INV')
    
    @property
    def input_dir(self):
        return self.get('paths', 'input_dir', default='Source_Data')
    
    @property
    def database_dir(self):
        return self.get('paths', 'database_dir', default='Database')
    
    @property
    def output_dir(self):
        return self.get('paths', 'output_dir', default='Outputs')
    
    @property
    def parallel_enabled(self):
        return self.get('parallel', 'enabled', default=True)
    
    @property
    def worker_count(self):
        return self.get('parallel', 'worker_count', default=max(1, multiprocessing.cpu_count() - 1))
    
    @property
    def dynamic_worker_adjustment(self):
        return self.get('parallel', 'dynamic_worker_adjustment', default=True)
    
    @property
    def csv_chunk_size(self):
        return self.get('performance', 'csv_chunk_size', default=10000)
    
    @property
    def stream_chunk_size(self):
        return self.get('performance', 'stream_chunk_size', default=50000)
    
    @property
    def stream_chunk_dynamic(self):
        return self.get('performance', 'stream_chunk_dynamic', default=True)
    
    @property
    def max_failure_samples(self):
        return self.get('data_processing', 'max_failure_samples', default=100)
    
    @property
    def tax_text_to_zero(self):
        return self.get('data_processing', 'tax_text_to_zero', default=True)
    
    @property
    def filter_empty_rows(self):
        return self.get('data_processing', 'filter_empty_rows', default=True)
    
    @property
    def filter_nan_rows(self):
        return self.get('data_processing', 'filter_nan_rows', default=True)
    
    @property
    def log_level(self):
        return self.get('logging', 'log_level', default='INFO')
    
    @property
    def log_to_file(self):
        return self.get('logging', 'log_to_file', default=True)
    
    @property
    def log_file(self):
        return self.get('logging', 'log_file', default='vat_audit.log')
    
    @property
    def log_max_bytes(self):
        return self.get('logging', 'max_bytes', default=10485760)
    
    @property
    def log_backup_count(self):
        return self.get('logging', 'backup_count', default=5)
    
    @property
    def debug_enabled(self):
        return self.get('logging', 'debug_enabled', default=False)
    
    @property
    def queue_mode_enabled(self):
        return self.get('performance', 'queue_mode', 'enabled', default=True)
    
    @property
    def queue_min_memory_mb(self):
        return self.get('performance', 'queue_mode', 'min_memory_mb', default=2000)
    
    @property
    def batch_method(self):
        return self.get('database', 'batch_operations', 'method', default='multi')
    
    @property
    def batch_chunksize(self):
        return self.get('database', 'batch_operations', 'chunksize', default=500)
    
    @property
    def date_columns(self):
        return self.get('column_mapping', 'date_columns', default=['开票日期'])
    
    @property
    def numeric_columns(self):
        return self.get('column_mapping', 'numeric_columns', default=['金额', '税额', '单价', '数量', '价税合计'])
    
    @property
    def tax_rate_columns(self):
        return self.get('column_mapping', 'tax_rate_columns', default=['税率'])
    
    @property
    def tax_text_tokens(self):
        return self.get('column_mapping', 'tax_text_tokens', default=['免税', '不征税', '免征'])
    
    @property
    def detail_patterns(self):
        return self.get('sheet_classification', 'detail_patterns', default=['发票基础信息'])
    
    @property
    def header_patterns(self):
        return self.get('sheet_classification', 'header_patterns', default=['信息汇总表'])
    
    @property
    def special_sheets(self):
        return self.get('sheet_classification', 'special_sheets', default={})
    
    @property
    def file_size_thresholds(self):
        return self.get('parallel', 'file_size_thresholds', default={'small': 10, 'medium': 50, 'large': 200})
    
    def reload(self, config_path=None):
        """重新加载配置文件"""
        self._config_data = None
        self.load_config(config_path)


# 全局配置实例
_config_instance = None

def get_config():
    """获取全局配置实例。

    兼容旧调用：get_config()。
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def get_config_with_overrides(config_path=None, overrides: dict | None = None) -> Config:
    """获取配置实例并应用指定配置路径与覆盖项。"""

    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    if config_path or overrides:
        _config_instance.load_config(config_path=config_path, overrides=overrides)
    return _config_instance


# 便捷函数
def reload_config(config_path=None):
    """重新加载配置"""
    global _config_instance
    _config_instance = None
    _config_instance = Config()
    if config_path:
        _config_instance.load_config(config_path)


if __name__ == '__main__':
    # 测试配置加载
    config = get_config()
    print(f"业务标识: {config.business_tag}")
    print(f"工作进程数: {config.worker_count}")
    print(f"CSV块大小: {config.csv_chunk_size}")
    print(f"日志级别: {config.log_level}")
    print("✅ 配置加载成功")
