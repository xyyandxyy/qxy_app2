# 社区地图信息查询系统

## 项目说明
这是一个基于Flask和SVG地图的社区信息查询系统，可以通过点击地图上的社区区域来查看相应的Excel数据。

## 项目结构
```
qxy_app2/
├── app.py                 # Flask主应用文件
├── demo_data.xlsx         # 社区数据Excel文件
├── 地图线稿.svg           # SVG地图文件
├── static/
│   └── 地图线稿.svg       # 静态资源SVG文件
└── templates/
    └── index.html         # 主页面模板
```

## 功能特点
1. **交互式SVG地图**: 可点击的社区区域，支持鼠标悬停和选中状态
2. **Excel数据读取**: 自动读取demo_data.xlsx中以"社区"结尾的行数据
3. **实时信息显示**: 点击社区后右侧面板显示详细信息
4. **响应式设计**: 适配不同屏幕尺寸

## 使用方法
1. 启动应用：
   ```bash
   python3 app.py
   ```

2. 在浏览器中访问：
   ```
   http://localhost:5001
   ```

3. 点击地图上的社区区域查看信息

## API接口
- `GET /` - 主页面
- `GET /api/communities` - 获取所有社区数据
- `GET /api/community/<社区名>` - 获取指定社区数据

## 技术栈
- **后端**: Python Flask, pandas, openpyxl
- **前端**: HTML5, CSS3, JavaScript
- **数据**: Excel表格, SVG矢量图

## 注意事项
- 确保demo_data.xlsx文件与app.py在同一目录
- SVG文件需要包含带有data-name属性的社区组元素
- Excel第一列应包含以"社区"结尾的社区名称