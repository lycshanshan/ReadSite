# Let's Read! 网站后端 API 文档

**版本**: v1.0
**基础 URL**: `http://127.0.0.1:8000/api`
**认证方式**: Basic Auth (推荐脚本使用) 或 Session Auth (浏览器使用)

> **注意**: 所有 API 均需要认证。
> *   普通管理员只能操作自己上传的书籍。
> *   超级管理员可以操作所有数据。

---

## 1. 认证与基础准备

在调用任何 API 之前，请确保你的 Python 脚本配置了正确的认证信息。

**通用 Python 示例头：**

```python
import requests
from requests.auth import HTTPBasicAuth

# 配置
BASE_URL = "http://read.lycshanshan.top/api"
# 请替换为你的管理员账号密码
AUTH = HTTPBasicAuth('admin_username', 'your_password')

def print_response(res):
    """辅助函数：打印美化后的响应"""
    try:
        print(f"Status: {res.status_code}")
        print(res.json())
    except:
        print(res.text)
```

---

## 2. 书籍内容管理 (Staff/Admin)

此部分接口允许管理员上传、修改和删除书籍资源。

### 2.1 上传书籍
创建一个新的书籍条目。创建者将自动被记录为该书的 `uploader`。

*   **URL**: `/admin/books/`
*   **Method**: `POST`
*   **权限**: IsAdminUser (员工)

**参数说明**:

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `title` | String | 是 | 书籍标题 |
| `author` | String | 是 | 作者名 |
| `description` | String | 否 | 书籍简介 |
| `cover` | File | 否 | 封面图片文件 |

**Python 示例**:

```python
def upload_book():
    url = f"{BASE_URL}/admin/books/"
    data = {
        "title": "API测试指南",
        "author": "开发者",
        "description": "这是一本通过API自动上传的书籍。"
    }
    # 上传文件时，需以二进制模式打开
    files = {
        "cover": open("local_cover.jpg", "rb") 
    }
  
    response = requests.post(url, data=data, files=files, auth=AUTH)
    print_response(response)
    return response.json().get('id') # 返回书籍ID供后续使用
```

### 2.2 修改书籍信息
修改已存在的书籍信息。

*   **URL**: `/admin/books/{id}/`
*   **Method**: `PATCH` (局部更新) 或 `PUT` (全量替换)
*   **权限**: 对象所有者 或 Superuser

**Python 示例**:

```python
def update_book_desc(book_id):
    url = f"{BASE_URL}/admin/books/{book_id}/"
    data = {
        "description": "简介已被修改。"
    }
    response = requests.patch(url, data=data, auth=AUTH)
    print_response(response)
```

### 2.3 上传章节
向指定书籍添加一章。

*   **URL**: `/admin/chapters/`
*   **Method**: `POST`
*   **权限**: 书籍所有者 或 Superuser

**参数说明**:

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `book` | Integer | 是 | 所属书籍的 ID |
| `title` | String | 是 | 章节标题 |
| `content` | String | 是 | 章节正文内容 |
| `index` | Integer | 否 | 排序索引 (如 1, 2, 3) |
| `volume_name` | String | 否 | 分卷名称 (如 "第一卷") |

**Python 示例**:

```python
def upload_chapter(book_id):
    url = f"{BASE_URL}/admin/chapters/"
    data = {
        "book": book_id,
        "title": "第一章 Hello World",
        "content": "这里是章节的正文内容......",
        "index": 1,
        "volume_name": "正文"
    }
    response = requests.post(url, data=data, auth=AUTH)
    print_response(response)
```

### 2.4 修改章节
修改已存在的章节内容。

*   **URL**: `/admin/chapters/{id}/`
*   **Method**: `PATCH` 或 `PUT`
*   **权限**: 书籍所有者 或 Superuser

**Python 示例**:

```python
def update_chapter_desc(chapter_id):
    url = f"{BASE_URL}/admin/chapters/{chapter_id}/"
    data = {
        "content": "正文已被修改。"
    }
    response = requests.patch(url, data=data, auth=AUTH)
    print_response(response)
```

