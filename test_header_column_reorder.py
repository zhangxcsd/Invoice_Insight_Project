"""测试 ODS_VAT_INV_HEADER 字段重排序功能"""

from vat_audit_pipeline.core.processors.ods_processor import _reorder_header_columns

# 测试用例 1：包含所有标准字段和额外字段
test_columns_1 = [
    "备注",  # 顺序混乱
    "发票代码",
    "其他字段1",
    "发票号码",
    "数电发票号码",
    "销方识别号",
    "销方名称",
    "购方识别号",
    "购买方名称",
    "开票日期",
    "金额",
    "其他字段2",
    "税额",
    "价税合计",
    "发票来源",
    "发票票种",
    "发票状态",
    "是否正数发票",
    "发票风险等级",
    "开票人",
]

result_1 = _reorder_header_columns(test_columns_1, "VAT_INV")
print("测试用例 1 - 包含所有字段和额外字段:")
print("输入:", test_columns_1)
print("\n输出(重排序后):")
for i, col in enumerate(result_1, 1):
    print(f"  {i}. {col}")

# 验证顺序是否正确
expected_order = [
    "发票代码",
    "发票号码",
    "数电发票号码",
    "销方识别号",
    "销方名称",
    "购方识别号",
    "购买方名称",
    "开票日期",
    "金额",
    "税额",
    "价税合计",
    "发票来源",
    "发票票种",
    "发票状态",
    "是否正数发票",
    "发票风险等级",
    "开票人",
    "备注",
    "其他字段1",
    "其他字段2",
]

print("\n✓ 验证结果:")
if result_1 == expected_order:
    print("  ✓ 排序正确！")
else:
    print("  ✗ 排序有问题！")
    print("  预期:", expected_order)
    print("  实际:", result_1)

# 测试用例 2：只有部分标准字段
test_columns_2 = [
    "发票号码",
    "发票代码",
    "销方识别号",
    "开票日期",
]

result_2 = _reorder_header_columns(test_columns_2, "VAT_INV")
print("\n\n测试用例 2 - 只有部分标准字段:")
print("输入:", test_columns_2)
print("\n输出(重排序后):")
for i, col in enumerate(result_2, 1):
    print(f"  {i}. {col}")

expected_order_2 = [
    "发票代码",
    "发票号码",
    "销方识别号",
    "开票日期",
]

print("\n✓ 验证结果:")
if result_2 == expected_order_2:
    print("  ✓ 排序正确！")
else:
    print("  ✗ 排序有问题！")
    print("  预期:", expected_order_2)
    print("  实际:", result_2)

print("\n" + "="*60)
print("所有测试完成！")
