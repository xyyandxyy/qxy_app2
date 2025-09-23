from flask import Flask, render_template, jsonify, request, session
import pandas as pd
import json
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 用于session管理

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def load_excel_data(file_path=None):
    """读取Excel文件并返回社区/村数据"""
    try:
        # 如果没有指定文件路径，使用默认文件或session中的文件
        if file_path is None:
            if 'current_excel_file' in session:
                file_path = session['current_excel_file']
            else:
                file_path = 'demo_data.xlsx'

        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return {}

        # 读取Excel文件，将第一行作为header
        df = pd.read_excel(file_path, header=0)

        # 获取实际的列名（第一行数据）
        header_row = df.iloc[0]  # 第一行数据就是列标题

        # 重新读取，跳过第一行，使用第二行开始的数据
        df = pd.read_excel(file_path, header=None, skiprows=1)

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

        return community_data
    except Exception as e:
        print(f"读取Excel文件出错: {e}")
        return {}

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理Excel文件上传"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件被上传'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        if file and allowed_file(file.filename):
            # 安全的文件名
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # 保存文件
            file.save(filepath)

            # 将文件路径保存到session中
            session['current_excel_file'] = filepath

            # 尝试读取文件以验证格式
            try:
                data = load_excel_data(filepath)
                community_count = len(data)

                return jsonify({
                    'success': True,
                    'message': f'文件上传成功！找到 {community_count} 个社区/村数据',
                    'filename': filename,
                    'community_count': community_count
                })
            except Exception as e:
                # 删除无效文件
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': f'文件格式错误：{str(e)}'}), 400
        else:
            return jsonify({'error': '只支持 .xlsx 和 .xls 文件'}), 400

    except Exception as e:
        return jsonify({'error': f'上传失败：{str(e)}'}), 500

@app.route('/api/current-file')
def get_current_file():
    """获取当前使用的Excel文件信息"""
    try:
        current_file = session.get('current_excel_file', 'demo_data.xlsx')
        filename = os.path.basename(current_file)

        if os.path.exists(current_file):
            data = load_excel_data(current_file)
            community_count = len(data)
            return jsonify({
                'filename': filename,
                'community_count': community_count,
                'file_exists': True
            })
        else:
            return jsonify({
                'filename': filename,
                'community_count': 0,
                'file_exists': False
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    data = load_excel_data()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)