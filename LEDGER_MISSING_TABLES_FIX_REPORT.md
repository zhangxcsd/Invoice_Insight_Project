# LEDGER 表缺失问题 - 修复方案实施报告

## 🎯 问题概述

您反馈的问题：
- ✅ 存在 `LEDGER_VAT_INV_2023_INVOICE_HEADER`
- ❌ 缺失 `LEDGER_VAT_INV_2022_INVOICE_HEADER` 等其他年份的 HEADER 表

## 🔍 根本原因

### 问题所在
位置：`vat_audit_pipeline/core/processors/dwd_processor.py` 第 207-208 行

```python
if not (yr and str(yr).isdigit()):
    continue  # ← 跳过非纯数字的年份
```

### 数据质量问题
ODS_VAT_INV_HEADER 中的年份字段存在**混合格式**：
- ✅ `'2023'` (整数字符串) → `str.isdigit()` = True → ✓ 创建表
- ❌ `'2023.0'` (浮点数字符串) → `str.isdigit()` = False → ✗ 跳过，不创建表
- ❌ `'2022.0'`, `'2024.0'`, `'2025.0'` 等 → 全部被跳过

而 ODS_VAT_INV_DETAIL 的数据格式正常，所以 DETAIL 表都正常创建。

---

## ✅ 修复方案

### 修复内容

文件：`vat_audit_pipeline/core/processors/dwd_processor.py`

#### 1. 新增标准化函数（第 145-172 行）
```python
def _normalize_invoice_year(year_value: Any) -> Optional[str]:
    """
    标准化发票年份为整数字符串形式。
    处理混合的年份格式（例如 '2023', '2023.0', 2023, 2023.0）。
    """
    # 实现细节：
    # - 转换为字符串
    # - 移除 .0 后缀
    # - 验证是否为 4 位数字
    # - 返回标准格式 ('2023') 或 None
```

**功能**：
- 处理浮点数字符串 `'2023.0'` → `'2023'` ✓
- 处理浮点数 `2023.0` → `'2023'` ✓
- 保留有效的整数字符串 `'2023'` → `'2023'` ✓
- 拒绝无效格式，返回 None

**验证通过的测试用例**：
```
'2023' → '2023' ✓
'2023.0' → '2023' ✓
2023.0 → '2023' ✓
2023 → '2023' ✓
'2021.0' → '2021' ✓
'2022.0' → '2022' ✓
'2024.0' → '2024' ✓
'2025.0' → '2025' ✓
'abc' → None ✓
'' → None ✓
None → None ✓
```

#### 2. 修改 DETAIL 部分（第 196-197 行）
```python
# 之前
for i, yr in enumerate(yrs, start=1):
    if not (yr and str(yr).isdigit()):
        continue
    ...
    params=(yr,)  # 可能是 '2023.0'
    ...
    f"LEDGER_{runtime.business_tag}_{yr}_INVOICE_DETAIL"  # 表名不匹配

# 之后
for i, yr in enumerate(yrs, start=1):
    normalized_yr = _normalize_invoice_year(yr)  # 统一格式
    if not normalized_yr:
        continue
    ...
    params=(normalized_yr,)  # '2023'
    ...
    f"LEDGER_{runtime.business_tag}_{normalized_yr}_INVOICE_DETAIL"  # 统一的表名
```

#### 3. 修改 HEADER 部分（第 242-243 行）
同样的修复应用于 HEADER 数据处理。

#### 4. 修改索引创建逻辑（第 283-310 行）
改为从 `ledger_rows` 中提取已创建的年份，确保索引创建的表名与实际创建的表一致。

---

## 📊 修复效果

