# 配置集中化管理 - 快速开始

## ✅ 已完成的工作

1. **创建配置文件**: `config.yaml` - 包含所有可配置项
2. **配置管理器**: `config_manager.py` - 负责加载和验证配置
3. **主程序集成**: `VAT_Invoice_Processor.py` - 已导入配置管理器

## 🚀 快速使用

### 1. 测试配置加载
```bash
python config_manager.py
```

### 2. 运行主程序
程序会自动从 `config.yaml` 加载配置：
```bash
python VAT_Invoice_Processor.py
```

## 📝 配置修改示例

### 修改业务标识
编辑 `config.yaml`:
```yaml
business:
  tag: "MY_PROJECT"  # 改为你的项目名
```

###修改性能参数
```yaml
performance:
  csv_chunk_size: 20000      # 加大块提升速度
  worker_count: 8            # 固定8个进程
```

### 修改日志配置
```yaml
logging:
  log_level: "DEBUG"         # 改为DEBUG查看详细日志
  log_file: "my_audit.log"   # 自定义日志文件名
```

## 📊 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `business.tag` | VAT_INV | 业务标识，用于数据库和表名 |
| `paths.input_dir` | Source_Data | 输入Excel文件目录 |
| `parallel.worker_count` | auto | 工作进程数 |
| `performance.csv_chunk_size` | 10000 | CSV读取块大小 |
| `performance.memory_monitoring` | enabled | 内存阈值与自动流式配置 |
| `data_processing.tax_text_to_zero` | true | 免税映射为0 |
| `logging.log_level` | INFO | 日志级别 |

完整配置项请查看 `config.yaml` 文件。

## 🔄 动态重载配置

无需重启程序即可重载配置：
```python
from config_manager import reload_config
reload_config()  # 重新加载config.yaml
```

## ⚙️ 代码中访问配置

```python
from config_manager import get_config

config = get_config()

# 方式1：使用便捷属性
business_tag = config.business_tag
worker_count = config.worker_count

# 方式2：使用get方法（支持多级访问）
log_level = config.get('logging', 'log_level', default='INFO')
chunk_size = config.get('performance', 'csv_chunk_size')
```

## 🛡️ 向后兼容

如果 `config.yaml` 不存在或加载失败，程序会自动使用默认配置，保证向后兼容性。

## 📁 文件结构

```
VAT_Audit_Project/
├── config.yaml                 # 配置文件（你可以修改）
├── config_manager.py           # 配置管理器（无需修改）
├── VAT_Invoice_Processor.py    # 主程序（已集成配置）
├── CONFIG_INTEGRATION_GUIDE.md # 集成指南
└── README_CONFIG.md            # 本文件
```

## 🎯 优势总结

✅ **无需改代码** - 所有配置在yaml文件中  
✅ **集中管理** - 一个文件管理所有配置  
✅ **类型安全** - 自动验证配置正确性  
✅ **易于维护** - 清晰的配置结构和注释  
✅ **向后兼容** - 支持默认值回退  

## 🔧 故障排查

### 配置加载失败
如果看到警告 "⚠️ 使用默认配置"，检查：
1. `config.yaml` 文件是否存在
2. yaml格式是否正确（注意缩进）
3. pyyaml包是否已安装：`pip install pyyaml`

### 配置不生效
1. 确认修改保存了 `config.yaml`
2. 重启程序加载新配置
3. 检查日志中的 "✅ 从config.yaml加载配置成功" 消息

---

**提示**: 第一次使用时，建议先运行 `python config_manager.py` 测试配置加载是否正常。
