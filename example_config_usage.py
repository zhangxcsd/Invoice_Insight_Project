"""
配置使用示例
演示如何在代码中使用config_manager
"""

from config_manager import get_config

# 获取配置实例（单例模式，全局唯一）
config = get_config()

print("=" * 60)
print("配置使用示例".center(60))
print("=" * 60)

# 示例1: 使用便捷属性访问配置
print("\n【示例1】使用便捷属性:")
print(f"  业务标识: {config.business_tag}")
print(f"  输入目录: {config.input_dir}")
print(f"  数据库目录: {config.database_dir}")
print(f"  输出目录: {config.output_dir}")

# 示例2: 访问性能配置
print("\n【示例2】性能配置:")
print(f"  工作进程数: {config.worker_count}")
print(f"  CSV块大小: {config.csv_chunk_size:,} 行")
print(f"  流式块大小: {config.stream_chunk_size:,} 行")
print(f"  动态Worker调整: {'开启' if config.dynamic_worker_adjustment else '关闭'}")

# 示例3: 访问数据处理配置
print("\n【示例3】数据处理配置:")
print(f"  最大失败样本数: {config.max_failure_samples}")
print(f"  免税映射为0: {'是' if config.tax_text_to_zero else '否'}")
print(f"  过滤空行: {'是' if config.filter_empty_rows else '否'}")
print(f"  过滤NaN行: {'是' if config.filter_nan_rows else '否'}")

# 示例4: 访问日志配置
print("\n【示例4】日志配置:")
print(f"  日志级别: {config.log_level}")
print(f"  日志文件: {config.log_file}")
print(f"  日志到文件: {'是' if config.log_to_file else '否'}")

# 示例5: 使用get()方法访问嵌套配置
print("\n【示例5】嵌套配置访问:")
business_desc = config.get('business', 'description', default='未设置')
print(f"  业务描述: {business_desc}")

queue_enabled = config.get('performance', 'queue_mode', 'enabled')
print(f"  队列模式: {'启用' if queue_enabled else '禁用'}")

batch_method = config.get('database', 'batch_operations', 'method')
print(f"  批量操作方法: {batch_method}")

# 示例6: 访问Sheet分类规则
print("\n【示例6】Sheet分类规则:")
detail_patterns = config.detail_patterns
print(f"  明细表规则 ({len(detail_patterns)}个):")
for pattern in detail_patterns:
    print(f"    - {pattern}")

special_sheets = config.special_sheets
print(f"  特殊表映射 ({len(special_sheets)}个):")
for sheet_name, suffix in list(special_sheets.items())[:3]:
    print(f"    - {sheet_name} → {suffix}")

# 示例7: 访问列名映射
print("\n【示例7】列名映射:")
date_cols = config.date_columns
print(f"  日期列: {', '.join(date_cols)}")

numeric_cols = config.numeric_columns
print(f"  数值列: {', '.join(numeric_cols[:3])} 等{len(numeric_cols)}个")

tax_tokens = config.tax_text_tokens
print(f"  税率文本标记: {', '.join(tax_tokens)}")

# 示例8: 文件大小阈值
print("\n【示例8】文件大小阈值:")
thresholds = config.file_size_thresholds
print(f"  小文件阈值: {thresholds['small']}MB")
print(f"  中等文件阈值: {thresholds['medium']}MB")
print(f"  大文件阈值: {thresholds['large']}MB")

# 示例9: 安全访问不存在的配置（使用默认值）
print("\n【示例9】安全访问（带默认值）:")
unknown_value = config.get('unknown', 'key', default='默认值')
print(f"  不存在的配置: {unknown_value}")

# 示例10: 在实际代码中的使用
print("\n【示例10】实际代码使用:")
print("```python")
print("# 在VAT_Invoice_Processor.py中")
print("from config_manager import get_config")
print("")
print("config = get_config()")
print("BUSINESS_TAG = config.business_tag")
print("WORKER_COUNT = config.worker_count")
print("CSV_CHUNK_SIZE = config.csv_chunk_size")
print("")
print("# 构建数据库路径")
print("DB_PATH = os.path.join(BASE_DIR, config.database_dir, f'{BUSINESS_TAG}_Audit_Repo.db')")
print("```")

print("\n" + "=" * 60)
print("✅ 配置使用示例完成".center(60))
print("=" * 60)

# 提示信息
print("\n💡 提示:")
print("  1. 修改config.yaml后重启程序即可生效")
print("  2. 使用config.get()可以安全访问任何配置项")
print("  3. 运行 python test_config.py 测试配置完整性")
