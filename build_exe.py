import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def main():
    """构建Windows可执行文件"""
    print("开始构建Windows可执行文件...")

    # 确保我们在正确的目录中
    script_dir = Path(__file__).parent.absolute()
    os.chdir(str(script_dir))

    # 清理上一次构建的残留文件
    build_dirs = ['build', 'dist']
    for dir_name in build_dirs:
        dir_path = script_dir / dir_name
        if dir_path.exists():
            print(f"清理目录: {dir_path}")
            shutil.rmtree(str(dir_path))

    # 检查必要文件是否存在
    required_files = ['app.py', 'qxy_app2.spec']
    for file in required_files:
        file_path = script_dir / file
        if not file_path.exists():
            print(f"错误: 找不到必要文件 {file_path}")
            return 1

    # 检查templates目录
    templates_dir = script_dir / 'templates'
    if not templates_dir.exists():
        print("警告: 找不到templates目录，Web界面可能无法正常工作")

    # 创建uploads目录（如果不存在）
    uploads_dir = script_dir / 'uploads'
    if not uploads_dir.exists():
        print("创建uploads目录...")
        uploads_dir.mkdir()

    # 使用PyInstaller执行打包
    try:
        print("开始PyInstaller打包过程...")
        # 使用预定义的spec文件
        result = subprocess.run(
            ["pyinstaller", "--clean", "qxy_app2.spec"],
            check=True,
            text=True,
            capture_output=True
        )
        print("PyInstaller完成:")
        print(result.stdout)

        # 构建成功
        dist_path = script_dir / "dist"
        if dist_path.exists():
            print(f"\n打包成功! 可执行文件位于: {dist_path}")
            print("文件列表:")
            for file_path in dist_path.iterdir():
                if file_path.is_file() and file_path.suffix == '.exe':
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    print(f" - {file_path.name} ({size_mb:.2f}MB)")

            print(f"\n使用说明:")
            print(f"1. 运行 {dist_path / 'qxy_app2.exe'}")
            print(f"2. 程序会自动打开浏览器访问 http://localhost:5001")
            print(f"3. 如果浏览器未自动打开，请手动访问上述地址")
            print(f"4. 上传Excel文件进行数据处理")
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

    print("\n打包操作完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())