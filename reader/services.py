import os
import zipfile
import tempfile
import time
import re
from django.http import FileResponse, StreamingHttpResponse
from django.utils.encoding import escape_uri_path
from django.db.models import Q
from .models import Illustration

class BookDownloadService:
    @staticmethod
    def generate_text_chunks(book):
        """文本生成器，分块生成小说文本"""
        yield f"《{book.title}》\n作者：{book.author}\n\n".encode('utf-8')
        yield f"简介：\n{book.description}\n\n".encode('utf-8')
        
        chapters = book.chapters.all().order_by('index').iterator()
        vol_name = ''
        for chapter in chapters:
            if chapter.volume_name != vol_name:
                vol_name = chapter.volume_name
                yield f"{'-' * 20}\n\n{vol_name}\n\n".encode('utf-8')
            yield f"{chapter.title}\n\n{chapter.content}\n\n\n".encode('utf-8')

    @classmethod
    def generate_download_response(cls, book, need_text=True, need_img=True):
        """
        根据需求生成对应的 HttpResponse (ZIP 或 TXT)
        - need_text: 是否需要下载文本
        - need_img: 是否需要下载插图
        """
        has_images = need_img and book.illustration_count > 0

        # 如果需要下载图片且小说有插图，则打包为 ZIP
        if has_images:
            temp_file = tempfile.SpooledTemporaryFile(max_size=10*1024*1024, mode='w+b')
            with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # 写入文本
                if need_text:
                    with zip_file.open(f"{book.title}.txt", 'w') as txt_file_in_zip:
                        for chunk in cls.generate_text_chunks(book):
                            txt_file_in_zip.write(chunk)
                
                # 写入图片
                illustrations = Illustration.objects.filter(book=book).order_by('volume_name', 'index').iterator()
                for ill in illustrations:
                    vol_folder = (ill.volume_name or "正文").replace("/", "_").replace("\\", "_")
                    _, ext = os.path.splitext(ill.image.path)
                    arcname = f"{vol_folder}/{ill.id}{ext}"
                    zip_file.write(ill.image.path, arcname=arcname)
            
            temp_file.seek(0)
            filename = f"{book.id}.zip"
            response = FileResponse(temp_file, as_attachment=True, filename=filename)
            response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
            return response
            
        else:
            # 对于纯文本，使用流式响应
            response = StreamingHttpResponse(cls.generate_text_chunks(book), content_type='text/plain')
            filename = f"{book.id}_text.txt"
            response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
            return response

    @classmethod
    def generate_multi_books_download_response(cls, books, need_text=True, need_img=True):
        """
        多本书籍批量下载: 打包为一个大的 ZIP 文件。
        books: 包含多个 Book 对象的列表或 QuerySet。
        """
        temp_file = tempfile.SpooledTemporaryFile(max_size=20*1024*1024, mode='w+b')
        
        with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for book in books:
                # 为了防止不同书籍重名导致文件覆盖，使用 "书名_ID" 作为每本书的根目录
                book_folder = f"{book.title}_{book.id}".replace("/", "_").replace("\\", "_")

                if need_text:
                    # 路径: 书名_ID/书名.txt
                    txt_arcname = f"{book_folder}/{book.title}.txt"
                    with zip_file.open(txt_arcname, 'w') as txt_file_in_zip:
                        for chunk in cls.generate_text_chunks(book):
                            txt_file_in_zip.write(chunk)

                has_images = need_img and book.illustration_count > 0
                if has_images:
                    illustrations = Illustration.objects.filter(book=book).order_by('volume_name', 'index').iterator()
                    for ill in illustrations:
                        vol_folder = (ill.volume_name or "正文").replace("/", "_").replace("\\", "_")
                        _, ext = os.path.splitext(ill.image.path)
                        # 路径: 书名_ID/卷名/图片.jpg
                        arcname = f"{book_folder}/{vol_folder}/{ill.id}{ext}"
                        zip_file.write(ill.image.path, arcname=arcname)

        temp_file.seek(0)
        
        # 生成带有时间戳的文件名
        filename = f"books_batch_{int(time.time())}.zip"
        response = FileResponse(temp_file, as_attachment=True, filename=filename)
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
        return response


class SearchService:
    @staticmethod
    def _is_regex(query_string):
        """
        判断用户输入是否具有明显的正则表达式意图，并且是一个合法的正则。
        """
        # 正则特殊字符集
        regex_indicators = [
            '^', '$', '.', '.*', '.+', '*', '+', '?', '|',
            '(', ')', '[', ']', '{', '}', '(?',
            r'\d', r'\w', r'\s',
            r'\D', r'\W', r'\S', r'\b', r'\B'
        ]
        
        # 如果包含这些特征字符之一，尝试编译
        if any(indicator in query_string for indicator in regex_indicators):
            try:
                re.compile(query_string)
                return True
            except re.error:
                return False
        return False
    
    @staticmethod
    def build_search_query(query_string, search_fields):
        """
        构建智能模糊搜索的 Q 对象
        :param query_string: 用户输入的搜索词
        :param search_fields: 需要搜索的模型字段列表，例如 ['title', 'author', 'tags__name']
        :return: Django Q 对象
        """
        query_string = query_string.strip()
        if not query_string:
            return Q()
        if SearchService._is_regex(query_string):
            final_q = Q()
            for field in search_fields:
                final_q |= Q(**{f"{field}__iregex": query_string})
            return final_q
        
        # 将多个连续空白字符压缩为一个空格并拆词搜索
        query_string = re.sub(r'\s+', ' ', query_string)
        if ' ' in query_string:
            words = query_string.split(' ')[:5]  # 最多允许拆分5个词，防止超长查询
            final_q = Q()
            for word in words:
                word_q = Q()
                for field in search_fields:
                    word_q |= Q(**{f"{field}__icontains": word})
                final_q &= word_q  # 多个词之间是 AND 关系 (必须同时满足)
            return final_q
        
        # 正则搜索
        length = len(query_string)
        # 边界条件：字符太少(1个字)没必要正则，字符太多(>10)正则极慢且容易无意义
        if 1 < length <= 10:
            # 边界条件处理：使用 re.escape 转义用户输入，防止用户输入 .*+? 等正则元字符导致数据库正则解析报错
            regex_pattern = '.*'.join(re.escape(char) for char in query_string)
            final_q = Q()
            for field in search_fields:
                final_q |= Q(**{f"{field}__iregex": regex_pattern})
            return final_q
        # 退化策略 (单个字符或超长字符串)
        else:
            final_q = Q()
            for field in search_fields:
                final_q |= Q(**{f"{field}__icontains": query_string})
            return final_q