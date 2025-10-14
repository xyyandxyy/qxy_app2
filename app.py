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
from difflib import SequenceMatcher

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())  # 用于session管理

# 配置文件处理 - 使用内存模式避免Windows路径问题
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# 全局变量存储当前文件数据
current_file_data = None  # 存储文件数据在内存中
current_filename = None   # 存储原始文件名
community_data_cache = {}  # 缓存处理后的数据

# 列名映射配置
COLUMN_MAPPINGS = {
    '社区名': ['村居', '社区', '村委会', '社区名', '村名', '地址', '所属社区', '社区村居', '村/社区'],
    '姓名': ['姓名', '名字', '人员姓名', '受益人', '人员', '户主'],
    '年龄': ['年龄', '周岁', '岁数', '周岁年龄', '实际年龄'],
    '金额': ['金额', '补贴', '发放金额', '数额', '补助金额', '津贴'],
    '性别': ['性别', '男女'],
    '电话': ['联系电话', '电话', '手机', '联系方式', '手机号'],
    '身份证': ['身份证号', '身份证', '证件号', '身份证号码']
}

# 社区村名关键词
COMMUNITY_KEYWORDS = ['社区', '村', '村委会', '居委会']

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def similarity(a, b):
    """计算字符串相似度"""
    return SequenceMatcher(None, a, b).ratio()

def find_best_column_match(column_name, candidates):
    """在候选列名中找到最佳匹配"""
    if not candidates:
        return None

    # 精确匹配
    for candidate in candidates:
        if column_name in candidate:
            return candidate

    # 相似度匹配
    best_match = None
    best_score = 0
    for candidate in candidates:
        score = similarity(column_name, candidate)
        if score > best_score and score > 0.6:  # 相似度阈值
            best_score = score
            best_match = candidate

    return best_match

def detect_header_row(df):
    """智能检测表头行位置"""
    # 检查前5行，寻找包含最多关键词的行
    key_indicators = ['姓名', '村居', '社区', '村', '年龄', '金额', '电话', '身份证']

    best_row = 0
    best_score = 0

    for i in range(min(5, len(df))):
        row = df.iloc[i]
        score = 0
        for cell in row:
            cell_str = str(cell).strip()
            for indicator in key_indicators:
                if indicator in cell_str:
                    score += 1

        if score > best_score:
            best_score = score
            best_row = i

    return best_row if best_score > 0 else 0

def find_community_column(df):
    """智能寻找社区名所在的列"""
    # 方法1: 通过列名匹配
    community_column_candidates = COLUMN_MAPPINGS['社区名']

    for i, col_name in enumerate(df.columns):
        col_name_str = str(col_name).strip()
        for candidate in community_column_candidates:
            if candidate in col_name_str:
                print(f"[INFO] 通过列名找到社区列: 第{i}列 '{col_name_str}'")
                return i

    # 方法2: 通过内容匹配（检查每列包含社区/村的比例）
    best_column = -1
    best_ratio = 0

    for i in range(min(5, len(df.columns))):  # 只检查前5列
        community_count = 0
        total_count = 0

        for index, row in df.iterrows():
            if index >= 20:  # 只检查前20行
                break

            cell_value = str(row.iloc[i]).strip()
            if cell_value and cell_value != 'nan' and cell_value != '':
                total_count += 1
                for keyword in COMMUNITY_KEYWORDS:
                    if keyword in cell_value:
                        community_count += 1
                        break

        if total_count > 0:
            ratio = community_count / total_count
            if ratio > best_ratio and ratio > 0.3:  # 至少30%的行包含社区/村关键词
                best_ratio = ratio
                best_column = i

    if best_column >= 0:
        print(f"[INFO] 通过内容匹配找到社区列: 第{best_column}列, 匹配率: {best_ratio:.2%}")
        return best_column

    print(f"[WARNING] 未能自动识别社区列，使用第1列作为默认")
    return 1  # 默认使用第二列

