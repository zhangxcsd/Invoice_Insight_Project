# 快速开始指南

## 🚀 5分钟快速部署

### 步骤 1: 检查 Python 版本
```powershell
python --version
# 需要 Python 3.8 或更高版本
```

### 步骤 2: 安装依赖包
```powershell
pip install -r requirements.txt
```

### 步骤 3: 验证环境
```powershell
python verify_dependencies.py
```

期望输出：
```
✅ 所有依赖已正确安装，环境配置完成！
```

### 步骤 4: 运行程序（任选其一，效果相同）
```powershell
# 兼容入口
python VAT_Invoice_Processor.py

# 新的包入口
python -m vat_audit_pipeline.main
```

---

## 📋 依赖包清单

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| pandas | >=2.0.0 | 数据处理 |
| numpy | >=1.24.0 | 数值计算 |
| openpyxl | >=3.0.0 | .xlsx 文件 |
| xlrd | ==1.2.0 | .xls 文件 |
| chardet | >=5.0.0 | 编码检测 |
| psutil | >=5.9.0 | 系统监控 |
| tqdm | >=4.65.0 | 进度条 |

**完整说明**: 查看 [DEPENDENCIES.md](DEPENDENCIES.md)

---

## ❓ 常见问题

### Q1: 提示缺少 tqdm 模块
```powershell
pip install tqdm>=4.65.0
```

### Q2: xlrd 版本错误
```powershell
pip uninstall xlrd
pip install xlrd==1.2.0
```

### Q3: 安装权限错误
```powershell
pip install --user -r requirements.txt
```

**更多问题**: 查看 [DEPENDENCIES.md](DEPENDENCIES.md) 的"常见问题与解决方案"章节

---

## 📖 相关文档

- [DEPENDENCIES.md](DEPENDENCIES.md) - 完整依赖安装指南
- [README.md](README.md) - 项目总体说明
- [DEPLOYMENT.md](DEPLOYMENT.md) - 生产环境部署指南
- [CONFIG_VALIDATION_GUIDE.md](CONFIG_VALIDATION_GUIDE.md) - 配置参数说明

---

## ✅ 验证检查清单

- [ ] Python 版本 >= 3.8
- [ ] 所有依赖包已安装
- [ ] `verify_dependencies.py` 输出全部 ✅
- [ ] 程序能成功导入（无 ImportError）
- [ ] 配置校验通过（无 ValueError）

完成以上检查后，您就可以开始使用 VAT_Audit_Project 了！
