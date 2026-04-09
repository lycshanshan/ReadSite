#!/usr/bin/env python3
"""
ReadSite 自动化部署脚本
支持平台: Windows, macOS, Linux
仅使用 Python 标准库，无第三方依赖。

用法:
    由 setup.sh / setup.bat 调用:  python scripts/setup.py <python_executable>
    直接运行:                       python scripts/setup.py
"""
import os
import sys
import subprocess
import platform
import shutil
import secrets
import getpass
from pathlib import Path

# ── 路径常量 ──────────────────────────────────────────────────────────────────

SCRIPTS_DIR  = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
VENV_DIR     = PROJECT_ROOT / 'venv'
ENV_FILE     = PROJECT_ROOT / '.env'
MANAGE_PY    = PROJECT_ROOT / 'manage.py'
DEPLOY_DIR   = PROJECT_ROOT / 'deploy'
REQUIREMENTS = PROJECT_ROOT / 'requirements.txt'

IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX   = platform.system() == 'Linux'
IS_MAC     = platform.system() == 'Darwin'

if IS_WINDOWS:
    VENV_PYTHON = VENV_DIR / 'Scripts' / 'python.exe'
    VENV_PIP    = VENV_DIR / 'Scripts' / 'pip.exe'
else:
    VENV_PYTHON = VENV_DIR / 'bin' / 'python'
    VENV_PIP    = VENV_DIR / 'bin' / 'pip'

# ── 输出工具 ──────────────────────────────────────────────────────────────────

def print_header(text: str):
    width = max(len(text) + 6, 55)
    print()
    print('─' * width)
    print(f'   {text}')
    print('─' * width)

def print_step(text: str):
    print(f'\n▶  {text}')

def print_ok(text: str):
    print(f'   ✓ {text}')

def print_warn(text: str):
    print(f'   ⚠  {text}', file=sys.stderr)

def print_error(text: str):
    print(f'\n   ✗ 错误: {text}', file=sys.stderr)

def ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = '[Y/n]' if default else '[y/N]'
    while True:
        ans = input(f'   {prompt} {hint}: ').strip().lower()
        if ans == '':
            return default
        if ans in ('y', 'yes', '是'):
            return True
        if ans in ('n', 'no', '否'):
            return False
        print('   请输入 y 或 n')

def run_subprocess(cmd: list, cwd: Path = None, exit_on_error: bool = True):
    """以列表方式运行子进程，失败时退出（不使用 shell=True，避免注入风险）。"""
    if cwd is None:
        cwd = PROJECT_ROOT
    result = subprocess.run([str(c) for c in cmd], cwd=str(cwd))
    if exit_on_error and result.returncode != 0:
        print_error(f'命令执行失败: {" ".join(str(c) for c in cmd)}')
        sys.exit(1)
    return result

# ── 环境变量检测 ──────────────────────────────────────────────────────────────

class EnvStatus:
    def __init__(self):
        self.is_configured = False
        self.db_type       = 'mysql'
        self.missing_keys  = []

