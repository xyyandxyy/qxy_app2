#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试引线修复效果的脚本
"""

import requests
import time

def test_line_fix():
    """测试引线修复效果"""
    base_url = "http://localhost:5001"

    print("🔄 开始测试引线修复效果...")

    # 1. 测试文件上传
    print("\n1. 测试文件上传...")
    try:
        with open('demo_data.xlsx', 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/api/upload", files=files)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 文件上传成功: {result['message']}")
            else:
                print(f"❌ 文件上传失败: {response.text}")
                return
    except Exception as e:
        print(f"❌ 文件上传异常: {e}")
        return

    # 2. 测试获取当前文件信息
    print("\n2. 测试获取当前文件信息...")
    try:
        response = requests.get(f"{base_url}/api/current-file")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 当前文件: {result['filename']}, 社区数量: {result['community_count']}")
        else:
            print(f"❌ 获取文件信息失败: {response.text}")
    except Exception as e:
        print(f"❌ 获取文件信息异常: {e}")

    # 3. 测试获取社区数据
    print("\n3. 测试获取社区数据...")
    try:
        response = requests.get(f"{base_url}/api/communities")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取到 {len(result)} 个社区的数据")
            for name in list(result.keys())[:3]:  # 显示前3个社区名称
                print(f"   - {name}")
        else:
            print(f"❌ 获取社区数据失败: {response.text}")
    except Exception as e:
        print(f"❌ 获取社区数据异常: {e}")

    print(f"\n🌐 现在可以打开浏览器访问 {base_url} 测试以下操作序列:")
    print("1. 点击地图上的多个社区/村区域")
    print("2. 选择数据列并绘制图表")
    print("3. 点击'隐藏信息框'按钮")
    print("4. 点击'显示信息框'按钮")
    print("5. 点击'清空'按钮")
    print("6. 重复上述步骤，观察引线是否正常显示")
    print("\n✨ 修复要点:")
    print("- 隐藏/显示信息框时引线应该正确跟随")
    print("- 清空后重新选择时引线应该正确创建")
    print("- 引线不应该在复杂操作后消失")

if __name__ == "__main__":
    test_line_fix()