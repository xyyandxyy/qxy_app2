import os
import sys
import shutil
import subprocess
import platform

def main():
    """构建Windows可执行文件"""
    print("开始构建Windows可执行文件...")

    # 确保我们在正确的目录中
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 清理上一次构建的残留文件
    build_dirs = ['build', 'dist']
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)

    # 检查必要文件是否存在
    required_files = ['app.py', 'qxy_app2.spec']
    for file in required_files:
        if not os.path.exists(file):
            print(f"错误: 找不到必要文件 {file}")
            return 1

    # 检查templates目录
    if not os.path.exists('templates'):
        print("警告: 找不到templates目录，Web界面可能无法正常工作")

    # 创建uploads目录（如果不存在）
    if not os.path.exists('uploads'):
        print("创建uploads目录...")
        os.makedirs('uploads')

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
        dist_path = os.path.join(script_dir, "dist")
        if os.path.exists(dist_path):
            print(f"\n打包成功! 可执行文件位于: {dist_path}")
            print("文件列表:")
            for file in os.listdir(dist_path):
                file_path = os.path.join(dist_path, file)
                if os.path.isfile(file_path) and file.endswith('.exe'):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f" - {file} ({size_mb:.2f}MB)")

            print(f"\n使用说明:")
            print(f"1. 运行 {dist_path}/qxy_app2.exe")
            print(f"2. 打开浏览器访问 http://localhost:5001")
            print(f"3. 上传Excel文件进行数据处理")
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
        return 1

    print("\n打包操作完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())