import base64

from django.db.models import Max
from django.utils.encoding import escape_uri_path
from django.http import StreamingHttpResponse
from django.contrib.auth.models import User

from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action # 用于自定义动作

from .models import Book, Chapter, Illustration, GlobalSettings
from .serializers import (
    BookSerializer, ChapterSerializer, IllustrationSerializer,
    GlobalSettingsSerializer, UserAdminSerializer
)
from .permissions import IsSuperUser, IsUploaderOrSuperUser


# --- 书籍管理 API ---
class BookManageViewSet(viewsets.ModelViewSet):
    """
    书籍管理接口，提供书籍的增删改查。
    普通管理员只能操作自己上传的书籍，超级管理员可操作所有。
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, IsUploaderOrSuperUser]

    def perform_create(self, serializer):
        # 保存时，自动将当前登录用户设为上传者
        serializer.save(uploader=self.request.user)
    
    # 自定义动作：下载书籍 TXT
    # url_path='download' -> /api/admin/books/{id}/download/
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def download(self, request, pk=None):
        book = self.get_object() # 自动根据 pk 获取对象，且检查权限
    
        # 定义生成器 (与网页端逻辑完全一致)
        def file_iterator():
            # 写入书名和作者
            yield f"《{book.title}》\n作者：{book.author}\n\n".encode('utf-8')
            yield f"简介：\n{book.description}\n\n".encode('utf-8')
            # 遍历所有章节 (使用 iterator() 避免一次性加载大量对象到内存)
            chapters = book.chapters.all().order_by('index').iterator()

            vol_name = ''
            volumes = []

            for chapter in chapters:
                if chapter.volume_name != vol_name:
                    vol_name = chapter.volume_name
                    volumes.append(vol_name)
                    yield f"{'-'*20}\n\n".encode('utf-8')
                    yield f"{vol_name}\n\n".encode('utf-8')
                # 拼接标题和正文
                text = f"{chapter.title}\n\n{chapter.content}\n\n\n"
                yield text.encode('utf-8')
            
            if book.illustration_count > 0:
                yield f"{'-'*20}以下为小说插图，以base64编码形式展示{'-'*20}\n\n"
                for volume in volumes:
                    vol_ills = Illustration.objects.filter(book=book, volume_name=volume).order_by('index').iterator()
                    yield f"{'-'*20}{volume}{'-'*20}\n\n"
                    for ill in vol_ills:
                        ill_path = ill.image.path
                        ill_index = ill.index
                        with open(ill_path, 'rb') as f:
                            image_data = f.read()
                            base64_str = base64.b64encode(image_data).decode('utf-8')
                            yield f"{'-'*10}{volume} 插图{ill_index}{'-'*10} start\n"
                            yield base64_str
                            yield f"\n{'-'*10}{volume} 插图{ill_index}{'-'*10} end\n"
                        yield "\n"
                    yield "\n\n"

        # 返回流式响应
        response = StreamingHttpResponse(file_iterator(), content_type='text/plain')
      
        # 设置文件名: {book.id}.txt
        filename = f"{book.id}.txt"
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
      
        return response


# --- 章节管理 API ---
class ChapterManageViewSet(viewsets.ModelViewSet):
    """
    提供章节的增删改查 (单章)。
    批量上传稍微复杂点，我们可以单独写一个 action 或者让客户端循环调这个接口。
    """
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, IsUploaderOrSuperUser]
    
    # 验证权限时，DRF 默认只能验证具体的 obj。
    # 对于 create 操作，因为还没生成 obj，我们需要在 save 时手动检查 book 的归属权。
    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        user = self.request.user
        
        # 如果不是超管，且书不是你传的 -> 拒绝
        if not user.is_superuser and book.uploader != user:
            raise serializers.ValidationError("你无权向这本书添加章节。")
            
        # 自动生成 index 逻辑
        # serializer.validated_data 是经过验证的数据
        if 'index' not in serializer.validated_data:
            # 查询当前书籍下 index 的最大值
            # aggregate 返回的是一个字典: {'index__max': 100} 或 {'index__max': None}
            max_index = Chapter.objects.filter(book=book).aggregate(Max('index'))['index__max']
            new_index = 1 if max_index is None else max_index + 1
            serializer.save(index=new_index)
        else:
            serializer.save()

# --- 插图管理 API ---
class IllustrationManageViewSet(viewsets.ModelViewSet):
    queryset = Illustration.objects.all()
    serializer_class = IllustrationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, IsUploaderOrSuperUser]

    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        user = self.request.user
        if not user.is_superuser and book.uploader != user:
            raise serializers.ValidationError("你无权向这本书添加插图。")
        
        if 'index' not in serializer.validated_data:
            # 查这本书、这一卷下的最大索引
            volume_name = serializer.validated_data.get('volume_name', '')
            max_index = Illustration.objects.filter(
                book=book, 
                volume_name=volume_name
            ).aggregate(Max('index'))['index__max']
            new_index = 1 if max_index is None else max_index + 1
            serializer.save(index=new_index)
        else:
            serializer.save()

class GlobalSettingsViewSet(viewsets.GenericViewSet):
    """
    系统设置管理。
    只允许 GET (查看) 和 PUT/PATCH (修改)。
    """
    serializer_class = GlobalSettingsSerializer
    permission_classes = [IsSuperUser] # 仅超管
    # 获取设置 (GET /api/admin/settings/)
    def list(self, request):
        settings = GlobalSettings.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    # 修改设置 (POST /api/admin/settings/update/)
    # 也可以设计为 PUT /api/admin/settings/，这里为了贴合你的需求路径
    @action(detail=False, methods=['post', 'put', 'patch'], url_path='update')
    def update_settings(self, request):
        settings = GlobalSettings.load()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- 用户管理 API ---
class UserAdminViewSet(viewsets.ModelViewSet):
    """
    用户管理：增删改查。
    包含封禁功能。
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsSuperUser] # 仅超管
    # 自定义动作：封禁用户 (POST /api/admin/users/{id}/ban/)
    @action(detail=True, methods=['post'])
    def ban(self, request, pk=None):
        user = self.get_object()
        
        # 防止自杀 (超管不能封禁自己)
        if user == request.user:
            return Response({"error": "你不能封禁自己。"}, status=status.HTTP_400_BAD_REQUEST)
            
        # 封禁逻辑：将 is_active 设为 False
        user.is_active = False
        user.save()
        return Response({"status": f"用户 {user.username} 已被封禁。"})
    # 自定义动作：解封用户 (POST /api/admin/users/{id}/unban/)
    @action(detail=True, methods=['post'])
    def unban(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({"status": f"用户 {user.username} 已解封。"})