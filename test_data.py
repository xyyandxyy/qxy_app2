#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试Excel文件
"""

import pandas as pd
import os

def create_test_excel():
    """创建测试Excel文件"""
    data = [
        ['名称', '老年人口', '青壮年人口', '儿童人口'],
        ['张家村', '85人', '120人', '35人'],
        ['李家社区', '67人', '89人', '42人'],
        ['王家村', '93人', '156人', '28人'],
        ['赵家社区', '72人', '134人', '39人'],
        ['钱家村', '88人', '98人', '45人']
    ]

    df = pd.DataFrame(data)

    # 保存为Excel文件
    output_file = 'demo_data.xlsx'
    df.to_excel(output_file, index=False, header=False)
    print(f"测试文件已创建: {output_file}")

    return output_file

if __name__ == "__main__":
    create_test_excel()