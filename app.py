from flask import Flask, render_template, jsonify, request, session
import pandas as pd
import json
import re
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote
from werkzeug.utils import secure_filename
import io
import uuid

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())  # 用于session管理

# 配置文件处理 - 使用内存模式避免Windows路径问题
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# 全局变量存储当前文件数据
current_file_data = None  # 存储文件数据在内存中
current_filename = None   # 存储原始文件名
community_data_cache = {}  # 缓存处理后的数据

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_people_count(text):
    """从文本中提取人数"""
    if not text or text == 'nan' or pd.isna(text):
        return 0

    text = str(text)
    # 使用正则表达式匹配"x人"模式
    pattern = r'(\d+)人'
    match = re.search(pattern, text)
    if match:
        return int(match.group(1))
    return 0

def process_data_value(value):
    """处理数据值，空值默认为0"""
    if pd.isna(value) or value == '' or str(value).strip() == '':
        return '0'
    return str(value).strip()

def load_excel_data(file_data=None, filename=None):
    """读取Excel文件并返回社区/村数据"""
    global current_file_data, current_filename, community_data_cache

    try:
        # 如果没有指定文件数据，使用全局缓存
        if file_data is None:
            if current_file_data is None:
                # 没有上传文件，返回空数据
                return {}
            file_data = current_file_data
            filename = current_filename

        # 检查缓存
        cache_key = f"{filename}_{len(file_data) if file_data else 0}"
        if cache_key in community_data_cache:
            print(f"使用缓存数据: {filename}")
            return community_data_cache[cache_key]

        print(f"从内存数据处理Excel文件: {filename}")

        # 从内存中的字节数据读取Excel
        if isinstance(file_data, bytes):
            df = pd.read_excel(io.BytesIO(file_data), header=0)
        else:
            print("错误：文件数据格式不正确")
            return {}

        # 获取实际的列名（第一行数据）
        header_row = df.iloc[0]  # 第一行数据就是列标题

        # 重新读取，跳过第一行，使用第二行开始的数据
        if isinstance(file_data, bytes):
            df = pd.read_excel(io.BytesIO(file_data), header=None, skiprows=1)
        else:
            return {}

        # 设置列名为第一行的内容
        df.columns = header_row.tolist()

        # 筛选第一列包含"社区"或"村"的行
        community_data = {}
        for index, row in df.iterrows():
            community_name = str(row.iloc[0]).strip()
            if '社区' in community_name or '村' in community_name:
                # 获取列名
                column_names = df.columns.tolist()

                # 处理各列数据
                community_info = {
                    'name': community_name,
                    'columns': {}  # 存储列名和数据的映射
                }

                # 遍历所有列（除了第一列名称列）
                for i, col_name in enumerate(column_names[1:], 1):
                    if i < len(row):
                        col_raw = process_data_value(row.iloc[i])
                        people_count = extract_people_count(col_raw)

                        community_info['columns'][col_name] = {
                            'raw_data': col_raw,
                            'people_count': people_count
                        }

                # 保持向后兼容性，仍然提供原来的字段
                if len(column_names) > 1:
                    community_info['column2'] = community_info['columns'].get(column_names[1], {}).get('raw_data', '0')
                    community_info['people_count_col2'] = community_info['columns'].get(column_names[1], {}).get('people_count', 0)
                if len(column_names) > 2:
                    community_info['column3'] = community_info['columns'].get(column_names[2], {}).get('raw_data', '0')
                    community_info['people_count_col3'] = community_info['columns'].get(column_names[2], {}).get('people_count', 0)
                if len(column_names) > 3:
                    community_info['column4'] = community_info['columns'].get(column_names[3], {}).get('raw_data', '0')
                    community_info['people_count_col4'] = community_info['columns'].get(column_names[3], {}).get('people_count', 0)
                if len(column_names) > 4:
                    community_info['column5'] = community_info['columns'].get(column_names[4], {}).get('raw_data', '0')
                    community_info['people_count_col5'] = community_info['columns'].get(column_names[4], {}).get('people_count', 0)

                community_data[community_name] = community_info

        # 缓存结果
        community_data_cache[cache_key] = community_data
        print(f"处理完成，找到 {len(community_data)} 个社区/村")

        return community_data
    except Exception as e:
        print(f"读取Excel文件出错: {e}")
        return {}

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理Excel文件上传 - 使用内存模式"""
    global current_file_data, current_filename

    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件被上传'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        # 检查文件大小，限制为100MB
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 重置文件指针

        if file_size > app.config['MAX_CONTENT_LENGTH']:
            return jsonify({'error': '文件太大，请上传不超过100MB的文件'}), 400

        if file and allowed_file(file.filename):
            # 获取原始文件名
            original_filename = file.filename
            print(f"开始处理文件：{original_filename}")

            try:
                # 直接读取文件内容到内存
                file_data = file.read()
                print(f"文件读取到内存成功，大小：{len(file_data)} 字节")

                # 存储文件数据和文件名到全局变量
                current_file_data = file_data
                current_filename = original_filename

                # 直接从内存数据加载并分析文件
                data = load_excel_data(file_data=file_data, filename=original_filename)
                community_count = len(data)

                if community_count > 0:
                    print(f"文件处理成功：{original_filename}，找到 {community_count} 个社区/村")
                    return jsonify({
                        'success': True,
                        'message': f'文件上传成功！找到 {community_count} 个社区/村数据',
                        'filename': original_filename,
                        'community_count': community_count
                    })
                else:
                    return jsonify({'error': '文件中没有找到有效的社区/村数据'}), 400

            except Exception as e:
                print(f"处理文件时出错：{str(e)}")
                return jsonify({'error': f'文件格式错误：{str(e)}'}), 400
        else:
            return jsonify({'error': '只支持 .xlsx 和 .xls 文件'}), 400

    except Exception as e:
        print(f"上传过程出错：{str(e)}")
        return jsonify({'error': f'上传失败：{str(e)}'}), 500

@app.route('/api/current-file')
def get_current_file():
    """获取当前使用的Excel文件信息"""
    global current_file_data, current_filename

    try:
        if current_file_data is None or current_filename is None:
            return jsonify({
                'filename': '请选择文件',
                'community_count': 0,
                'file_exists': False,
                'message': '请先上传Excel文件'
            })

        # 从内存数据获取信息
        data = load_excel_data()
        community_count = len(data)

        return jsonify({
            'filename': current_filename,
            'community_count': community_count,
            'file_exists': True
        })

    except Exception as e:
        print(f"获取文件信息失败: {str(e)}")
        return jsonify({
            'filename': current_filename or '未知文件',
            'community_count': 0,
            'file_exists': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/community/<community_name>')
def get_community_data(community_name):
    """获取指定社区的数据"""
    data = load_excel_data()
    if community_name in data:
        return jsonify(data[community_name])
    else:
        return jsonify({'error': '未找到该社区数据'}), 404

@app.route('/api/communities')
def get_all_communities():
    """获取所有社区数据"""
    try:
        data = load_excel_data()
        return jsonify(data)
    except Exception as e:
        print(f"获取社区数据失败: {str(e)}")
        return jsonify({})

def open_browser():
    """延迟打开浏览器"""
    time.sleep(1.5)  # 等待Flask启动
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    # 检查是否是打包后的exe
    if getattr(sys, 'frozen', False):
        # 在新线程中打开浏览器
        threading.Timer(1.5, open_browser).start()
        print("正在启动应用...")
        print("浏览器将自动打开访问 http://localhost:5001")
        print("如果浏览器未自动打开，请手动访问上述地址")
        app.run(debug=False, host='127.0.0.1', port=5001, use_reloader=False)
    else:
        # 开发环境
        app.run(debug=True, host='0.0.0.0', port=5001)