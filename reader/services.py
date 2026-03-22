# services.py (或者 utils.py)
import os
import zipfile
import tempfile
import time
from django.http import FileResponse, StreamingHttpResponse
from django.utils.encoding import escape_uri_path
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