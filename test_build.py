#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试打包脚本功能
"""

import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from build_exe import create_spec_file

def test_spec_generation():
    """测试spec文件生成功能"""
    print("🔄 测试spec文件生成功能...")

    # 测试默认模式（无控制台）
    print("\\n1. 测试默认模式（无控制台）...")
    spec_file_no_console = create_spec_file(show_console=False)

    # 测试控制台模式
    print("\\n2. 测试控制台模式...")
    spec_file_with_console = create_spec_file(show_console=True)

    # 读取生成的spec文件内容
    print("\\n3. 验证生成的spec文件内容...")

    if spec_file_no_console.exists():
        with open(spec_file_no_console, 'r', encoding='utf-8') as f:
            content = f.read()

        print("✅ spec文件生成成功")
        print(f"📁 文件位置: {spec_file_no_console}")

        # 检查关键配置
        checks = [
            ("图标配置", "icon=" in content),
            ("控制台设置", "console=" in content),
            ("应用名称", "name='qxy_app2'" in content),
            ("模板包含", "('templates', 'templates')" in content),
            ("静态文件包含", "('static', 'static')" in content),
        ]

        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"{status} {check_name}: {'通过' if result else '失败'}")

        # 显示控制台设置行
        for line in content.split('\\n'):
            if 'console=' in line:
                print(f"🔧 控制台设置: {line.strip()}")
            if 'icon=' in line:
                print(f"🎨 图标设置: {line.strip()}")

    else:
        print("❌ spec文件生成失败")

    print("\\n✨ 功能特性:")
    print("🔧 支持通过 --console 参数控制是否显示控制台")
    print("🎨 自动使用 favicon.ico 作为应用图标")
    print("📦 动态生成 .spec 文件，支持不同配置")
    print("🛠️ 支持 --no-clean 参数保留构建文件")

    print("\\n📋 使用示例:")
    print("  python build_exe.py              # 默认：无控制台，使用图标")
    print("  python build_exe.py --console    # 显示控制台，使用图标")
    print("  python build_exe.py --no-clean   # 不清理之前的构建文件")


if __name__ == "__main__":
    test_spec_generation()