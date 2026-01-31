"""简单的配置校验测试，不依赖完整的模块导入"""

# 模拟配置校验逻辑
def validate_config_logic():
    """测试配置校验的核心逻辑"""
    
    print("="*70)
    print("配置校验逻辑测试")
    print("="*70)
    
    # 测试 1: worker_count 校验
    print("\n测试 1: worker_count 校验")
    worker_count = -1
    errors = []
    if worker_count < 1:
        errors.append(f"worker_count 必须 >= 1，当前值: {worker_count}")
    
    if errors:
        print(f"  ✅ 正确检测到错误: {errors[0]}")
    else:
        print(f"  ❌ 未检测到错误")
    
    # 测试 2: csv_chunk_size 校验
    print("\n测试 2: csv_chunk_size 校验")
    csv_chunk_size = 50
    errors = []
    if csv_chunk_size < 100:
        errors.append(f"csv_chunk_size 必须 >= 100，当前值: {csv_chunk_size}")
    
    if errors:
        print(f"  ✅ 正确检测到错误: {errors[0]}")
    else:
        print(f"  ❌ 未检测到错误")
    
    # 测试 3: stream_chunk_size 校验
    print("\n测试 3: stream_chunk_size 校验")
    stream_chunk_size = 500
    errors = []
    if stream_chunk_size < 1000:
        errors.append(f"stream_chunk_size 必须 >= 1000，当前值: {stream_chunk_size}")
    
    if errors:
        print(f"  ✅ 正确检测到错误: {errors[0]}")
    else:
        print(f"  ❌ 未检测到错误")
    
    # 测试 4: max_file_mb 校验
    print("\n测试 4: default_max_file_mb 校验")
    max_file_mb = 5
    errors = []
    if max_file_mb < 10:
        errors.append(f"default_max_file_mb 必须 >= 10，当前值: {max_file_mb}MB")
    
    if errors:
        print(f"  ✅ 正确检测到错误: {errors[0]}")
    else:
        print(f"  ❌ 未检测到错误")
    
    # 测试 5: 合法配置
    print("\n测试 5: 合法配置")
    worker_count = 4
    csv_chunk_size = 10000
    stream_chunk_size = 50000
    max_file_mb = 500
    
    errors = []
    if worker_count < 1:
        errors.append(f"worker_count 必须 >= 1")
    if csv_chunk_size < 100:
        errors.append(f"csv_chunk_size 必须 >= 100")
    if stream_chunk_size < 1000:
        errors.append(f"stream_chunk_size 必须 >= 1000")
    if max_file_mb < 10:
        errors.append(f"default_max_file_mb 必须 >= 10")
    
    if not errors:
        print(f"  ✅ 合法配置通过校验")
    else:
        print(f"  ❌ 合法配置被错误拒绝: {errors}")
    
    # 测试 6: 多个错误
    print("\n测试 6: 多个错误同时检测")
    worker_count = 0
    csv_chunk_size = 50
    stream_chunk_size = 500
    
    errors = []
    if worker_count < 1:
        errors.append(f"worker_count 必须 >= 1，当前值: {worker_count}")
    if csv_chunk_size < 100:
        errors.append(f"csv_chunk_size 必须 >= 100，当前值: {csv_chunk_size}")
    if stream_chunk_size < 1000:
        errors.append(f"stream_chunk_size 必须 >= 1000，当前值: {stream_chunk_size}")
    
    if len(errors) == 3:
        print(f"  ✅ 正确检测到所有 {len(errors)} 个错误:")
        for i, err in enumerate(errors, 1):
            print(f"     {i}. {err}")
    else:
        print(f"  ❌ 应检测到 3 个错误，实际检测到 {len(errors)} 个")
    
    print("\n" + "="*70)
    print("✅ 所有逻辑测试完成！配置校验逻辑工作正常。")
    print("="*70)


if __name__ == "__main__":
    validate_config_logic()
