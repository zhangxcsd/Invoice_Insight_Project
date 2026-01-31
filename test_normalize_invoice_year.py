"""测试年份标准化函数"""

from vat_audit_pipeline.core.processors.dwd_processor import _normalize_invoice_year

print("=" * 80)
print("年份标准化函数测试")
print("=" * 80)

test_cases = [
    ("2023", "2023"),           # 整数字符串 ✓
    ("2023.0", "2023"),         # 浮点数字符串
    (2023.0, "2023"),          # 浮点数
    (2023, "2023"),            # 整数
    ("2021.0", "2021"),        # 浮点数字符串
    ("2022.0", "2022"),        # 浮点数字符串
    ("2024.0", "2024"),        # 浮点数字符串
    ("2025.0", "2025"),        # 浮点数字符串
    ("abc", None),             # 无效
    ("", None),                # 空字符串
    (None, None),              # None
    ("2023.5", "2023"),        # 向下取整（实际数据中年份都是 X.0 格式）
]

print("\n测试结果:")
print("-" * 80)

all_passed = True
for input_val, expected in test_cases:
    result = _normalize_invoice_year(input_val)
    status = "✓" if result == expected else "✗"
    
    if result != expected:
        all_passed = False
        print(f"{status} 输入: {repr(input_val):15} 期望: {repr(expected):6} 得到: {repr(result):6} ❌")
    else:
        print(f"{status} 输入: {repr(input_val):15} → {repr(result):6} ✓")

print("\n" + "=" * 80)
if all_passed:
    print("✓ 所有测试通过！")
else:
    print("✗ 有测试失败！")
print("=" * 80)
