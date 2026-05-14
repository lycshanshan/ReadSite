#!/usr/bin/env python3
"""
小说自动导入脚本 — 通过 REST API 将小说数据导入 ReadSite

用法:
  python scripts/import_novel.py novels/eg1 --username admin

数据格式要求：
  - 小说文件夹中有一个 .hmz 文件（JSON），存储书名、作者、简介、分卷和章节信息
  - 每卷为同名子文件夹，内含 1.txt, 2.txt, ... 章节正文
  - 每卷 插图/ 子文件夹存放插图图片
  - .txt 文件段落间以空行分隔，脚本保留此格式
"""

import argparse
import json
import os
import re
from pathlib import Path

# ── 默认值常量 ────────────────────────────────────────────────────────────────────

DEFAULT_API_BASE = "http://127.0.0.1:8000/api/"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "LYC20070825"
NOVEL_PATH = "novels/eg1"


# ── .hmz 解析 ──────────────────────────────────────────────────────────────────

def find_hmz(novel_path):
    """在小说文件夹中查找 .hmz 文件，找不到则退出"""
    hmz_files = list(Path(novel_path).glob("*.hmz"))
    if not hmz_files:
        raise SystemExit(f"错误：在 {novel_path} 中未找到 .hmz 文件")
    if len(hmz_files) > 1:
        names = [f.name for f in hmz_files]
        raise SystemExit(f"错误：在 {novel_path} 中发现多个 .hmz 文件: {names}。请用 --hmz-file 指定。")
    return hmz_files[0]


def parse_hmz(hmz_file):
    """
    解析 .hmz 文件，返回 (book_meta, volumes) 元组。

    book_meta: dict with keys: title, author, description
    volumes: list of volume dicts:
        {
            "name": "第一卷",
            "chapters": [
                {"title": "章节标题", "index": 2, "txt_file": Path("第一卷/2.txt")},
                ...
            ],
            "illustration_dir": Path("第一卷/插图") or None,
        }
    """
    with open(hmz_file, encoding="utf-8") as f:
        data = json.load(f)

    book_meta = {
        "title": data.get("name", ""),
        "author": data.get("writer", "未知"),
        "description": data.get("description", ""),
    }

    base_dir = Path(hmz_file).parent
    allname = data.get("allname", [])

    volumes = []
    chapter_index = 1  # 跨卷全局章节序号
    for vol_entries in allname:
        if not vol_entries:
            continue
        volume_name = vol_entries[0]

        # 收集本章节的章节（跳过卷名和"插图"条目）
        chapters = []
        txt_seq = 1  # txt 文件序号（跳过非插图章节才递增）
        for idx in range(1, len(vol_entries)):
            raw_title = vol_entries[idx]
            is_illustration_chapter = raw_title.strip() == "插图"

            if is_illustration_chapter:
                # 跳过插图章节，但 txt_seq 仍需递增（该条目占位但不生成 Chapter）
                txt_seq += 1
                continue

            chapter_title = raw_title.strip()
            txt_file = base_dir / volume_name / f"{txt_seq}.txt"

            if txt_file.exists():
                chapters.append({
                    "title": chapter_title,
                    "index": chapter_index,
                    "txt_file": txt_file,
                })
                chapter_index += 1
            else:
                print(f"  [警告] 章节文件不存在，跳过: {txt_file}")

            txt_seq += 1

        # 插图目录
        illust_dir = base_dir / volume_name / "插图"
        if not illust_dir.is_dir():
            illust_dir = None

        volumes.append({
            "name": volume_name,
            "chapters": chapters,
            "illustration_dir": illust_dir,
        })

    return book_meta, volumes


def _numeric_key(path):
    """从文件名中提取数字作为排序键，如 '10.jpg' -> 10"""
    m = re.search(r"(\d+)", path.stem)
    return int(m.group(1)) if m else 0


def list_illustrations(illust_dir):
    """返回插图目录中按数字顺序排序的图片路径列表"""
    if illust_dir is None:
        return []
    images = [
        p for p in illust_dir.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    ]
    images.sort(key=_numeric_key)
    return images


# ── 正文读取 ────────────────────────────────────────────────────────────────────

def read_content(txt_file):
    """
    读取章节正文，保留段落间的空行格式。
    将 \r\n 统一转换为 \n。
    """
    with open(txt_file, encoding="utf-8") as f:
        content = f.read()
    # 统一换行符
    content = content.replace("\n", "\n\n")
    return content


# ── API 模式 ────────────────────────────────────────────────────────────────────

def _api_post(api_base, endpoint, data=None, files=None, auth=None):
    """POST 请求封装，返回 response"""
    import requests

    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    resp = requests.post(url, data=data, files=files, auth=auth)
    if resp.status_code not in (200, 201):
        detail = ""
        try:
            detail = resp.text[:300]
        except Exception:
            pass
        print(f"    [API错误] POST {url} -> {resp.status_code}: {detail}")
        return None
    return resp


def _api_put(api_base, endpoint, data=None, files=None, auth=None):
    """PUT 请求封装，返回 response"""
    import requests

    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    resp = requests.put(url, data=data, files=files, auth=auth)
    if resp.status_code not in (200, 201):
        detail = ""
        try:
            detail = resp.text[:300]
        except Exception:
            pass
        print(f"    [API错误] PUT {url} -> {resp.status_code}: {detail}")
        return None
    return resp


