# 配置系统快速启动指南

## ✅ 配置系统已就绪

所有配置已集中到 [config.yaml](config.yaml) 文件中，通过 [config_manager.py](config_manager.py) 统一管理。

---

## 🚀 快速开始

### 1. 查看当前配置

```powershell
D:/PythonCode/VAT_Audit_Project/.venv/Scripts/python.exe config_manager.py
```

### 2. 运行示例代码

```powershell
D:/PythonCode/VAT_Audit_Project/.venv/Scripts/python.exe example_config_usage.py
```

### 3. 测试配置系统

```powershell
D:/PythonCode/VAT_Audit_Project/.venv/Scripts/python.exe test_config.py
```

---

## 📝 修改配置

直接编辑 [config.yaml](config.yaml#L1)，常用配置项：

### 业务配置
```yaml
business:
  tag: "VAT_INV"          # 修改此项改变数据库文件名前缀
  description: "增值税发票专项审计"
```

### 路径配置
```yaml
paths:
  input_dir: "Source_Data"    # 输入数据目录
  database_dir: "Database"    # 数据库存储目录
  output_dir: "Outputs"       # 输出结果目录
```

### 性能配置
```yaml
parallel:
  worker_count: "auto"        # "auto" = CPU核心数, 或指定数字如 8
  dynamic_worker_adjustment:
    enabled: true             # 根据文件大小动态调整Worker数

performance:
  csv_chunk_size: 10000       # CSV批量导入块大小
  stream_chunk_size: 50000    # 流式处理块大小
  stream_chunk_dynamic: true  # 根据内存动态调整块大小
```

### 日志配置
```yaml
logging:
  enabled: true
  log_to_file: true
  log_level: "INFO"           # DEBUG | INFO | WARNING | ERROR
  log_file: "vat_audit.log"
```

---

## 🔧 在代码中使用配置

### 方式1：使用便捷属性

```python
from config_manager import get_config

config = get_config()

# 直接访问属性
business_tag = config.business_tag
worker_count = config.worker_count
csv_chunk_size = config.csv_chunk_size
```

### 方式2：使用get()方法（支持多层嵌套）

```python
# 访问嵌套配置
queue_size = config.get('performance', 'queue_mode', 'size')
batch_method = config.get('database', 'batch_operations', 'method')

# 带默认值的安全访问
custom_value = config.get('custom', 'key', default='默认值')
```

---

## 📁 文件说明

| 文件 | 说明 | 状态 |
|------|------|------|
| [config.yaml](config.yaml) | 配置文件（140+行） | ✅ 完整 |
| [config_manager.py](config_manager.py) | 配置管理器（240+行） | ✅ 完整 |
| [test_config.py](test_config.py) | 测试套件（180+行） | ✅ 6/6通过 |
| [example_config_usage.py](example_config_usage.py) | 使用示例 | ✅ 已验证 |
| [CONFIG_INTEGRATION_GUIDE.md](CONFIG_INTEGRATION_GUIDE.md) | 集成指南 | ✅ 详细 |
| [CONFIG_SUMMARY.md](CONFIG_SUMMARY.md) | 完整文档 | ✅ 200+行 |

---

## ⚠️ 最后一步：集成到主程序

配置系统已完成并测试通过，需要手动完成最后的集成步骤：

### 操作步骤

1. **打开主程序**
   ```powershell
   code VAT_Invoice_Processor.py
   ```

2. **定位到第1042-1070行**
   - 搜索 `BUSINESS_TAG =`
   - 这部分是硬编码的配置常量

3. **替换为配置管理器调用**
   - 参考 [CONFIG_INTEGRATION_GUIDE.md](CONFIG_INTEGRATION_GUIDE.md) 第3节
   - 复制"替换后代码"
   - 粘贴替换原有代码

4. **验证集成**
   ```powershell
   D:/PythonCode/VAT_Audit_Project/.venv/Scripts/python.exe VAT_Invoice_Processor.py
   ```
   - 查看日志中的 "✅ 从config.yaml加载配置成功"
   - 确认程序正常运行

---

## 🎯 集成后的效果

### 集成前（硬编码）
```python
BUSINESS_TAG = "VAT_INV"
WORKER_COUNT = 15
CSV_CHUNK_SIZE = 10000
# ... 30多行硬编码常量
```

### 集成后（配置文件驱动）
```python
config = get_config()
BUSINESS_TAG = config.business_tag
WORKER_COUNT = config.worker_count
CSV_CHUNK_SIZE = config.csv_chunk_size
# ... 所有配置从config.yaml读取
```

### 使用优势
- ✅ 修改配置无需修改代码
- ✅ 一处修改，全局生效
- ✅ 支持注释和文档说明
- ✅ 便于版本管理和团队协作
- ✅ 支持多环境配置（开发/测试/生产）

---

## 💡 实用技巧

### 快速测试配置改动

1. **修改配置**
   ```yaml
   business:
     tag: "TEST_RUN"  # 改为测试标识
   ```

2. **运行程序**
   ```powershell
   python VAT_Invoice_Processor.py
   ```

3. **检查效果**
   - 数据库文件名会变为 `TEST_RUN_Audit_Repo.db`
   - 日志文件路径会更新
   - 无需修改任何代码

### 多环境配置

创建不同的配置文件：
```
config.yaml              # 默认配置
config.development.yaml  # 开发环境
config.production.yaml   # 生产环境
```

通过环境变量切换：
```python
import os
config_file = os.getenv('VAT_CONFIG', 'config.yaml')
config = get_config(config_file)
```

---

## 📊 测试报告

最近测试结果（2026-01-03）：

```
✅ 测试1: 配置文件存在检查 - 通过 (3/3文件)
✅ 测试2: 配置加载测试 - 通过
✅ 测试3: 配置值读取测试 - 通过 (7/7项)
✅ 测试4: 嵌套配置访问测试 - 通过 (4/4项)
✅ 测试5: Sheet分类规则测试 - 通过
✅ 测试6: 列名映射测试 - 通过

总计: 6/6 测试通过 🎉
```

---

## 📚 更多文档

- **完整文档**: [CONFIG_SUMMARY.md](CONFIG_SUMMARY.md)
- **集成指南**: [CONFIG_INTEGRATION_GUIDE.md](CONFIG_INTEGRATION_GUIDE.md)
- **配置参考**: [config.yaml](config.yaml) (内含详细注释)

---

## 🆘 遇到问题？

### 问题1: 导入错误 `ModuleNotFoundError: No module named 'yaml'`
**解决方案:**
```powershell
D:/PythonCode/VAT_Audit_Project/.venv/Scripts/python.exe -m pip install pyyaml
```

### 问题2: 配置文件找不到
**解决方案:**
- 确保 `config.yaml` 在项目根目录
- 检查工作目录是否正确：
  ```python
  import os
  print(os.getcwd())  # 应输出项目根目录
  ```

### 问题3: 配置值未生效
**解决方案:**
- 检查YAML语法（缩进、冒号、引号）
- 运行测试验证：`python test_config.py`
- 重启程序（配置在程序启动时加载）

---

## ✨ 下一步

1. ✅ **配置系统已完成** - 所有测试通过
2. ⏳ **主程序集成** - 需手动完成（5-10分钟）
3. 🚀 **投入使用** - 修改config.yaml即可调整行为

**立即开始**: 查看 [CONFIG_INTEGRATION_GUIDE.md](CONFIG_INTEGRATION_GUIDE.md) 完成最后集成步骤！
