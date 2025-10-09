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
    print(f"[DEBUG] extract_people_count 输入: {repr(text)}")
    
    if not text or text == 'nan' or pd.isna(text):
        print(f"[DEBUG] extract_people_count 空值或NaN，返回0")
        return 0

    text = str(text)
    print(f"[DEBUG] extract_people_count 转换后文本: {repr(text)}")
    
    # 使用正则表达式匹配"x人"模式
    pattern = r'(\d+)人'
    match = re.search(pattern, text)
    if match:
        result = int(match.group(1))
        print(f"[DEBUG] extract_people_count 匹配成功，提取人数: {result}")
        return result
    
    print(f"[DEBUG] extract_people_count 未匹配到人数模式，返回0")
    return 0

def process_data_value(value):
    """处理数据值，空值默认为0"""
    print(f"[DEBUG] process_data_value 输入: {repr(value)}")
    
    if pd.isna(value) or value == '' or str(value).strip() == '':
        print(f"[DEBUG] process_data_value 检测到空值，返回'0'")
        return '0'
    
    result = str(value).strip()
    print(f"[DEBUG] process_data_value 处理结果: {repr(result)}")
    return result

def load_excel_data(file_data=None, filename=None):
    """读取Excel文件并返回社区/村数据"""
    global current_file_data, current_filename, community_data_cache
    
    print(f"[DEBUG] load_excel_data 开始执行")
    print(f"[DEBUG] load_excel_data 参数 - file_data: {type(file_data)}, filename: {filename}")

    try:
        # 如果没有指定文件数据，使用全局缓存
        if file_data is None:
            print(f"[DEBUG] load_excel_data 使用全局文件数据")
            if current_file_data is None:
                print(f"[DEBUG] load_excel_data 没有全局文件数据，返回空字典")
                # 没有上传文件，返回空数据
                return {}
            file_data = current_file_data
            filename = current_filename
            print(f"[DEBUG] load_excel_data 使用全局数据: {filename}, 大小: {len(file_data) if file_data else 0} 字节")

        # 检查缓存
        cache_key = f"{filename}_{len(file_data) if file_data else 0}"
        print(f"[DEBUG] load_excel_data 缓存键: {cache_key}")
        if cache_key in community_data_cache:
            print(f"[DEBUG] load_excel_data 使用缓存数据: {filename}")
            return community_data_cache[cache_key]

        print(f"[DEBUG] load_excel_data 从内存数据处理Excel文件: {filename}")

        # 从内存中的字节数据读取Excel
        print(f"[DEBUG] load_excel_data 开始读取Excel数据")
        if isinstance(file_data, bytes):
            print(f"[DEBUG] load_excel_data 文件数据是bytes类型，大小: {len(file_data)} 字节")
            df = pd.read_excel(io.BytesIO(file_data), header=0)
            print(f"[DEBUG] load_excel_data 第一次读取成功，DataFrame形状: {df.shape}")
        else:
            print(f"[ERROR] load_excel_data 文件数据格式不正确: {type(file_data)}")
            return {}

        # 获取实际的列名（第一行数据）
        header_row = df.iloc[0]  # 第一行数据就是列标题
        print(f"[DEBUG] load_excel_data 获取列标题: {header_row.tolist()}")

        # 重新读取，跳过第一行，使用第二行开始的数据
        if isinstance(file_data, bytes):
            print(f"[DEBUG] load_excel_data 重新读取数据，跳过第一行")
            df = pd.read_excel(io.BytesIO(file_data), header=None, skiprows=1)
            print(f"[DEBUG] load_excel_data 重新读取成功，DataFrame形状: {df.shape}")
        else:
            print(f"[ERROR] load_excel_data 重新读取时文件数据格式不正确")
            return {}

        # 设置列名为第一行的内容
        df.columns = header_row.tolist()
        print(f"[DEBUG] load_excel_data 设置列名完成: {df.columns.tolist()}")

        # 筛选第一列包含"社区"或"村"的行
        print(f"[DEBUG] load_excel_data 开始筛选社区/村数据，总行数: {len(df)}")
        community_data = {}
        community_count = 0
        
        for index, row in df.iterrows():
            community_name = str(row.iloc[0]).strip()
            print(f"[DEBUG] load_excel_data 检查第{index}行: {repr(community_name)}")

            # 获取列名
            column_names = df.columns.tolist()

            if '社区' in community_name or '村' in community_name:
                community_count += 1
                print(f"[DEBUG] load_excel_data 找到社区/村 #{community_count}: {community_name}")
                print(f"[DEBUG] load_excel_data 社区 {community_name} 的列名: {column_names}")

                # 处理各列数据
                community_info = {
                    'name': community_name,
                    'columns': {}  # 存储列名和数据的映射
                }

                # 遍历所有列（除了第一列名称列）
                print(f"[DEBUG] load_excel_data 开始处理社区 {community_name} 的数据列")
                for i, col_name in enumerate(column_names[1:], 1):
                    if i < len(row):
                        print(f"[DEBUG] load_excel_data 处理列 {i}: {col_name}")
                        col_raw = process_data_value(row.iloc[i])
                        people_count = extract_people_count(col_raw)
                        print(f"[DEBUG] load_excel_data 列 {col_name} 原始数据: {repr(col_raw)}, 提取人数: {people_count}")

                        community_info['columns'][col_name] = {
                            'raw_data': col_raw,
                            'people_count': people_count
                        }
                    else:
                        print(f"[DEBUG] load_excel_data 列索引 {i} 超出行长度 {len(row)}")
            else:
                print(f"[DEBUG] load_excel_data 第{index}行不是社区/村: {repr(community_name)}")
                # 跳过非社区/村行
                continue

            # 保持向后兼容性，仍然提供原来的字段
            print(f"[DEBUG] load_excel_data 为社区 {community_name} 设置向后兼容字段")
            if len(column_names) > 1:
                community_info['column2'] = community_info['columns'].get(column_names[1], {}).get('raw_data', '0')
                community_info['people_count_col2'] = community_info['columns'].get(column_names[1], {}).get('people_count', 0)
                print(f"[DEBUG] load_excel_data column2: {community_info['column2']}, people_count_col2: {community_info['people_count_col2']}")
            if len(column_names) > 2:
                community_info['column3'] = community_info['columns'].get(column_names[2], {}).get('raw_data', '0')
                community_info['people_count_col3'] = community_info['columns'].get(column_names[2], {}).get('people_count', 0)
                print(f"[DEBUG] load_excel_data column3: {community_info['column3']}, people_count_col3: {community_info['people_count_col3']}")
            if len(column_names) > 3:
                community_info['column4'] = community_info['columns'].get(column_names[3], {}).get('raw_data', '0')
                community_info['people_count_col4'] = community_info['columns'].get(column_names[3], {}).get('people_count', 0)
                print(f"[DEBUG] load_excel_data column4: {community_info['column4']}, people_count_col4: {community_info['people_count_col4']}")
            if len(column_names) > 4:
                community_info['column5'] = community_info['columns'].get(column_names[4], {}).get('raw_data', '0')
                community_info['people_count_col5'] = community_info['columns'].get(column_names[4], {}).get('people_count', 0)
                print(f"[DEBUG] load_excel_data column5: {community_info['column5']}, people_count_col5: {community_info['people_count_col5']}")

            community_data[community_name] = community_info
            print(f"[DEBUG] load_excel_data 社区 {community_name} 数据处理完成")
            
            # 每处理10行输出一次进度
            if (index + 1) % 10 == 0:
                print(f"[DEBUG] load_excel_data 已处理 {index + 1}/{len(df)} 行")

        # 缓存结果
        community_data_cache[cache_key] = community_data
        print(f"[DEBUG] load_excel_data 数据已缓存，缓存键: {cache_key}")
        print(f"[INFO] load_excel_data 处理完成，找到 {len(community_data)} 个社区/村")
        
        # 输出每个社区的基本信息
        for name, info in community_data.items():
            print(f"[INFO] load_excel_data 社区: {name}, 列数: {len(info.get('columns', {}))}")

        return community_data
    except Exception as e:
        print(f"[ERROR] load_excel_data 读取Excel文件出错: {e}")
        print(f"[ERROR] load_excel_data 错误类型: {type(e).__name__}")
        import traceback
        print(f"[ERROR] load_excel_data 错误堆栈: {traceback.format_exc()}")
        return {}

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理Excel文件上传 - 使用内存模式"""
    global current_file_data, current_filename
    
    print(f"[INFO] upload_file API调用开始")
    print(f"[DEBUG] upload_file 请求方法: {request.method}")
    print(f"[DEBUG] upload_file 请求文件: {list(request.files.keys())}")

    try:
        if 'file' not in request.files:
            print(f"[ERROR] upload_file 没有文件被上传")
            return jsonify({'error': '没有文件被上传'}), 400

        file = request.files['file']
        print(f"[DEBUG] upload_file 获取到文件对象: {file}")
        
        if file.filename == '':
            print(f"[ERROR] upload_file 没有选择文件")
            return jsonify({'error': '没有选择文件'}), 400

        # 检查文件大小，限制为100MB
        print(f"[DEBUG] upload_file 开始检查文件大小")
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        print(f"[DEBUG] upload_file 文件大小: {file_size} 字节")

        if file_size > app.config['MAX_CONTENT_LENGTH']:
            print(f"[ERROR] upload_file 文件太大: {file_size} > {app.config['MAX_CONTENT_LENGTH']}")
            return jsonify({'error': '文件太大，请上传不超过100MB的文件'}), 400

        if file and allowed_file(file.filename):
            # 获取原始文件名
            original_filename = file.filename
            print(f"[INFO] upload_file 开始处理文件：{original_filename}")
            print(f"[DEBUG] upload_file 文件类型检查通过")
        else:
            print(f"[ERROR] upload_file 文件类型不支持: {file.filename if file else 'None'}")
            return jsonify({'error': '只支持 .xlsx 和 .xls 文件'}), 400

        try:
            # 直接读取文件内容到内存
            print(f"[DEBUG] upload_file 开始读取文件内容到内存")
            file_data = file.read()
            print(f"[INFO] upload_file 文件读取到内存成功，大小：{len(file_data)} 字节")

            # 存储文件数据和文件名到全局变量
            print(f"[DEBUG] upload_file 存储文件数据到全局变量")
            current_file_data = file_data
            current_filename = original_filename
            print(f"[DEBUG] upload_file 全局变量已更新: current_filename={current_filename}")

            # 直接从内存数据加载并分析文件
            print(f"[DEBUG] upload_file 开始调用load_excel_data处理文件")
            data = load_excel_data(file_data=file_data, filename=original_filename)
            community_count = len(data)
            print(f"[DEBUG] upload_file load_excel_data返回数据，社区数量: {community_count}")

            if community_count > 0:
                print(f"[INFO] upload_file 文件处理成功：{original_filename}，找到 {community_count} 个社区/村")
                response_data = {
                    'success': True,
                    'message': f'文件上传成功！找到 {community_count} 个社区/村数据',
                    'filename': original_filename,
                    'community_count': community_count
                }
                print(f"[DEBUG] upload_file 返回成功响应: {response_data}")
                return jsonify(response_data)
            else:
                print(f"[ERROR] upload_file 文件中没有找到有效的社区/村数据")
                return jsonify({'error': '文件中没有找到有效的社区/村数据'}), 400

        except Exception as e:
            print(f"[ERROR] upload_file 处理文件时出错：{str(e)}")
            print(f"[ERROR] upload_file 错误类型: {type(e).__name__}")
            import traceback
            print(f"[ERROR] upload_file 错误堆栈: {traceback.format_exc()}")
            return jsonify({'error': f'文件格式错误：{str(e)}'}), 400

    except Exception as e:
        print(f"[ERROR] upload_file 上传过程出错：{str(e)}")
        print(f"[ERROR] upload_file 错误类型: {type(e).__name__}")
        import traceback
        print(f"[ERROR] upload_file 错误堆栈: {traceback.format_exc()}")
        return jsonify({'error': f'上传失败：{str(e)}'}), 500

@app.route('/api/current-file')
def get_current_file():
    """获取当前使用的Excel文件信息"""
    global current_file_data, current_filename
    
    print(f"[INFO] get_current_file API调用开始")
    print(f"[DEBUG] get_current_file 当前文件状态: current_file_data={current_file_data is not None}, current_filename={current_filename}")

    try:
        if current_file_data is None or current_filename is None:
            print(f"[DEBUG] get_current_file 没有当前文件，返回默认信息")
            response_data = {
                'filename': '请选择文件',
                'community_count': 0,
                'file_exists': False,
                'message': '请先上传Excel文件'
            }
            print(f"[DEBUG] get_current_file 返回响应: {response_data}")
            return jsonify(response_data)

        # 从内存数据获取信息
        print(f"[DEBUG] get_current_file 调用load_excel_data获取数据")
        data = load_excel_data()
        community_count = len(data)
        print(f"[DEBUG] get_current_file 获取到社区数量: {community_count}")

        response_data = {
            'filename': current_filename,
            'community_count': community_count,
            'file_exists': True
        }
        print(f"[DEBUG] get_current_file 返回成功响应: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] get_current_file 获取文件信息失败: {str(e)}")
        print(f"[ERROR] get_current_file 错误类型: {type(e).__name__}")
        import traceback
        print(f"[ERROR] get_current_file 错误堆栈: {traceback.format_exc()}")
        error_response = {
            'filename': current_filename or '未知文件',
            'community_count': 0,
            'file_exists': False,
            'error': str(e)
        }
        print(f"[DEBUG] get_current_file 返回错误响应: {error_response}")
        return jsonify(error_response), 500

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/community/<community_name>')
def get_community_data(community_name):
    """获取指定社区的数据"""
    print(f"[INFO] get_community_data API调用开始，社区名称: {community_name}")
    
    try:
        data = load_excel_data()
        print(f"[DEBUG] get_community_data 获取到数据，社区总数: {len(data)}")
        print(f"[DEBUG] get_community_data 可用社区列表: {list(data.keys())}")
        
        if community_name in data:
            print(f"[DEBUG] get_community_data 找到社区数据: {community_name}")
            community_data = data[community_name]
            print(f"[DEBUG] get_community_data 社区数据列数: {len(community_data.get('columns', {}))}")
            return jsonify(community_data)
        else:
            print(f"[ERROR] get_community_data 未找到社区: {community_name}")
            return jsonify({'error': '未找到该社区数据'}), 404
    except Exception as e:
        print(f"[ERROR] get_community_data 获取社区数据失败: {str(e)}")
        print(f"[ERROR] get_community_data 错误类型: {type(e).__name__}")
        import traceback
        print(f"[ERROR] get_community_data 错误堆栈: {traceback.format_exc()}")
        return jsonify({'error': f'获取社区数据失败：{str(e)}'}), 500

@app.route('/api/communities')
def get_all_communities():
    """获取所有社区数据"""
    print(f"[INFO] get_all_communities API调用开始")
    
    try:
        data = load_excel_data()
        community_count = len(data)
        print(f"[DEBUG] get_all_communities 获取到所有社区数据，数量: {community_count}")
        print(f"[DEBUG] get_all_communities 社区列表: {list(data.keys())}")
        return jsonify(data)
    except Exception as e:
        print(f"[ERROR] get_all_communities 获取社区数据失败: {str(e)}")
        print(f"[ERROR] get_all_communities 错误类型: {type(e).__name__}")
        import traceback
        print(f"[ERROR] get_all_communities 错误堆栈: {traceback.format_exc()}")
        return jsonify({})

def open_browser():
    """延迟打开浏览器"""
    print(f"[INFO] open_browser 等待Flask启动...")
    time.sleep(1.5)  # 等待Flask启动
    print(f"[INFO] open_browser 正在打开浏览器访问 http://localhost:5001")
    webbrowser.open('http://localhost:5001')
    print(f"[INFO] open_browser 浏览器打开完成")

def load_default_excel():
    """启动时加载默认的test_data.xlsx文件"""
    global current_file_data, current_filename

    default_file_path = 'test_data.xlsx'
    if os.path.exists(default_file_path):
        print(f"[INFO] 找到默认Excel文件: {default_file_path}")
        try:
            with open(default_file_path, 'rb') as f:
                current_file_data = f.read()
                current_filename = default_file_path
                print(f"[INFO] 默认Excel文件加载成功: {default_file_path}")

                # 验证数据
                data = load_excel_data()
                print(f"[INFO] 默认文件包含 {len(data)} 个社区/村数据")
        except Exception as e:
            print(f"[ERROR] 加载默认Excel文件失败: {e}")
    else:
        print(f"[INFO] 未找到默认Excel文件: {default_file_path}")

if __name__ == '__main__':
    print(f"[INFO] 应用启动开始")
    print(f"[DEBUG] Python版本: {sys.version}")
    print(f"[DEBUG] 工作目录: {os.getcwd()}")

    # 加载默认Excel文件
    load_default_excel()
    
    # 检查是否是打包后的exe
    if getattr(sys, 'frozen', False):
        print(f"[INFO] 检测到打包环境，以生产模式运行")
        # 在新线程中打开浏览器
        print(f"[DEBUG] 启动浏览器打开线程")
        threading.Timer(1.5, open_browser).start()
        print(f"[INFO] 正在启动应用...")
        print(f"[INFO] 浏览器将自动打开访问 http://localhost:5001")
        print(f"[INFO] 如果浏览器未自动打开，请手动访问上述地址")
        print(f"[INFO] 应用将在 http://127.0.0.1:5001 上运行")
        app.run(debug=False, host='127.0.0.1', port=5001, use_reloader=False)
    else:
        print(f"[INFO] 检测到开发环境，以调试模式运行")
        print(f"[INFO] 应用将在 http://0.0.0.0:5001 上运行")
        print(f"[INFO] 调试模式已启用，代码变更将自动重载")
        # 开发环境
        app.run(debug=True, host='0.0.0.0', port=5001)