def import_via_api(book_meta, volumes, api_base, auth):
    """通过 REST API 导入"""
    # 1. 创建 Book
    book_data = {
        "title": book_meta["title"],
        "author": book_meta["author"],
        "description": book_meta["description"],
    }
    resp = _api_post(api_base, "admin/books/", data=book_data, auth=auth)
    if resp is None:
        raise SystemExit("错误：创建书籍失败，中止。")
    book = resp.json()
    book_id = book["id"]
    print(f"  创建书籍: {book_meta['title']} (id={book_id})")

    # 2. 设置封面：第一卷第一张插图
    cover_set = False
    first_vol = volumes[0] if volumes else None
    if first_vol:
        first_illusts = list_illustrations(first_vol["illustration_dir"])
        if first_illusts:
            cover_path = first_illusts[0]
            with open(cover_path, "rb") as f:
                resp = _api_put(
                    api_base,
                    f"admin/books/{book_id}/",
                    files={"cover": (cover_path.name, f, "image/jpeg")},
                    auth=auth,
                )
                if resp is not None:
                    print(f"  设置封面: {cover_path.name}")
                    cover_set = True

    if not cover_set:
        print("  [提示] 未找到封面图片或上传失败")

    # 3. 逐卷导入章节
    total_chapters = 0
    for vol in volumes:
        for ch in vol["chapters"]:
            content = read_content(ch["txt_file"])
            chapter_data = {
                "book": book_id,
                "title": ch["title"],
                "content": content,
                "index": ch["index"],
                "volume_name": vol["name"],
            }
            resp = _api_post(api_base, "admin/chapters/", data=chapter_data, auth=auth)
            if resp is not None:
                total_chapters += 1
                print(f"    [{vol['name']}] {ch['title']} (index={ch['index']})")

    # 4. 逐卷导入插图
    total_illustrations = 0
    for vol in volumes:
        illusts = list_illustrations(vol["illustration_dir"])
        for idx, img_path in enumerate(illusts, start=1):
            with open(img_path, "rb") as f:
                resp = _api_post(
                    api_base,
                    "admin/illustrations/",
                    data={
                        "book": book_id,
                        "index": idx,
                        "volume_name": vol["name"],
                    },
                    files={"image": (img_path.name, f, "image/jpeg")},
                    auth=auth,
                )
                if resp is not None:
                    total_illustrations += 1
                    print(f"    [插图-{vol['name']}] {img_path.name} (index={idx})")

    print()
    print(f"  导入完成: {total_chapters} 个章节, {total_illustrations} 张插图, 书籍 id={book_id}")


# ── 命令行入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="小说自动导入脚本 — 从指定格式的小说文件夹导入到 ReadSite"
    )
    parser.add_argument(
        "novel_path",
        default=NOVEL_PATH,
        nargs='?',
        help="小说文件夹路径，如 novels/eg1",
    )
    parser.add_argument(
        "--hmz-file",
        help="指定 .hmz 文件路径（默认自动查找）",
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"API 基础 URL（默认 {DEFAULT_API_BASE}）",
    )
    parser.add_argument(
        "--username",
        default=DEFAULT_USERNAME,
        help="API 认证用户名",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="API 认证密码（也可通过 READ_SITE_API_PASSWORD 环境变量设置）",
    )

    args = parser.parse_args()
    novel_path = Path(args.novel_path)

    if not novel_path.is_dir():
        raise SystemExit(f"错误：小说文件夹不存在: {novel_path}")

    # 查找 .hmz
    if args.hmz_file:
        hmz_file = Path(args.hmz_file)
        if not hmz_file.exists():
            raise SystemExit(f"错误：指定的 .hmz 文件不存在: {hmz_file}")
    else:
        hmz_file = find_hmz(novel_path)

    print(f"解析 .hmz 文件: {hmz_file}")
    book_meta, volumes = parse_hmz(hmz_file)

    total_chapters = sum(len(v["chapters"]) for v in volumes)
    total_illusts = 0
    skipped_illust_chapters = 0
    for v in volumes:
        illusts = list_illustrations(v["illustration_dir"])
        total_illusts += len(illusts)

    # 统计跳过的插图章节数（从 allname 中统计）
    with open(hmz_file, encoding="utf-8") as f:
        raw_data = json.load(f)
    for vol_entries in raw_data.get("allname", []):
        for title in vol_entries[1:]:
            if title.strip() == "插图":
                skipped_illust_chapters += 1

    print(f"  书名: {book_meta['title']}")
    print(f"  作者: {book_meta['author']}")
    print(f"  分卷数: {len(volumes)}")
    print(f"  章节数: {total_chapters}")
    print(f"  插图章节数（跳过）: {skipped_illust_chapters}")
    print(f"  插图图片数: {total_illusts}")
    print()

    print(f"使用 API 模式导入 (base={args.api_base})...")
    username = args.username
    if not username:
        raise SystemExit("错误：需要 --username 参数")
    pw = args.password or os.environ.get("READ_SITE_API_PASSWORD")
    if not pw:
        from getpass import getpass
        pw = getpass(f"请输入用户 {username} 的密码: ")
    auth = (username, pw)
    import_via_api(book_meta, volumes, args.api_base, auth)


if __name__ == "__main__":
    main()