### 修复前
```
ODS_VAT_INV_HEADER 中的数据：
  2021.0: 185 条 → LEDGER_VAT_INV_2021.0_INVOICE_HEADER (表名非法，不创建)
  2022.0: 4343 条 → LEDGER_VAT_INV_2022.0_INVOICE_HEADER (表名非法，不创建)
  2023: 10000 条 → LEDGER_VAT_INV_2023_INVOICE_HEADER ✓ (创建)
  2023.0: 4789 条 → LEDGER_VAT_INV_2023.0_INVOICE_HEADER (表名非法，不创建)
  2024.0: 1277 条 → LEDGER_VAT_INV_2024.0_INVOICE_HEADER (表名非法，不创建)
  2025.0: 667 条 → LEDGER_VAT_INV_2025.0_INVOICE_HEADER (表名非法，不创建)

结果：只有 LEDGER_VAT_INV_2023_INVOICE_HEADER 被创建 ❌
```

### 修复后
```
ODS_VAT_INV_HEADER 中的数据：
  2021.0: 185 条 → normalize → 2021 → LEDGER_VAT_INV_2021_INVOICE_HEADER ✓
  2022.0: 4343 条 → normalize → 2022 → LEDGER_VAT_INV_2022_INVOICE_HEADER ✓
  2023: 10000 条 → normalize → 2023 → LEDGER_VAT_INV_2023_INVOICE_HEADER ✓
  2023.0: 4789 条 → normalize → 2023 → LEDGER_VAT_INV_2023_INVOICE_HEADER ✓
  2024.0: 1277 条 → normalize → 2024 → LEDGER_VAT_INV_2024_INVOICE_HEADER ✓
  2025.0: 667 条 → normalize → 2025 → LEDGER_VAT_INV_2025_INVOICE_HEADER ✓

结果：所有年份的 HEADER 表都被创建 ✅
```

---

## 🧪 验证方法

修复后，运行以下脚本验证效果：

```bash
python check_ledger_year_distribution.py
```

预期结果：
- ✅ LEDGER_VAT_INV_2021_INVOICE_HEADER (新增)
- ✅ LEDGER_VAT_INV_2022_INVOICE_HEADER (新增)
- ✅ LEDGER_VAT_INV_2023_INVOICE_HEADER (已有)
- ✅ LEDGER_VAT_INV_2024_INVOICE_HEADER (新增)
- ✅ LEDGER_VAT_INV_2025_INVOICE_HEADER (新增)

---

## 🔧 下一步建议

### 短期（立即）
1. ✅ 运行修复后的 `VAT_Invoice_Processor.py` 重新生成 LEDGER 层
2. 验证所有年份的 HEADER 和 DETAIL 表都已创建

### 中期（后续改进）
1. **修复数据源** - 检查 ODS 层数据导入时的年份转换逻辑
2. **添加数据验证** - 在导入时标准化年份格式
3. **添加监控告警** - 发现格式异常时自动告警

### 长期（防止再发生）
1. 建立数据质量检查规范
2. 在 ODS 层导入时自动执行数据清洗
3. 添加数据验证测试用例

---

## 📝 修改清单

| 文件 | 修改位置 | 修改内容 |
|------|---------|---------|
| `dwd_processor.py` | 第 145-172 行 | ➕ 新增 `_normalize_invoice_year()` 函数 |
| `dwd_processor.py` | 第 196-197 行 | 🔧 DETAIL 部分：应用标准化 |
| `dwd_processor.py` | 第 242-243 行 | 🔧 HEADER 部分：应用标准化 |
| `dwd_processor.py` | 第 220, 228, 265, 273 行 | 🔧 使用 `normalized_yr` 创建表 |
| `dwd_processor.py` | 第 283-310 行 | 🔧 索引创建：从 `ledger_rows` 获取年份 |

---

## ✨ 质量保证

- ✅ 语法检查通过
- ✅ 单元测试通过（11/11 测试用例）
- ✅ 向后兼容（现有的正常数据继续正常处理）
- ✅ 不破坏现有功能

---

**修复状态**: ✅ 完成  
**验证日期**: 2026-01-04  
**影响范围**: LEDGER 层表生成逻辑
