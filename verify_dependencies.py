"""
依赖包验证脚本

验证 VAT_Audit_Project 所需的所有依赖包是否已正确安装。
运行此脚本可以快速诊断环境配置问题。

使用方法:
    python verify_dependencies.py
"""

import sys
from typing import List, Tuple


def check_dependency(name: str, version_attr: str = '__version__') -> Tuple[bool, str]:
    """检查单个依赖包是否已安装。
    
    Args:
        name: 包名
        version_attr: 版本属性名称
    
    Returns:
        (是否安装成功, 版本号或错误信息)
    """
    try:
        module = __import__(name)
        version = getattr(module, version_attr, 'unknown')
        return True, str(version)
    except ImportError as e:
        return False, str(e)


def check_python_version() -> Tuple[bool, str]:
    """检查 Python 版本是否满足要求。"""
    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}.{sys.version_info.micro}"
    
    if major < 3 or (major == 3 and minor < 8):
        return False, version_str
    return True, version_str


def main():
    """主函数：检查所有依赖并生成报告。"""
    print("=" * 70)
    print("VAT_Audit_Project 依赖包检查")
    print("=" * 70)
    
    # 1. 检查 Python 版本
    print("\n1. Python 版本检查")
    print("-" * 70)
    py_ok, py_version = check_python_version()
    status = "✅" if py_ok else "❌"
    requirement = "Python >= 3.8"
    print(f"{status} Python 版本: {py_version} (要求: {requirement})")
    
    if not py_ok:
        print("\n⚠️  Python 版本过低，请升级到 3.8 或更高版本")
    
    # 2. 检查第三方依赖包
    print("\n2. 第三方依赖包检查")
    print("-" * 70)
    
    dependencies = [
        ('pandas', '>=2.0.0'),
        ('numpy', '>=1.24.0'),
        ('openpyxl', '>=3.0.0'),
        ('xlrd', '==1.2.0'),
        ('chardet', '>=5.0.0'),
        ('psutil', '>=5.9.0'),
        ('tqdm', '>=4.65.0'),
    ]
    
    results: List[Tuple[str, bool, str, str]] = []
    
    for name, requirement in dependencies:
        ok, version = check_dependency(name)
        status = "✅" if ok else "❌"
        results.append((name, ok, version, requirement))
        
        if ok:
            print(f"{status} {name:15} {version:20} (要求: {requirement})")
        else:
            print(f"{status} {name:15} {'未安装':20} (要求: {requirement})")
    
    # 3. 检查标准库（只验证是否可导入）
    print("\n3. Python 标准库检查（抽样）")
    print("-" * 70)
    
    stdlib_modules = [
        'sqlite3',
        'logging',
        'multiprocessing',
        'json',
        'datetime',
    ]
    
    stdlib_ok = True
    for name in stdlib_modules:
        ok, version = check_dependency(name, 'unknown')
        status = "✅" if ok else "❌"
        print(f"{status} {name:15} {'可用' if ok else '不可用'}")
        if not ok:
            stdlib_ok = False
    
    # 4. 生成总结报告
    print("\n" + "=" * 70)
    print("检查结果总结")
    print("=" * 70)
    
    failed_deps = [name for name, ok, _, _ in results if not ok]
    total = len(dependencies)
    passed = total - len(failed_deps)
    
    print(f"\nPython 版本: {'✅ 通过' if py_ok else '❌ 不符合要求'}")
    print(f"第三方依赖: {passed}/{total} 已安装")
    print(f"标准库: {'✅ 正常' if stdlib_ok else '❌ 异常'}")
    
    if failed_deps:
        print(f"\n❌ 缺失的依赖包: {', '.join(failed_deps)}")
        print("\n解决方案:")
        print("  1. 安装所有依赖: pip install -r requirements.txt")
        print("  2. 或逐个安装缺失的包:")
        for name, ok, _, requirement in results:
            if not ok:
                print(f"     pip install {name}{requirement.replace('==', '==').replace('>=', '>=')}")
    
    # 5. 退出码
    if py_ok and not failed_deps and stdlib_ok:
        print("\n" + "=" * 70)
        print("✅ 所有依赖已正确安装，环境配置完成！")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌ 环境配置不完整，请按照上述提示安装缺失的依赖")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
