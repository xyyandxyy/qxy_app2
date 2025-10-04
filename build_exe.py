#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 Windows 可执行文件的脚本
支持图标和控制台显示选项
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse
from pathlib import Path


def create_spec_file(show_console=False):
    """创建.spec文件并配置图标和控制台选项"""
    script_dir = Path(__file__).parent.absolute()
    icon_path = script_dir / 'favicon.ico'

    # 检查图标文件是否存在
    if not icon_path.exists():
        print(f"警告: 找不到图标文件 {icon_path}, 将不使用图标")
        icon_line = "    icon=None,"
    else:
        icon_line = f"    icon='{icon_path}',"

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'pandas',
        'openpyxl',
        'flask',
        'werkzeug',
        'jinja2',
        'click',
        'itsdangerous',
        'markupsafe',
        'pathlib',
        'urllib.parse',
        'threading',
        'time',
        'webbrowser',
        'uuid',
        'io',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='qxy_app2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={str(show_console).lower()},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
{icon_line}
)
'''

    spec_file = script_dir / 'qxy_app2.spec'
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print(f"已创建 .spec 文件: {spec_file}")
    print(f"  - 控制台显示: {'开启' if show_console else '关闭'}")
    print(f"  - 图标文件: {icon_path if icon_path.exists() else '无'}")

    return spec_file


def main():
    """构建 Windows 可执行文件"""
    parser = argparse.ArgumentParser(description='构建 Windows 可执行文件')
    parser.add_argument('--console', action='store_true',
                       help='显示控制台窗口（默认不显示）')
    parser.add_argument('--no-clean', action='store_true',
                       help='不清理之前的构建文件')

    args = parser.parse_args()

    console_mode = args.console
    clean_build = not args.no_clean

    print(f"开始构建 Windows 可执行文件...")
    print(f"  - 控制台显示: {'开启' if console_mode else '关闭'}")
    print(f"  - 清理构建: {'开启' if clean_build else '关闭'}")

    # 确保我们在正确的目录中
    script_dir = Path(__file__).parent.absolute()
    os.chdir(str(script_dir))

    # 清理上一次构建的残留文件
    if clean_build:
        build_dirs = ['build', 'dist']
        for dir_name in build_dirs:
            dir_path = script_dir / dir_name
            if dir_path.exists():
                print(f"清理目录: {dir_path}")
                shutil.rmtree(str(dir_path))

    # 检查必要文件是否存在
    required_files = ['app.py']
    for file in required_files:
        file_path = script_dir / file
        if not file_path.exists():
            print(f"错误: 找不到必要文件 {file_path}")
            return 1

    # 检查templates目录
    templates_dir = script_dir / 'templates'
    if not templates_dir.exists():
        print("警告: 找不到templates目录，Web界面可能无法正常工作")

    # 创建动态 .spec 文件
    spec_file = create_spec_file(show_console=console_mode)

    # 使用PyInstaller执行打包
    try:
        print("开始PyInstaller打包过程...")
        # 使用动态生成的spec文件
        result = subprocess.run(
            ["pyinstaller", "--clean", str(spec_file)],
            check=True,
            text=True,
            capture_output=True
        )
        print("PyInstaller完成:")
        print(result.stdout)

        # 构建成功
        dist_path = script_dir / "dist"
        if dist_path.exists():
            print(f"\\n打包成功! 可执行文件位于: {dist_path}")
            print(f"配置信息:")
            print(f"  - 控制台显示: {'开启' if console_mode else '关闭'}")
            print(f"  - 使用图标: {'是' if (script_dir / 'favicon.ico').exists() else '否'}")
            print(f"\\n文件列表:")
            for file_path in dist_path.iterdir():
                if file_path.is_file() and file_path.suffix == '.exe':
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    print(f" - {file_path.name} ({size_mb:.2f}MB)")

            print(f"\\n使用说明:")
            print(f"1. 运行 {dist_path / 'qxy_app2.exe'}")
            if not console_mode:
                print(f"2. 程序会自动打开浏览器访问 http://localhost:5001")
                print(f"3. 如果浏览器未自动打开，请手动访问上述地址")
                print(f"4. 上传Excel文件进行数据处理")
            else:
                print(f"2. 程序会显示控制台窗口和调试信息")
                print(f"3. 程序会自动打开浏览器访问 http://localhost:5001")
                print(f"4. 上传Excel文件进行数据处理")

            print(f"\\n参数说明:")
            print(f"  - 使用 --console 参数可以重新打包为显示控制台的版本")
            print(f"  - 使用 --no-clean 参数可以保留上次构建的文件")
            print(f"\\n示例命令:")
            print(f"  python build_exe.py              # 默认：无控制台")
            print(f"  python build_exe.py --console    # 显示控制台")
        else:
            print("警告: 找不到dist目录，打包可能失败")

    except subprocess.CalledProcessError as e:
        print("打包失败:")
        print(e.stdout)
        print(e.stderr)
        return 1
    except FileNotFoundError:
        print("错误: 找不到pyinstaller命令")
        print("请先安装PyInstaller: pip install pyinstaller")
        print("完整安装命令: pip install -r requirements.txt")
        return 1

    print("\\n打包操作完成!")
    return 0


if __name__ == "__main__":
    sys.exit(main())