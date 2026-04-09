# 📚 ReadSite - 在线小说阅读系统

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org)
[![Django](https://img.shields.io/badge/Django-6.x-092E20.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14+-red.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

基于 Django + Django REST Framework 开发的轻量级在线小说阅读平台。支持小说阅读、分卷管理、插图画廊、积分签到系统，并提供完善的后台 RESTful API 与 Swagger 交互文档。

## ✨ 核心特性

- **📖 沉浸式阅读体验**：支持章节按分卷展示，自动记录用户阅读进度，支持章节书签。
- **📦 完善的下载系统**：按字数和插图数计算积分，支持打包下载纯文本 (TXT) 或 图文混合包 (ZIP)。
- **🎮 用户中心与积分机制**：内置每日签到、经验值与会员等级（LV0-LV6）系统。下载小说消耗积分。
- **🖼️ 插图画廊模式**：支持为特定分卷上传插图，并提供独立的画廊模式沉浸浏览。
- **📚 书单系统**：管理员可创建书单（BookGroup）归类书籍，用户可在书库按书单筛选浏览。
- **⭐ 评分系统**：用户可为书籍打分（1-10），书籍详情页实时显示平均评分与评分人数。
- **⚙️ 全局系统控制**：基于单例模式的系统设置，支持后台切换注册模式（完全开放 / 邀请码注册 / 关闭注册）。
- **🛠️ 后台管理 API**：普通管理员可管理自己上传的书籍，超级管理员拥有全部权限。
- **🔍 智能检索**：支持对书名、作者、标签、书单的多维度搜索，支持正则表达式和多关键词模糊搜索。

---

## 🛠️ 技术栈

- **后端框架**: Django 6.x
- **API 框架**: Django REST Framework (DRF)
- **数据库**: MySQL / SQLite3
- **API 文档**: `drf-spectacular` (Swagger UI)
- **环境变量**: `python-dotenv`

---

## 📁 数据库模型

- **Book / Chapter / Illustration**: 书籍元数据、章节内容与插图，利用 Django Signals 自动统计总字数与插图总数。
- **Tag**: 标签，存储当前存在的所有标签，与书籍绑定（每本书最多 6 个标签）。
- **BookGroup**: 书单，管理员创建的书籍分类合集，支持按书单筛选书库。
- **UserProgress / Bookshelf / Bookmark**: 记录用户当前阅读到了哪一章，以及用户的个人书架和收藏夹。
- **UserPoints**: 扩展内置 User，管理用户的推荐 (Reco)、积分 (Point)、经验值 (Exp) 和等级。
- **BookRecoLog**: 推荐记录，记录每名用户当天对某本书的推荐次数（每天每本最多 4 次）。
- **BookRating**: 评分记录，记录每名用户对某本书的评分（1-10），Signals 自动更新均分和评分数。
- **GlobalSettings**: 全局设置，保证数据库中只有一条记录，控制整站级别的开关。
- **StaffApplication**: 员工申请，普通用户可以申请成为网站维护者 (Staff)。

---

## ⚡ 快速开始

推荐使用自动化脚本完成环境搭建，脚本将自动检测 Python、创建虚拟环境、安装依赖、初始化数据库，并在最后启动服务器或生成部署配置。

> ⚠ 警告：目前`setup.bat`, `setup.py`, `setup.sh`, `dev.sh`, `update.sh`尚未经过完全测试，如使用中出现问题，请提交issue反馈，感谢理解！

### 0. 环境准备

开始安装前，请先自行安装 Python 和 MySQL：
- [Python 3.12.x](https://www.python.org/downloads/latest/python3.12/)
- [MySQL 8.0.45](https://dev.mysql.com/downloads/)

如果您在未安装必要环境的情况下运行了配置脚本，其将会提示您安装并退出。

### 1. 运行配置脚本

**Linux / macOS**
```bash
bash scripts/setup.sh
# 或先授权后运行:
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

**Windows**
```bat
scripts\setup.bat
```

### 2. 选择运行模式

脚本运行时将引导您选择：

| 模式 | 说明 |
|------|------|
| **[L] 本地调试** | 配置 `.env`，完成数据库初始化，最后自动启动 `runserver` |
| **[S] 服务器部署** | 写入生产配置（`DEBUG=False`），安装 Gunicorn，在 `deploy/` 目录生成 `gunicorn.conf.py`、`readsite.service`、`nginx.conf`，并打印后续操作步骤 |

> **注意**：服务器部署模式（Gunicorn + systemd）仅支持 **Linux 和 macOS**。

### 3. 日常开发

项目完成初始化后，每次更新只需运行：

**Linux / macOS**
```bash
# 开发运行
bash scripts/dev.sh

# 服务器运行
bash scripts/update.sh
```

**Windows**
```bat
scripts\dev.bat
```

脚本会自动执行数据库更新和静态文件收集，然后启动服务器。

---

## 🚀 手动配置（Manual Setup）

如需手动配置，请按以下步骤操作。

### 1. 克隆项目
```bash
git clone https://github.com/lycshanshan/ReadSite.git
cd ReadSite
```

### 2. 创建并激活虚拟环境
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 创建 MySQL 数据库
```bash
# 登录 MySQL
mysql -u root -p
```
```sql
-- 在 MySQL 控制台执行:
CREATE DATABASE novel_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;
```

### * 使用 SQLite 数据库

如果您希望使用 SQLite，请在 `.env` 中添加：
```env
DB_TYPE=sqlite3
```
此情况下，**无需**创建数据库，直接进入步骤 5 即可。SQLite 数据库文件将自动创建为 `db.sqlite3`。

> 如需将数据从 SQLite 迁移至 MySQL，请参看 [CHANGELOG](CHANGELOG.md) v0.3.0 版本说明。

### 5. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# --- 安全配置 ---
SECRET_KEY=填入一个复杂的随机字符串

# --- 数据库配置 ---
# 数据库类型: mysql 或 sqlite3（默认 mysql）
DB_TYPE=mysql

# MySQL 配置（仅 DB_TYPE=mysql 时需要）
DB_NAME=novel_db
DB_USER=root
DB_PASSWORD=你的密码
DB_HOST=127.0.0.1
DB_PORT=3306

# --- 运行配置 ---
# 开发时填 True，上线时填 False
DEBUG=True

# 多个域名用逗号分隔；本地开发可填 127.0.0.1,localhost
# 上线后应替换为服务器 IP 或域名，并删除 127.0.0.1
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1,http://localhost,http://127.0.0.1:8000,http://localhost:8000
```

### 6. 初始化数据库与静态文件
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
```

### 7. 创建超级管理员
```bash
python manage.py createsuperuser
```

### 8. 启动服务
```bash
python manage.py runserver
```
访问 `http://127.0.0.1:8000` 浏览前台页面！

---

## 📖 API 文档

项目集成了 `drf-spectacular`，启动服务后可通过以下地址查看和调试 API：

- **Swagger UI（交互式文档）**: `http://127.0.0.1:8000/api/docs/`
- **OpenAPI Schema 下载**: `http://127.0.0.1:8000/api/schema/`

---

## 🚢 部署建议（生产环境）

推荐使用 `scripts/setup.sh`（服务器模式）自动生成部署配置，脚本会在 `deploy/` 目录生成 Gunicorn、systemd 和 Nginx 配置文件，并打印完整的操作步骤。

若需手动部署，请注意以下几点：

1. **修改环境变量**：将 `.env` 中的 `DEBUG` 修改为 `False`。
2. **配置 ALLOWED_HOSTS**：将服务器 IP 或域名加入 `ALLOWED_HOSTS` 和 `CSRF_TRUSTED_ORIGINS`。
3. **使用 WSGI 服务器**：不要在生产环境使用 `runserver`，推荐使用 **Gunicorn** + **Nginx**。

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动示例（入口文件: novel_proj/wsgi.py）
gunicorn novel_proj.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 协议开源。
