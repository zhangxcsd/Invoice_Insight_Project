# 代码可维护性改进 - 快速参考指南

## 🎯 目标

提升 VAT_Invoice_Processor.py 代码可维护性，通过：
1. ✅ 消除魔法字符串 - 替换为全局常量
2. ✅ 提取重复逻辑 - 创建公共辅助函数  
3. ✅ 改进代码组织 - 集中式常量管理

## 📋 改进统计

| 指标 | 数值 |
|------|------|
| 新增全局常量 | **80+** |
| 新增公共函数 | **10** |
| 替换位置 | **50+** |
| 消除的魔法字符串 | **70+** |
| 代码行数 | 3619 |
| 语法错误 | **0** ✅ |

## 🔧 使用示例

### 1. 时间戳格式化

❌ **之前（硬编码）:**
```python
filename = f"report_{process_time.replace(':','-').replace(' ','_')}.csv"
```

✅ **之后（使用函数）:**
```python
filename = f"report_{format_timestamp_for_filename(process_time)}.csv"
# 或者直接使用生成函数
filename = generate_manifest_filename("report", process_time)
```

### 2. 添加审计列

❌ **之前（分散的代码）:**
```python
df['AUDIT_SRC_FILE'] = fname
df['AUDIT_IMPORT_TIME'] = process_time
if '开票日期' in df.columns:
    df['开票年份'] = df['开票日期'].astype(str).str[:4]
df = df.reindex(columns=target_cols)
```

✅ **之后（集中的函数调用）:**
```python
df = add_audit_columns(df, fname, process_time)
if INVOICE_DATE_COL in df.columns:
    df = add_invoice_year_column(df)
df = filter_dataframe_columns(df, target_cols)
```

### 3. CSV 输出

❌ **之前（重复的参数）:**
```python
df.to_csv(path1, index=False, encoding='utf-8-sig')
df.to_csv(path2, index=False, encoding='utf-8-sig')
df.to_csv(path3, index=False, encoding='utf-8-sig')
```

✅ **之后（统一的函数）:**
```python
save_dataframe_to_csv(df, path1)
save_dataframe_to_csv(df, path2)
save_dataframe_to_csv(df, path3)
```

### 4. 列常量使用

❌ **之前（硬编码的列名）:**
```python
if '开票日期' in df.columns:
    key_cols = [c for c in ['发票代码','发票号码','数电发票号码'] if c in df.columns]
```

✅ **之后（使用常量）:**
```python
if INVOICE_DATE_COL in df.columns:
    key_cols = select_invoice_key_columns(df)
```

## 📚 常用常量速查

### 列名常量
```python
INVOICE_CODE_COL        # '发票代码'
INVOICE_NUMBER_COL      # '发票号码'
ETICKET_NUMBER_COL      # '数电发票号码'
INVOICE_DATE_COL        # '开票日期'
INVOICE_YEAR_COL        # '开票年份'
AUDIT_SRC_FILE_COL      # 'AUDIT_SRC_FILE'
AUDIT_IMPORT_TIME_COL   # 'AUDIT_IMPORT_TIME'
```

### 列列表常量
```python
INVOICE_KEY_COLS    # [INVOICE_CODE_COL, INVOICE_NUMBER_COL, ETICKET_NUMBER_COL]
DETAIL_COLS_NEEDED  # 明细表 26 列
HEADER_COLS_NEEDED  # 表头表 20 列
DETAIL_DEDUP_COLS   # 明细表去重列
HEADER_DEDUP_COLS   # 表头表去重列
```

### 文件命名常量
```python
MANIFEST_PREFIX           # 'ods_sheet_manifest'
CAST_STATS_PREFIX         # 'ods_type_cast_manifest'
CAST_FAILURES_PREFIX      # 'ods_type_cast_failures'
ERROR_LOG_PREFIX          # 'process_error_logs'
IMPORT_SUMMARY_PREFIX     # 'ods_import_summary'
LEDGER_MANIFEST_PREFIX    # 'invoice_ledgers_manifest'
```

### 处理配置常量
```python
DEFAULT_CSV_CHUNK_SIZE      # 1000
DEFAULT_STREAM_CHUNK_SIZE   # 10000
CSV_ENCODING                # 'utf-8-sig'
TEMP_FILE_PREFIX            # 'tmp_imports'
```

## 🔍 常用函数速查

### 时间和文件名处理
```python
format_timestamp_for_filename(timestamp: str) -> str
# 将 '2024-01-02 12:00:00' 转为 '2024-01-02_12-00-00'

generate_manifest_filename(prefix: str, timestamp: str) -> str
# 生成完整文件名：'prefix_2024-01-02_12-00-00.csv'

extract_table_prefix_from_filename(filename: str) -> Optional[str]
# 从 'TABLE__file__sheet__uuid.csv' 提取 'TABLE'
```

### DataFrame 操作
```python
add_audit_columns(df: pd.DataFrame, source_file: str, import_time: str) -> pd.DataFrame
# 添加 AUDIT_SRC_FILE 和 AUDIT_IMPORT_TIME 列

add_invoice_year_column(df: pd.DataFrame) -> pd.DataFrame
# 从 INVOICE_DATE_COL 提取年份到 INVOICE_YEAR_COL

select_invoice_key_columns(df: pd.DataFrame) -> List[str]
# 返回数据中存在的发票关键列

filter_dataframe_columns(df: pd.DataFrame, target_columns: List[str]) -> pd.DataFrame
# 过滤并重新索引列

save_dataframe_to_csv(df: pd.DataFrame, output_path: str) -> None
# 保存 DataFrame 为 CSV（utf-8-sig 编码）
```

## 🎓 学习建议

1. **查看函数文档**
   ```python
   >>> help(add_audit_columns)
   >>> help(format_timestamp_for_filename)
   ```

2. **找出常用模式**
   - 所有时间戳格式化 → 使用 `format_timestamp_for_filename()`
   - 所有文件名生成 → 使用 `generate_manifest_filename()`
   - 所有 CSV 输出 → 使用 `save_dataframe_to_csv()`
   - 所有列赋值 → 使用 `add_audit_columns()` 等函数

3. **维护常量**
   - 修改列名？编辑常量定义（Lines 95-146）
   - 修改输出编码？改 `CSV_ENCODING` 常量
   - 修改文件前缀？改相应 `*_PREFIX` 常量

## ⚠️ 常见注意事项

1. **添加新列时** - 确定是否应该加到相应的列列表常量中
2. **修改列名时** - 必须同时更新常量和使用处
3. **修改文件格式时** - 检查是否需要更新 CSV_ENCODING 或函数参数
4. **性能考量** - 函数调用有少量开销，但代码简化的好处更大

## 📞 反馈和改进

如果发现以下情况，请添加新的常量或函数：
- ✅ 魔法字符串出现 2 次以上
- ✅ 代码片段重复 3 次以上
- ✅ 参数列表长且重复

---

**最后更新**: 2026-01-03  
**维护者**: GitHub Copilot  
**版本**: 1.0