def parse_env_file() -> dict:
    """读取 .env 文件，返回 key->value 字典（忽略注释和空行）。"""
    env = {}
    if not ENV_FILE.exists():
        return env
    with open(ENV_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, val = line.partition('=')
                env[key.strip()] = val.strip()
    return env

def check_env() -> EnvStatus:
    """检查 .env 文件是否存在且包含所有必需配置项。"""
    status = EnvStatus()
    if not ENV_FILE.exists():
        return status

    env = parse_env_file()
    db_type = env.get('DB_TYPE', 'mysql')
    # 与 settings.py 保持一致：不识别的值也默认为 mysql
    status.db_type = db_type if db_type in ('mysql', 'sqlite3') else 'mysql'

    if not env.get('SECRET_KEY'):
        status.missing_keys.append('SECRET_KEY')
    if not env.get('DB_TYPE'):
        status.missing_keys.append('DB_TYPE')
    if status.db_type == 'mysql':
        for key in ('DB_NAME', 'DB_USER', 'DB_PASSWORD'):
            if not env.get(key):
                status.missing_keys.append(key)

    status.is_configured = len(status.missing_keys) == 0
    return status

# ── 模式选择 ──────────────────────────────────────────────────────────────────

def ask_mode() -> str:
    print_header('ReadSite 自动化配置向导')
    print('\n   请选择运行模式:')
    print('   [L] 本地调试   - 配置开发环境并启动 runserver')
    print('   [S] 服务器部署 - 配置生产环境并生成 Gunicorn/Nginx 配置')
    while True:
        ans = input('\n   请输入选项 (L/S): ').strip().lower()
        if ans in ('l', 'local'):
            return 'local'
        if ans in ('s', 'server'):
            return 'server'
        print('   请输入 L 或 S')

# ── 密钥生成 ──────────────────────────────────────────────────────────────────

def generate_secret_key() -> str:
    return secrets.token_urlsafe(50)

# ── 数据库配置 ────────────────────────────────────────────────────────────────

def ask_db_type() -> str:
    print('\n   请选择数据库类型:')
    print('   [1] MySQL   (推荐，生产环境首选)')
    print('   [2] SQLite3 (轻量，适合快速测试)')
    while True:
        ans = input('\n   请输入选项 (1/2): ').strip()
        if ans == '1':
            return 'mysql'
        if ans == '2':
            return 'sqlite3'
        print('   请输入 1 或 2')

def check_mysql_cli_available():
    """检查 mysql 命令行工具是否可用，不可用则打印安装指引并退出。"""
    if shutil.which('mysql') is None:
        print_error('未找到 MySQL 命令行工具 (mysql)，请先安装 MySQL。')
        print()
        if IS_LINUX:
            print('   Ubuntu/Debian:  sudo apt install mysql-client default-libmysqlclient-dev')
            print('   CentOS/RHEL:    sudo yum install mysql')
        elif IS_MAC:
            print('   macOS (Homebrew): brew install mysql-client')
            print('   安装后请将以下行添加到 ~/.zshrc 或 ~/.bash_profile:')
            print('     export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"')
        else:
            print('   Windows 请前往以下地址下载 MySQL Installer:')
            print('     https://dev.mysql.com/downloads/installer/')
            print('   安装时确保勾选 "MySQL Server" 并将 mysql.exe 添加到 PATH。')
        sys.exit(1)

def ask_mysql_credentials() -> dict:
    print('\n   请输入 MySQL 连接信息:')
    host    = input('   主机地址 [127.0.0.1]: ').strip() or '127.0.0.1'
    port    = input('   端口     [3306]:      ').strip() or '3306'
    user    = ''
    while not user:
        user = input('   用户名:               ').strip()
        if not user:
            print('   用户名不能为空')
    password = getpass.getpass('   密码:                 ')
    db_name  = input('   数据库名  [novel_db]:  ').strip() or 'novel_db'
    return {
        'host':     host,
        'port':     port,
        'user':     user,
        'password': password,
        'db_name':  db_name,
    }

def _mysql_cmd(db_config: dict, sql: str) -> list:
    """构建 mysql CLI 命令列表（不经 shell，密码拼接而非空格分隔，避免转义问题）。"""
    return [
        'mysql',
        f'-h{db_config["host"]}',
        f'-P{db_config["port"]}',
        f'-u{db_config["user"]}',
        f'-p{db_config["password"]}',   # 密码紧跟 -p，无空格
        '-e', sql,
    ]

def test_mysql_connection(db_config: dict):
    print_step('测试 MySQL 连接...')
    result = subprocess.run(
        _mysql_cmd(db_config, 'SELECT 1;'),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print_error('MySQL 连接失败，请检查用户名、密码和主机地址。')
        # 隐藏密码后输出错误信息
        stderr_safe = result.stderr.replace(db_config['password'], '***')
        print(f'   {stderr_safe.strip()}', file=sys.stderr)
        sys.exit(1)
    print_ok('MySQL 连接成功')

def create_mysql_database(db_config: dict):
    db_name = db_config['db_name']
    print_step(f'创建数据库 `{db_name}`...')
    sql = (
        f'CREATE DATABASE IF NOT EXISTS `{db_name}` '
        f'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'
    )
    result = subprocess.run(
        _mysql_cmd(db_config, sql),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr_safe = result.stderr.replace(db_config['password'], '***')
        print_error(f'数据库创建失败: {stderr_safe.strip()}')
        sys.exit(1)
    print_ok(f'数据库 `{db_name}` 已就绪')

# ── 主机配置 ──────────────────────────────────────────────────────────────────

def ask_host_config(mode: str) -> dict:
    if mode == 'local':
        return {
            'allowed_hosts': '127.0.0.1,localhost',
            'csrf_origins':  (
                'http://127.0.0.1,http://localhost,'
                'http://127.0.0.1:8000,http://localhost:8000'
            ),
            'server_ip': None,
        }
    # 服务器模式：询问公网 IP
    server_ip = ''
    while not server_ip:
        server_ip = input('   服务器公网 IP 地址: ').strip()
        if not server_ip:
            print('   IP 地址不能为空')
    return {
        'allowed_hosts': server_ip,
        'csrf_origins':  f'http://{server_ip},https://{server_ip}',
        'server_ip':     server_ip,
    }

# ── .env 文件读写 ──────────────────────────────────────────────────────────────

def write_env_file(secret_key: str, db_type: str, db_config: dict,
                   host_config: dict, mode: str):
    debug = 'True' if mode == 'local' else 'False'

    lines = [
        '# Generated by ReadSite setup script\n',
        '\n',
        '# Security\n',
        f'SECRET_KEY={secret_key}\n',
        '\n',
        '# Database\n',
        f'DB_TYPE={db_type}\n',
    ]
    if db_type == 'mysql':
        lines += [
            f'DB_NAME={db_config["db_name"]}\n',
            f'DB_USER={db_config["user"]}\n',
            f'DB_PASSWORD={db_config["password"]}\n',
            f'DB_HOST={db_config["host"]}\n',
            f'DB_PORT={db_config["port"]}\n',
        ]
    lines += [
        '\n',
        f'DEBUG={debug}\n',
        '\n',
        f'ALLOWED_HOSTS={host_config["allowed_hosts"]}\n',
        f'CSRF_TRUSTED_ORIGINS={host_config["csrf_origins"]}\n',
    ]

    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print_ok(f'.env 已写入: {ENV_FILE}')

def update_env_value(key: str, value: str):
    """更新 .env 中某个 key 的值（不存在则追加）。"""
    if not ENV_FILE.exists():
        return
    lines = ENV_FILE.read_text(encoding='utf-8').splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f'{key}=') or stripped.startswith(f'{key} ='):
            lines[i] = f'{key}={value}\n'
            found = True
            break
    if not found:
        lines.append(f'{key}={value}\n')
    ENV_FILE.write_text(''.join(lines), encoding='utf-8')

def append_to_env_list(key: str, new_value: str):
    """将 new_value 追加到 .env 某个逗号分隔列表（去重）。"""
    env = parse_env_file()
    current = env.get(key, '')
    items = [x.strip() for x in current.split(',') if x.strip()]
    if new_value not in items:
        items.append(new_value)
    update_env_value(key, ','.join(items))

# ── 虚拟环境 ──────────────────────────────────────────────────────────────────

def ensure_venv(python_cmd: str):
    print_step('检查虚拟环境...')
    if VENV_PYTHON.exists():
        # 验证 venv Python 是否可用
        result = subprocess.run(
            [str(VENV_PYTHON), '--version'],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print_ok(f'使用已存在的虚拟环境: {VENV_DIR}')
            return
        print_warn('虚拟环境似乎已损坏。')
        if ask_yes_no('是否删除并重新创建?'):
            shutil.rmtree(str(VENV_DIR))
        else:
            print_error('请手动修复虚拟环境后重试。')
            sys.exit(1)

    print_step('创建虚拟环境...')
    result = subprocess.run(
        [python_cmd, '-m', 'venv', str(VENV_DIR)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = result.stderr
        if 'ensurepip' in err or 'venv' in err.lower():
            print_error('创建虚拟环境失败，可能缺少 python3.12-venv 包。')
            if IS_LINUX:
                print('\n   请先运行: sudo apt install python3.12-venv')
        else:
            print_error(f'创建虚拟环境失败: {err.strip()}')
        sys.exit(1)
    print_ok(f'虚拟环境已创建: {VENV_DIR}')

def pip_install(db_type: str = 'mysql'):
    print_step('安装 Python 依赖（可能需要几分钟）...')

    # 如果是 sqlite3，则动态生成一个不包含 mysqlclient 的临时 requirements 文件
    if db_type == 'sqlite3':
        with open(REQUIREMENTS, 'r', encoding='utf-8') as f:
            reqs = f.readlines()
        filtered_reqs = [req for req in reqs if not req.strip().lower().startswith('mysqlclient')]
        target_req_path = PROJECT_ROOT / 'requirements_temp.txt'
        with open(target_req_path, 'w', encoding='utf-8') as f:
            f.writelines(filtered_reqs)
    else:
        target_req_path = REQUIREMENTS

    result = subprocess.run(
        [str(VENV_PIP), 'install', '-r', str(target_req_path)],
        cwd=str(PROJECT_ROOT),
    )
    if db_type == 'sqlite3' and target_req_path.exists():
        target_req_path.unlink()

    if result.returncode != 0:
        print_error('依赖安装失败。')
        if IS_LINUX:
            print('\n   若 mysqlclient 编译失败，请先安装系统依赖:')
            print('   sudo apt install default-libmysqlclient-dev build-essential python3-dev')
        sys.exit(1)
    print_ok('依赖安装完成')

# ── Django 命令 ───────────────────────────────────────────────────────────────

def run_migrations():
    print_step('执行数据库迁移...')
    run_subprocess([VENV_PYTHON, MANAGE_PY, 'makemigrations'])
    run_subprocess([VENV_PYTHON, MANAGE_PY, 'migrate'])
    print_ok('数据库迁移完成')

def run_collectstatic():
    print_step('收集静态文件...')
    run_subprocess([VENV_PYTHON, MANAGE_PY, 'collectstatic', '--noinput'])
    print_ok('静态文件已收集至 static_collection/')

def run_createsuperuser():
    print_step('创建超级管理员账号（请按提示输入用户名、邮箱和密码）...')
    subprocess.run(
        [str(VENV_PYTHON), str(MANAGE_PY), 'createsuperuser'],
        cwd=str(PROJECT_ROOT),
        # 不捕获 stdin/stdout，让 Django 的交互提示直接显示
    )

def run_devserver():
    print_header('启动开发服务器')
    print('   访问地址: http://127.0.0.1:8000')
    print('   API 文档: http://127.0.0.1:8000/api/docs/')
    print('   按 Ctrl+C 停止服务器\n')
    subprocess.run(
        [str(VENV_PYTHON), str(MANAGE_PY), 'runserver'],
        cwd=str(PROJECT_ROOT),
    )

# ── 服务器部署 ────────────────────────────────────────────────────────────────

def generate_deploy_configs(server_ip: str, domain: str | None):
    """生成 deploy/ 目录下的 Gunicorn/systemd/Nginx 配置文件。"""
    DEPLOY_DIR.mkdir(exist_ok=True)

    server_name = domain if domain else server_ip
    try:
        current_user = getpass.getuser()
    except Exception:
        current_user = 'www-data'

    root            = str(PROJECT_ROOT)
    venv_gunicorn   = str(VENV_DIR / 'bin' / 'gunicorn')
    static_root     = str(PROJECT_ROOT / 'static_collection')
    media_root      = str(PROJECT_ROOT / 'media')

    # ── gunicorn.conf.py ──
    gunicorn_conf = f"""\
# Generated by ReadSite setup script
# Project root: {root}

bind    = "127.0.0.1:8000"
workers = 3
# 推荐值: workers = (CPU 核心数 × 2) + 1

wsgi_app = "novel_proj.wsgi:application"
chdir    = "{root}"

accesslog = "{root}/deploy/gunicorn_access.log"
errorlog  = "{root}/deploy/gunicorn_error.log"
loglevel  = "info"

pidfile = "{root}/deploy/gunicorn.pid"
"""
    (DEPLOY_DIR / 'gunicorn.conf.py').write_text(gunicorn_conf, encoding='utf-8')

    # ── readsite.service (systemd) ──
    service_conf = f"""\
[Unit]
Description=ReadSite Gunicorn Daemon
After=network.target

[Service]
User={current_user}
Group=www-data
WorkingDirectory={root}
ExecStart={venv_gunicorn} \\
          --config {root}/deploy/gunicorn.conf.py \\
          novel_proj.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    (DEPLOY_DIR / 'readsite.service').write_text(service_conf, encoding='utf-8')

    # ── nginx.conf ──
    nginx_conf = f"""\
server {{
    listen 80;
    server_name {server_name};

    location /static/ {{
        alias {static_root}/;
    }}

    location /media/ {{
        alias {media_root}/;
    }}

    location / {{
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }}
}}
"""
    (DEPLOY_DIR / 'nginx.conf').write_text(nginx_conf, encoding='utf-8')

    print_ok(f'部署配置文件已生成至 {DEPLOY_DIR}/:')
    print('     gunicorn.conf.py  —  Gunicorn 配置')
    print('     readsite.service  —  systemd 服务单元')
    print('     nginx.conf        —  Nginx 反向代理配置')

def print_post_deploy_instructions():
    root = str(PROJECT_ROOT)
    print_header('后续手动操作步骤')
    print(f"""
   1. 注册并启动 systemd 服务:
      sudo cp {root}/deploy/readsite.service /etc/systemd/system/
      sudo systemctl daemon-reload
      sudo systemctl enable readsite
      sudo systemctl start readsite

   2. 查看服务状态:
      sudo systemctl status readsite

   3. 配置 Nginx:
      sudo cp {root}/deploy/nginx.conf /etc/nginx/sites-available/readsite
      sudo ln -sf /etc/nginx/sites-available/readsite /etc/nginx/sites-enabled/readsite
      sudo nginx -t
      sudo systemctl reload nginx

   4. （可选）申请 HTTPS 证书 (需要已配置域名):
      sudo apt install certbot python3-certbot-nginx
      sudo certbot --nginx -d your-domain.com
""")

def deploy_server():
    if IS_WINDOWS:
        print_warn('Gunicorn 和 systemd 在 Windows 上不受支持。')
        print('   配置文件将被生成供参考，Windows 服务器请考虑使用 waitress 或 IIS。')

    # 安装 Gunicorn
    print_step('安装 Gunicorn...')
    run_subprocess([VENV_PIP, 'install', 'gunicorn'])
    print_ok('Gunicorn 安装完成')

    # 从 .env 读取服务器 IP
    env = parse_env_file()
    server_ip = env.get('ALLOWED_HOSTS', '').split(',')[0].strip() or 'your-server-ip'

    # 询问域名（可选）
    print('\n   是否配置域名？（直接回车跳过，Nginx 将使用 IP 地址）')
    domain = input('   域名 (如 example.com): ').strip() or None

    if domain:
        print_step(f'将域名 {domain} 写入 .env...')
        append_to_env_list('ALLOWED_HOSTS', domain)
        append_to_env_list('CSRF_TRUSTED_ORIGINS', f'http://{domain}')
        append_to_env_list('CSRF_TRUSTED_ORIGINS', f'https://{domain}')
        print_ok('.env 中的 ALLOWED_HOSTS 和 CSRF_TRUSTED_ORIGINS 已更新')

    generate_deploy_configs(server_ip, domain)
    print_post_deploy_instructions()

# ── 两条主流程 ────────────────────────────────────────────────────────────────

def run_configured_workflow(mode: str, python_cmd: str):
    """已有完整 .env 配置时的快速工作流。"""
    print_ok('.env 配置检测通过，跳过配置向导')
    env = parse_env_file()
    db_type = env.get('DB_TYPE', 'mysql')
    ensure_venv(python_cmd)
    pip_install(db_type)
    run_migrations()
    if ask_yes_no('是否立即创建超级管理员账号?', default=True):
        run_createsuperuser()
    if mode == 'local':
        run_devserver()
    else:
        run_collectstatic()
        deploy_server()

def run_new_setup_workflow(mode: str, python_cmd: str):
    """首次配置或 .env 不完整时的引导工作流。"""
    status = check_env()
    if ENV_FILE.exists() and status.missing_keys:
        print_warn(f'.env 文件存在但缺少以下配置项: {", ".join(status.missing_keys)}')
        if not ask_yes_no('继续将覆盖现有 .env，是否继续?'):
            print('   已取消。')
            sys.exit(0)

    print_header('配置环境变量')

    secret_key = generate_secret_key()
    db_type    = ask_db_type()
    db_config  = {}

    if db_type == 'mysql':
        check_mysql_cli_available()
        db_config = ask_mysql_credentials()
        test_mysql_connection(db_config)
        create_mysql_database(db_config)

    if mode == 'server':
        print('\n   请输入服务器信息:')
    host_config = ask_host_config(mode)

    write_env_file(secret_key, db_type, db_config, host_config, mode)

    ensure_venv(python_cmd)
    pip_install(db_type)
    run_migrations()

    if ask_yes_no('是否立即创建超级管理员账号?', default=True):
        run_createsuperuser()

    if mode == 'local':
        run_devserver()
    else:
        run_collectstatic()
        deploy_server()

# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    # sys.argv[1] 由 setup.sh/setup.bat 传入，为系统 Python 3.12 路径
    python_cmd = sys.argv[1] if len(sys.argv) > 1 else sys.executable

    mode   = ask_mode()
    status = check_env()

    if status.is_configured:
        run_configured_workflow(mode, python_cmd)
    else:
        run_new_setup_workflow(mode, python_cmd)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n   ✓ 已停止服务器或取消当前操作。")
        sys.exit(0)
