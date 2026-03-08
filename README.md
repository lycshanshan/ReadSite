# 📚 ReadSite - 在线小说阅读系统

基于 Django + DRF 开发的轻量级在线小说阅读平台。支持小说上传、分卷阅读、书架管理及全站搜索。

## ✨ 功能特性

- **阅读体验**：支持分卷章节阅读，自动记录阅读进度（书签）。
- **用户中心**：注册/登录，个人书架管理，积分系统。
- **内容管理**：后台批量上传小说（TXT解析），插图画廊模式。
- **API 支持**：提供完整的 RESTful API，集成 Swagger 自动文档。
- **搜索功能**：支持书名、作者、描述的模糊搜索。

## 🛠️ 技术栈

- **后端框架**: Django 6.x
- **API 框架**: Django REST Framework
- **数据库**: SQLite
- **文档工具**: drf-spectacular (Swagger UI)

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/lycshanshan/novel-reader.git
cd novel-reader
```

### 2. 创建并激活虚拟环境
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
在项目根目录创建 `.env` 文件，填入以下内容：
```env
DEBUG=True
SECRET_KEY=随便写一个复杂的字符串
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 5. 初始化数据库并运行
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

访问 `http://127.0.0.1:8000` 即可开始阅读。

## 📖 API 文档

启动服务后，访问以下地址查看交互式接口文档：
`http://127.0.0.1:8000/api/docs/`