# 打包说明

## 概述

本项目支持将 Python 应用打包为 Windows 可执行文件，支持自定义图标和控制台显示选项。

## 功能特性

- ✅ **自定义图标**: 自动使用 `favicon.ico` 作为可执行文件图标
- ✅ **控制台控制**: 通过参数选择是否显示后台控制台窗口
- ✅ **动态配置**: 根据参数动态生成 PyInstaller 配置文件
- ✅ **清理选项**: 支持保留或清理之前的构建文件

## 使用方法

### 基本命令

```bash
# 默认模式：无控制台窗口，使用图标
python build_exe.py

# 显示控制台窗口（用于调试）
python build_exe.py --console

# 不清理之前的构建文件
python build_exe.py --no-clean

# 组合使用
python build_exe.py --console --no-clean
```

### 参数说明

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `--console` | 显示控制台窗口 | 不显示 |
| `--no-clean` | 不清理之前的构建文件 | 清理 |
| `--help` | 显示帮助信息 | - |

## 配置详情

### 图标设置
- 图标文件位置: `favicon.ico`
- 图标来源: `/Users/xyy/git_syn/utils/qxy_app/favicon.ico`
- 如果图标文件不存在，将不使用图标

### 控制台模式
- **默认 (无控制台)**: 适合最终用户使用，窗口简洁
- **控制台模式**: 适合开发和调试，显示详细日志

### 打包输出
- 输出目录: `dist/`
- 可执行文件: `qxy_app2.exe`
- 包含模板文件和静态资源

## 构建步骤

1. **准备环境**
   ```bash
   pip install pyinstaller
   ```

2. **确保文件完整**
   - `app.py` - 主应用文件
   - `templates/` - HTML 模板目录
   - `static/` - 静态资源目录（如果有）
   - `favicon.ico` - 应用图标

3. **执行打包**
   ```bash
   python build_exe.py
   ```

4. **测试可执行文件**
   ```bash
   ./dist/qxy_app2.exe
   ```

## 输出示例

```
开始构建 Windows 可执行文件...
  - 控制台显示: 关闭
  - 清理构建: 开启

已创建 .spec 文件: /path/to/qxy_app2.spec
  - 控制台显示: 关闭
  - 图标文件: /path/to/favicon.ico

开始PyInstaller打包过程...
PyInstaller完成:
...

打包成功! 可执行文件位于: /path/to/dist
配置信息:
  - 控制台显示: 关闭
  - 使用图标: 是

文件列表:
 - qxy_app2.exe (45.67MB)

使用说明:
1. 运行 /path/to/dist/qxy_app2.exe
2. 程序会自动打开浏览器访问 http://localhost:5001
3. 如果浏览器未自动打开，请手动访问上述地址
4. 上传Excel文件进行数据处理
```

## 故障排除

### 常见问题

1. **找不到 pyinstaller**
   ```bash
   pip install pyinstaller
   ```

2. **图标文件不存在**
   - 确保 `favicon.ico` 在项目根目录
   - 或手动复制图标文件到项目目录

3. **模板文件丢失**
   - 确保 `templates/` 目录存在
   - 检查 `templates/index.html` 等文件

4. **运行时错误**
   - 使用 `--console` 参数重新打包以查看详细错误信息
   - 检查所有依赖库是否正确安装

### 开发建议

- 开发时使用 `--console` 参数便于调试
- 发布时使用默认参数获得更好的用户体验
- 使用 `--no-clean` 可以加速重复构建过程

## 项目结构

```
qxy_app2/
├── app.py              # 主应用文件
├── build_exe.py        # 打包脚本
├── favicon.ico         # 应用图标
├── templates/          # HTML 模板
│   └── index.html
├── static/            # 静态资源（可选）
├── build/             # 构建临时文件（自动生成）
├── dist/              # 输出目录（自动生成）
│   └── qxy_app2.exe   # 最终可执行文件
└── qxy_app2.spec      # PyInstaller 配置文件（自动生成）
```