# 复杂度重构进度

## 阶段 1：函数分解与策略模式（已完成）

### 1. 提取 Sheet 处理策略 (utils/sheet_processing.py)
- `SheetTypeMapping`: 数据类，封装 sheet 处理的所有参数（表类型、目标表名、列集合、分类标签等）
- `SheetProcessingContext`: 数据类，传递 sheet 处理上下文，避免参数爆炸
- `get_sheet_handler()`: 工厂函数，根据 sheet 名和元数据返回对应策略，替代嵌套 if-elif 链
- `normalize_sheet_dataframe()`: 纯函数，类型化 + 审计列 + 年份提取 + 列重索引
- `write_to_csv_or_queue()`: 纯函数，尝试队列入库，失败回退到 CSV

### 2. 新增辅助函数 (VAT_Invoice_Processor.py)
- `process_single_sheet()`: 处理单个 sheet 的完整流程（读取、分类、规范化、写入），取代 process_file_worker_with_queue 中的巨型 if-elif 块
  - 返回结构化结果: (行数, 分类, CSV路径或'queued')
  - 集中了所有 MemoryError 和异常处理

### 3. 导入和依赖更新
- VAT_Invoice_Processor.py 顶部添加：`from vat_audit_pipeline.utils.sheet_processing import ...` 5 个新辅助
- 添加类型提示：`from typing import Optional, Tuple, Any`

## 阶段 2：配置与依赖注入（已完成）

### 4. PipelineSettings 数据类（已实现）
在 `utils/sheet_processing.py` 中添加 `PipelineSettings` 数据类：
- 集中所有配置（路径、业务标识、性能参数、内存阈值、I/O 限流、调试标志等）
- `from_config()` 类方法：从 config_manager 对象加载
- `get_database_path()` 方法：获取数据库文件完整路径
- **消除全局变量分散**：`BUSINESS_TAG`, `INPUT_DIR`, `DEBUG_MODE` 等全部转为 `settings.xxx`

### 5. build_pipeline_settings() 函数（已实现）
在 `VAT_Invoice_Processor.py` 中：
- 初始化 `PipelineSettings` 的中央工厂函数
- 自动路径解析（相对 → 绝对）
- 自动目录创建

### 6. 依赖注入指南（已实现）
新增 `DEPENDENCY_INJECTION_GUIDE.md`：
- PipelineSettings 用法示例
- 全局变量 → settings 映射表
- worker 函数的签名更新步骤
- 单元测试示例
- 后续优化方向

## 待完成的工作

### Step 1: 简化 process_file_worker_with_queue（需要手工或脚本完成）
**目标**：从 ~500+ 行嵌套 if-elif-else 压缩到 ~60 行控制流