def extract_community_name(text):
    """提取并标准化社区名称"""
    if not text or text == 'nan' or pd.isna(text):
        return None

    text = str(text).strip()

    # 使用正则表达式提取社区/村名称
    # 匹配模式：XX社区、XX村、XX村委会、XX居委会等
    patterns = [
        r'([^街道镇]*(?:社区|村委会|居委会|村))',  # 提取社区/村名称
        r'.*?([^\s]*(?:社区|村))',  # 更宽松的匹配
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            community_name = match.group(1).strip()
            # 清理前缀
            community_name = re.sub(r'^[^a-zA-Z\u4e00-\u9fff]*', '', community_name)
            if community_name:
                return community_name

    # 如果包含关键词但正则匹配失败，直接返回原文本
    for keyword in COMMUNITY_KEYWORDS:
        if keyword in text:
            return text

    return None

def smart_column_mapping(df):
    """智能列映射"""
    column_map = {}

    for standard_name, candidates in COLUMN_MAPPINGS.items():
        best_match = find_best_column_match(standard_name, [str(col) for col in df.columns])
        if best_match:
            # 找到列的索引
            for i, col in enumerate(df.columns):
                if str(col) == best_match:
                    column_map[standard_name] = i
                    break

    return column_map

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
    """读取Excel文件并返回社区/村数据 - 增强版"""
    global current_file_data, current_filename, community_data_cache

    try:
        # 如果没有指定文件数据，返回空字典
        if file_data is None:
            return {}

        print(f"[INFO] 开始智能解析Excel文件: {filename}")

        # 从内存中的字节数据读取Excel - 支持多种格式
        try:
            if isinstance(file_data, bytes):
                # 尝试读取为xlsx
                try:
                    df_raw = pd.read_excel(io.BytesIO(file_data), header=None)
                except Exception as e:
                    print(f"[INFO] xlsx读取失败，尝试xls格式: {e}")
                    # 尝试读取为xls
                    df_raw = pd.read_excel(io.BytesIO(file_data), header=None, engine='xlrd')
            else:
                print(f"[ERROR] 文件数据格式不正确: {type(file_data)}")
                return {}
        except Exception as e:
            print(f"[ERROR] 文件读取失败: {e}")
            return {}

        print(f"[INFO] 原始数据形状: {df_raw.shape}")

        # 智能检测表头行位置
        header_row_index = detect_header_row(df_raw)
        print(f"[INFO] 检测到表头行位置: 第{header_row_index + 1}行")

        # 使用检测到的表头行重新读取数据
        if isinstance(file_data, bytes):
            try:
                df = pd.read_excel(io.BytesIO(file_data), header=header_row_index)
            except:
                df = pd.read_excel(io.BytesIO(file_data), header=header_row_index, engine='xlrd')

        # 处理列名，去除空格和特殊字符
        df.columns = [str(col).strip() for col in df.columns]
        print(f"[INFO] 处理后数据形状: {df.shape}")
        print(f"[INFO] 列名: {df.columns.tolist()}")

        # 智能寻找社区名所在的列
        community_col_index = find_community_column(df)

        # 智能列映射
        column_mapping = smart_column_mapping(df)
        print(f"[INFO] 智能列映射结果: {column_mapping}")

        # 筛选包含社区/村的数据行
        community_data = {}
        processed_count = 0
        skipped_count = 0

        for index, row in df.iterrows():
            # 获取社区名称
            community_cell = row.iloc[community_col_index] if community_col_index < len(row) else None
            community_name = extract_community_name(community_cell)

            if community_name:
                processed_count += 1
                print(f"[INFO] 处理社区: {community_name}")

                # 获取列名
                column_names = df.columns.tolist()

                # 处理各列数据
                community_info = {
                    'name': community_name,
                    'columns': {},  # 存储列名和数据的映射
                    'row_index': index,  # 记录原始行号
                    'detected_column_index': community_col_index  # 记录检测到的社区列索引
                }

                # 遍历所有列
                for i, col_name in enumerate(column_names):
                    if i < len(row):
                        col_raw = process_data_value(row.iloc[i])
                        people_count = extract_people_count(col_raw)

                        community_info['columns'][col_name] = {
                            'raw_data': col_raw,
                            'people_count': people_count,
                            'column_index': i
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

                # 添加智能映射的字段
                community_info['smart_mapping'] = {}
                for field_name, col_index in column_mapping.items():
                    if col_index < len(row):
                        community_info['smart_mapping'][field_name] = {
                            'raw_data': process_data_value(row.iloc[col_index]),
                            'column_index': col_index,
                            'column_name': column_names[col_index] if col_index < len(column_names) else f'Column_{col_index}'
                        }

                community_data[community_name] = community_info
            else:
                skipped_count += 1

        print(f"[INFO] 处理完成，找到 {len(community_data)} 个社区/村")
        print(f"[INFO] 处理了 {processed_count} 行，跳过了 {skipped_count} 行")

        # 数据质量检测
        data_quality_report = {
            'total_rows': len(df),
            'community_rows': processed_count,
            'skipped_rows': skipped_count,
            'detection_rate': processed_count / len(df) if len(df) > 0 else 0,
            'community_column_index': community_col_index,
            'header_row_index': header_row_index,
            'column_mapping': column_mapping
        }

        print(f"[INFO] 数据质量报告: 检测率 {data_quality_report['detection_rate']:.2%}")

        # 如果检测率过低，给出警告
        if data_quality_report['detection_rate'] < 0.3:
            print(f"[WARNING] 社区/村检测率较低({data_quality_report['detection_rate']:.2%})，请检查文件格式")

        return community_data

    except Exception as e:
        print(f"[ERROR] 读取Excel文件出错: {e}")
        import traceback
        print(f"[ERROR] 错误堆栈: {traceback.format_exc()}")
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
            print(f"[INFO] 开始处理文件：{original_filename}")
        else:
            return jsonify({'error': '只支持 .xlsx 和 .xls 文件'}), 400

        try:
            # 直接读取文件内容到内存
            file_data = file.read()
            print(f"[INFO] 文件读取成功，大小：{len(file_data)} 字节")

            # 存储文件数据和文件名到全局变量
            current_file_data = file_data
            current_filename = original_filename

            # 直接从内存数据加载并分析文件
            data = load_excel_data(file_data=file_data, filename=original_filename)
            community_count = len(data)

            if community_count > 0:
                print(f"[INFO] 文件处理成功：{original_filename}，找到 {community_count} 个社区/村")
                response_data = {
                    'success': True,
                    'message': f'文件上传成功！找到 {community_count} 个社区/村数据',
                    'filename': original_filename,
                    'community_count': community_count
                }
                return jsonify(response_data)
            else:
                return jsonify({'error': '文件中没有找到有效的社区/村数据'}), 400

        except Exception as e:
            print(f"[ERROR] 处理文件时出错：{str(e)}")
            return jsonify({'error': f'文件格式错误：{str(e)}'}), 400

    except Exception as e:
        print(f"[ERROR] 上传过程出错：{str(e)}")
        return jsonify({'error': f'上传失败：{str(e)}'}), 500

@app.route('/api/current-file')
def get_current_file():
    """获取当前使用的Excel文件信息"""
    global current_file_data, current_filename

    try:
        if current_file_data is None or current_filename is None:
            response_data = {
                'filename': '请选择文件',
                'community_count': 0,
                'file_exists': False,
                'message': '请先上传Excel文件'
            }
            return jsonify(response_data)

        # 从内存数据获取信息
        data = load_excel_data(file_data=current_file_data, filename=current_filename)
        community_count = len(data)

        response_data = {
            'filename': current_filename,
            'community_count': community_count,
            'file_exists': True
        }
        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] 获取文件信息失败: {str(e)}")
        error_response = {
            'filename': current_filename or '未知文件',
            'community_count': 0,
            'file_exists': False,
            'error': str(e)
        }
        return jsonify(error_response), 500

@app.route('/api/data-quality')
def get_data_quality():
    """获取数据质量报告"""
    try:
        if current_file_data is None:
            return jsonify({'error': '没有上传文件'}), 400

        # 重新分析文件以获取详细的质量报告
        file_data = current_file_data
        filename = current_filename

        # 读取原始数据
        try:
            df_raw = pd.read_excel(io.BytesIO(file_data), header=None)
        except:
            df_raw = pd.read_excel(io.BytesIO(file_data), header=None, engine='xlrd')

        # 智能检测
        header_row_index = detect_header_row(df_raw)

        try:
            df = pd.read_excel(io.BytesIO(file_data), header=header_row_index)
        except:
            df = pd.read_excel(io.BytesIO(file_data), header=header_row_index, engine='xlrd')

        df.columns = [str(col).strip() for col in df.columns]
        community_col_index = find_community_column(df)
        column_mapping = smart_column_mapping(df)

        # 分析每行数据
        rows_analysis = []
        community_count = 0

        for index, row in df.iterrows():
            community_cell = row.iloc[community_col_index] if community_col_index < len(row) else None
            community_name = extract_community_name(community_cell)

            row_info = {
                'row_index': index,
                'community_cell_value': str(community_cell) if community_cell is not None else '',
                'extracted_community_name': community_name,
                'is_community_row': community_name is not None
            }

            if community_name:
                community_count += 1

            rows_analysis.append(row_info)

        quality_report = {
            'filename': filename,
            'total_rows': len(df),
            'header_row_index': header_row_index,
            'community_column_index': community_col_index,
            'community_column_name': df.columns[community_col_index] if community_col_index < len(df.columns) else f'Column_{community_col_index}',
            'detected_communities': community_count,
            'detection_rate': community_count / len(df) if len(df) > 0 else 0,
            'column_mapping': column_mapping,
            'columns': df.columns.tolist(),
            'rows_analysis': rows_analysis[:10],  # 只返回前10行的详细分析
            'file_shape': df.shape
        }

        return jsonify(quality_report)

    except Exception as e:
        print(f"[ERROR] 获取数据质量报告失败: {str(e)}")
        return jsonify({'error': f'获取数据质量报告失败：{str(e)}'}), 500

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/community/<community_name>')
def get_community_data(community_name):
    """获取指定社区的数据"""
    try:
        data = load_excel_data(file_data=current_file_data, filename=current_filename)

        if community_name in data:
            community_data = data[community_name]
            return jsonify(community_data)
        else:
            return jsonify({'error': '未找到该社区数据'}), 404
    except Exception as e:
        print(f"[ERROR] 获取社区数据失败: {str(e)}")
        return jsonify({'error': f'获取社区数据失败：{str(e)}'}), 500

@app.route('/api/communities')
def get_all_communities():
    """获取所有社区数据"""
    try:
        data = load_excel_data(file_data=current_file_data, filename=current_filename)
        return jsonify(data)
    except Exception as e:
        print(f"[ERROR] 获取社区数据失败: {str(e)}")
        return jsonify({})

def open_browser():
    """延迟打开浏览器"""
    time.sleep(1.5)  # 等待Flask启动
    print(f"[INFO] 正在打开浏览器访问 http://localhost:5001")
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    print(f"[INFO] 应用启动，等待用户上传Excel文件")

    # 检查是否是打包后的exe
    if getattr(sys, 'frozen', False):
        print(f"[INFO] 检测到打包环境，以生产模式运行")
        # 在新线程中打开浏览器
        threading.Timer(1.5, open_browser).start()
        print(f"[INFO] 正在启动应用...")
        print(f"[INFO] 浏览器将自动打开访问 http://localhost:5001")
        print(f"[INFO] 如果浏览器未自动打开，请手动访问上述地址")
        app.run(debug=False, host='127.0.0.1', port=5001, use_reloader=False)
    else:
        print(f"[INFO] 检测到开发环境，以调试模式运行")
        print(f"[INFO] 应用将在 http://0.0.0.0:5001 上运行")
        # 开发环境
        app.run(debug=True, host='0.0.0.0', port=5001)