# ODS_VAT_INV_HEADER 字段排序实现说明

## 需求

对 ODS_VAT_INV_HEADER 表的字段进行标准化排列，按照以下顺序：

1. 发票代码
2. 发票号码
3. 数电发票号码
4. 销方识别号
5. 销方名称
6. 购方识别号
7. 购买方名称
8. 开票日期
9. 金额
10. 税额
11. 价税合计
12. 发票来源
13. 发票票种
14. 发票状态
15. 是否正数发票
16. 发票风险等级
17. 开票人
18. 备注

其他额外字段排在后面，保持原有相对顺序。

## 实现方案

### 1. 核心函数：`_reorder_header_columns()`

位置：`vat_audit_pipeline/core/processors/ods_processor.py`（第 783-843 行）

功能：
- 输入：表字段列表（无序）
- 输出：按照标准顺序排列的字段列表
- 逻辑：
  1. 首先按照标准顺序添加所有存在的标准字段
  2. 然后添加其他字段（保持原有相对顺序）

```python
def _reorder_header_columns(columns: List[str], business_tag: str) -> List[str]:
    """
    按照指定的标准顺序重新排列 ODS_VAT_INV_HEADER 表的字段。
    """
```

### 2. 集成点

#### 点 1：表创建阶段（`_prepare_ods_tables` 函数）
- 位置：第 845-866 行
- 作用：在创建 ODS_VAT_INV_HEADER 表时，使用排序后的列列表
- 代码：
```python
sorted_header_columns = _reorder_header_columns(header_columns, business_tag)
pd.DataFrame(columns=sorted_header_columns).to_sql(...)
```

#### 点 2：数据导入阶段（`_import_ods_data` 函数）
- 位置：第 1020-1023 行
- 作用：数据导入时，将已排序的列用于 CSV 到数据库的合并操作
- 代码：
```python
sorted_header_columns = _reorder_header_columns(header_columns, runtime.business_tag)
table_columns_map[f"ODS_{runtime.business_tag}_HEADER"] = sorted_header_columns
```

#### 点 3：直接数据库插入（非并行模式）
- 位置：第 1139 行
- 作用：当直接向数据库插入数据时，使用排序后的列顺序
- 代码：
```python
df = df.reindex(columns=list(header_columns))
```
注：此处使用的 `header_columns` 已在表创建时确保了正确的顺序

## 验证

运行测试脚本：
```bash
python test_header_column_reorder.py
```

测试覆盖：
- ✅ 包含所有标准字段和额外字段的情况
- ✅ 只包含部分标准字段的情况
- ✅ 字段顺序验证

## 关键特性

- **无数据排序**：仅重排列（表结构），不对数据行进行排序
- **自适应**：自动处理源数据中缺失或多余的字段
- **向后兼容**：额外字段排在标准字段后面，不丢失任何数据
- **一致性**：表创建和数据导入使用同一排序函数，确保一致性

## 修改影响范围

- ✅ `vat_audit_pipeline/core/processors/ods_processor.py`：新增函数，修改两个现有函数
- ✅ 仅影响 ODS_VAT_INV_HEADER 表的列顺序
- ✅ 不影响数据完整性
- ✅ 下游表（DWD、LEDGER 等）自动受益

## 使用方式

无需修改调用代码，实现已自动集成到现有流程：
1. 运行 VAT_Invoice_Processor.py
2. 自动调用 process_ods() 函数
3. 自动应用列排序逻辑