### 2.5 上传插图
向指定书籍的某一卷添加插图。

*   **URL**: `/admin/illustrations/`
*   **Method**: `POST`
*   **权限**: 书籍所有者 或 Superuser

**参数说明**:

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `book` | Integer | 是 | 所属书籍的 ID |
| `image` | File | 是 | 图片文件 |
| `index` | Integer | 否 | 排序索引 |
| `volume_name` | String | 否 | 分卷名称 |

**Python 示例**:

```python
def upload_illustration(book_id):
    url = f"{BASE_URL}/admin/illustrations/"
    data = {
        "book": book_id,
        "index": 1,
        "volume_name": "正文"
    }
    files = {
        "image": open("illustration.png", "rb")
    }
    response = requests.post(url, data=data, files=files, auth=AUTH)
    print_response(response)
```

### 2.6 删除资源
删除书籍、章节或插图。删除书籍会级联删除其下所有章节和插图。

*   **URL**: 
    *   `/admin/books/{id}/`
    *   `/admin/chapters/{id}/`
    *   `/admin/illustrations/{id}/`
*   **Method**: `DELETE`

**Python 示例**:

```python
def delete_resource(resource_type, resource_id):
    # resource_type 可以是 'books', 'chapters', 'illustrations'
    url = f"{BASE_URL}/admin/{resource_type}/{resource_id}/"
    response = requests.delete(url, auth=AUTH)
    print(f"Delete Status: {response.status_code}") # 204 表示成功
```

---

## 3. 全局系统设置 (Superuser Only)

此部分接口仅限超级管理员使用，用于控制网站的注册策略。

### 3.1 查看当前设置
*   **URL**: `/admin/settings/`
*   **Method**: `GET`

### 3.2 修改全局配置
*   **URL**: `/admin/settings/update/`
*   **Method**: `POST` 或 `PATCH`

**参数说明**:

| 参数名 | 类型 | 选项值 | 说明 |
| :--- | :--- | :--- | :--- |
| `registration_mode` | String | `open`, `invite`, `closed` | 注册模式 |
| `invite_code` | String | 任意字符串 | 邀请码 (仅在 invite 模式生效) |

**Python 示例**:

```python
def change_system_settings():
    url = f"{BASE_URL}/admin/settings/update/"
    data = {
        "registration_mode": "invite", # 开启邀请码模式
        "invite_code": "VIP888"        # 设置邀请码
    }
    response = requests.post(url, data=data, auth=AUTH)
    print_response(response)
```

---

## 4. 用户管理 (Superuser Only)

此部分接口仅限超级管理员使用，用于管理网站用户。

### 4.1 获取用户列表
*   **URL**: `/admin/users/`
*   **Method**: `GET`
*   **功能**: 返回所有注册用户的列表，按注册时间倒序排列。

### 4.2 创建新用户
*   **URL**: `/admin/users/`
*   **Method**: `POST`

**参数说明**:

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `username` | String | 是 | 用户名 |
| `password` | String | 是 | 密码 |
| `is_staff` | Boolean | 否 | 是否为员工 (默认为 False) |

**Python 示例**:

```python
def create_staff_user():
    url = f"{BASE_URL}/admin/users/"
    data = {
        "username": "editor_01",
        "password": "SecretPassword123",
        "is_staff": True,  # 创建一个普通管理员账号
        "is_active": True # 保证用户可以登录
    }
    response = requests.post(url, data=data, auth=AUTH)
    print_response(response)
```

### 4.3 封禁/解封用户
通过专用接口快速封禁用户（禁止登录）。

*   **URL**: 
    *   封禁: `/admin/users/{id}/ban/`
    *   解封: `/admin/users/{id}/unban/`
*   **Method**: `POST`

**Python 示例**:

```python
def ban_bad_user(user_id):
    url = f"{BASE_URL}/admin/users/{user_id}/ban/"
    response = requests.post(url, auth=AUTH)
    print_response(response)
```

---