**新逻辑**：
```python
def process_file_worker_with_queue(args, settings: PipelineSettings):
    """大幅简化版：使用工厂 + 策略模式 + 依赖注入"""
    file, meta, temp_dir_root, process_time, detail_columns, header_columns, summary_columns, special_columns, df_queue, use_csv_fallback = args
    fname = os.path.basename(file)
    result = {'temp_csvs': [], 'cast_stats_path': None, 'cast_failures_path': None, 'sheet_manifest': [], 'dataframes_queued': 0}
    cast_stats_local = []
    cast_failures_local = []
    local_errors = []
    temp_dir = ensure_worker_temp_dir(temp_dir_root)
    
    # 检测流式处理标志
    use_streaming_for_this_file = determine_streaming_mode(file, config=settings.config) and not is_xls_file(file)
    
    try:
        engine = 'xlrd' if is_xls_file(file) else None
        with pd.ExcelFile(file, engine=engine) as xl:
            for sheet in xl.sheet_names:
                # 使用工厂获取处理策略
                handler = get_sheet_handler(
                    sheet, meta,
                    detail_columns, header_columns, summary_columns, special_columns,
                    settings.business_tag  # 从 settings 获取而非全局变量
                )
                if handler is None:
                    result['sheet_manifest'].append({
                        'file': fname, 'sheet': sheet, 'classification': 'ignored',
                        'columns': ';'.join(meta.get('sheet_info', {}).get(sheet, [])),
                        'target_table': '', 'rows': 0
                    })
                    continue
                
                # 处理单个 sheet（统一的流程）
                rows_written, classification, csv_path = process_single_sheet(
                    file, sheet, handler, temp_dir, fname, process_time,
                    cast_stats_local, cast_failures_local, local_errors,
                    df_queue, use_csv_fallback, use_streaming_for_this_file
                )
                
                # 记录结果
                if csv_path == 'queued':
                    result['dataframes_queued'] += 1
                elif csv_path:
                    result['temp_csvs'].append({
                        'path': csv_path, 'target_table': handler.target_table, 'rows': rows_written
                    })
                
                # 提取汇总表的去重键
                if handler.extract_keys and rows_written > 0 and csv_path != 'queued':
                    try:
                        df_for_keys = read_csv_with_encoding_detection(csv_path, nrows=100)
                        key_cols = [c for c in ['发票代码','发票号码','数电发票号码'] if c in df_for_keys.columns]
                        if key_cols:
                            result['summary_keys'] = df_for_keys[key_cols].drop_duplicates().to_dict(orient='records')
                    except Exception:
                        pass
                
                # 记录 manifest
                cols = meta.get('sheet_info', {}).get(sheet, [])
                result['sheet_manifest'].append({
                    'file': fname, 'sheet': sheet, 'classification': classification,
                    'columns': ';'.join(cols), 'target_table': handler.target_table, 'rows': rows_written
                })
        
        # 保存统计和失败
        if cast_stats_local:
            cs_path = os.path.join(temp_dir, f"cast_stats_{uuid.uuid4().hex}.csv")
            pd.DataFrame(cast_stats_local).to_csv(cs_path, index=False, encoding='utf-8-sig')
            result['cast_stats_path'] = cs_path
        if cast_failures_local:
            cf_path = os.path.join(temp_dir, f"cast_failures_{uuid.uuid4().hex}.csv")
            pd.concat(cast_failures_local, ignore_index=True).to_csv(cf_path, index=False, encoding='utf-8-sig')
            result['cast_failures_path'] = cf_path
    
    except Exception as e:
        logger.error(f"处理文件失败 {fname}: {e}")
    
    if local_errors:
        result['errors'] = local_errors
    return result
```

**改进**：
- 消除嵌套的 if-elif-elif 链（原来处理每种 sheet 类型都重复读取、规范化、写入逻辑）
- 使用 `get_sheet_handler()` 工厂单一决策点
- 使用 `process_single_sheet()` 统一流程，避免重复代码
- 使用 `settings.business_tag` 替代全局 `BUSINESS_TAG`
- 行数从 ~500+ 缩减到 ~80，圈复杂度大幅下降

### Step 2: 同样简化 process_file_worker（不含队列版本）
原理相同，提取参数。

### Step 3: 更新 VATAuditPipeline
- 在 `__init__` 中初始化 `self.settings = build_pipeline_settings(config, BASE_DIR)`
- 在调用 `pool.apply_async(process_file_worker_with_queue, ...)` 时传入 settings
- 逐步用 `self.settings.xxx` 替代全局变量读取

### Step 4: 消除余下的全局变量
- `BUSINESS_TAG`, `INPUT_DIR`, `DB_DIR`, `OUTPUT_DIR` → `settings.business_tag`, etc.
- `DEBUG_MODE`, `TAX_TEXT_TO_ZERO` → `settings.debug_mode`, etc.
- 保留最少必要的全局变量（logger, config_manager 对象等）

## 益处总结
- **可读性**：新手可快速理解：工厂 → 策略 → 执行 → 聚合
- **可维护性**：新增 sheet 类型只需在 `get_sheet_handler()` 中加一个分支
- **可测试性**：`get_sheet_handler` / `normalize_sheet_dataframe` / `write_to_csv_or_queue` 均可独立单测；`PipelineSettings` 可注入自定义值用于测试
- **全局变量减少**：从分散的 10+ 个全局变量集中到 1 个 `settings` 对象，参数清晰
- **扩展性**：新增配置字段只需在 `PipelineSettings` 中加一个属性，无需修改函数签名

