# LEDGER 表缺失的根本原因分析报告

## 🔴 问题现象

您报告的问题：

但 DETAIL 表都存在：

`ODS_VAT_INV_HEADER_FULL_2021`
`ODS_VAT_INV_HEADER_FULL_2022`
`ODS_VAT_INV_HEADER_FULL_2023`
`ODS_VAT_INV_HEADER_FULL_2024`
`ODS_VAT_INV_HEADER_FULL_2025`

### 问题代码

```python
try:
    yrs_hdr = pd.read_sql(
        f"SELECT DISTINCT {models.INVOICE_YEAR_COL} as y FROM ODS_{runtime.business_tag}_HEADER WHERE {models.INVOICE_YEAR_COL} IS NOT NULL ORDER BY y",
        conn,
    )["y"].dropna().tolist()
except Exception:
    yrs_hdr = []
```

### 数据质量问题

ODS_VAT_INV_HEADER 中的 开票年份 字段存在**混合格式**：

```
开票年份 = '2021.0'  (字符串 "2021.0")    ← 浮点数字符串
开票年份 = '2022.0'  (字符串 "2022.0")    ← 浮点数字符串
开票年份 = '2023'    (字符串 "2023")      ← 整数字符串 ✓
开票年份 = '2023.0'  (字符串 "2023.0")    ← 浮点数字符串
开票年份 = '2024.0'  (字符串 "2024.0")    ← 浮点数字符串
开票年份 = '2025.0'  (字符串 "2025.0")    ← 浮点数字符串
```

### 关键检查条件

代码第 208 行的检查：

```python
if not (yr and str(yr).isdigit()):
    continue  # ← 跳过不是纯数字的年份
```

**问题分析**：

- ✅ `str('2023').isdigit()` → `True` → 会创建表
- ❌ `str('2023.0').isdigit()` → `False` → 被跳过，不创建表
- ❌ `str('2022.0').isdigit()` → `False` → 被跳过，不创建表
- ❌ `str('2024.0').isdigit()` → `False` → 被跳过，不创建表

---

## 📊 数据对比分析

### ODS_VAT_INV_DETAIL（正常）

```
年份数据格式：整数字符串
开票年份 = '2021'
开票年份 = '2022'
开票年份 = '2023'
开票年份 = '2024'
开票年份 = '2025'

对应的 LEDGER 表：✅ 全部存在（5 个表）
```

### ODS_VAT_INV_HEADER（问题）

```
年份数据格式：混合格式（浮点数字符串 + 整数字符串）
开票年份 = '2021.0' → str.isdigit() = False ❌
开票年份 = '2022.0' → str.isdigit() = False ❌
开票年份 = '2023'   → str.isdigit() = True  ✅
开票年份 = '2023.0' → str.isdigit() = False ❌
开票年份 = '2024.0' → str.isdigit() = False ❌
开票年份 = '2025.0' → str.isdigit() = False ❌

对应的 LEDGER 表：只有 2023 ❌ （其他年份全部缺失）
```

---

## 🐛 问题的来源

### 数据导入阶段的问题

在 ODS 层导入数据时，开票年份的转换不一致：

**ODS_VAT_INV_DETAIL**:

```python
# 年份提取成功，格式为整数字符串
开票年份 = '2021', '2022', '2023', '2024', '2025'
```

**ODS_VAT_INV_HEADER**:

```python
# 年份提取失败或格式混乱
开票年份 = '2021.0', '2022.0', '2023', '2023.0', '2024.0', '2025.0'
# 混合的原因：可能是类型转换不当或数据源本身的差异
```

---

## ✅ 解决方案

### 方案 1：修复数据源（根本解决）

在数据导入时，确保 开票年份 字段的统一格式：

**位置**: `vat_audit_pipeline/utils/file_handlers.py` 或 `ods_processor.py`

```python
# 添加数据清洗步骤
def normalize_invoice_year(year_value):
    """标准化年份值为整数字符串"""
    if year_value is None or year_value == '':
        return None
    
    # 转换为字符串
    year_str = str(year_value).strip()
    
    # 移除 .0 后缀
    if year_str.endswith('.0'):
        year_str = year_str[:-2]
    
    # 验证是否为有效年份
    if year_str.isdigit():
        return year_str
    else:
        return None

# 在加载 HEADER 数据时应用：
df[INVOICE_YEAR_COL] = df[INVOICE_YEAR_COL].apply(normalize_invoice_year)
```

### 方案 2：修复 LEDGER 生成逻辑（快速修复）

修改 dwd_processor.py 中的年份检查条件：

```python
# 当前代码（第 208 行）
if not (yr and str(yr).isdigit()):
    continue

# 修改为
if not yr:
    continue

year_str = str(yr).strip()
if year_str.endswith('.0'):
    year_str = year_str[:-2]

if not year_str.isdigit():
    continue

# 然后使用 year_str 创建表
yr = year_str  # 或在后续代码中使用 year_str
```

或更简洁的方式：

```python
# 提取纯数字部分
try:
    yr_int = int(float(str(yr)))  # '2023.0' → 2023 → '2023'
    yr = str(yr_int)
except (ValueError, TypeError):
    continue

if not yr.isdigit():
    continue
```

---

## 🛠️ 建议修复优先级

| 优先级 | 方案 | 工作量 | 效果 |
|--------|------|--------|------|
| 🔴 高 | 修复数据源格式（方案 1） | 中 | 彻底解决，防止后续问题 |
| 🟡 中 | 修复 LEDGER 生成逻辑（方案 2） | 小 | 快速修复当前问题 |
| 🟢 低 | 添加数据验证告警 | 小 | 早期发现类似问题 |

---

## 📝 建议修复步骤

1. **立即修复**（方案 2）：修改 dwd_processor.py 的年份验证逻辑
2. **中期修复**（方案 1）：找到年份字段转换的源头，统一格式
3. **长期方案**：添加数据质量检查，防止类似问题再发生

---

## 验证脚本

修复后，可运行以下脚本验证：

```bash
python check_ledger_year_distribution.py
```

应该显示所有年份都有对应的 HEADER 表。
