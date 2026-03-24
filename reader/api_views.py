from django.db.models import Max
from django.contrib.auth.models import User

from rest_framework import viewsets, status, serializers, renderers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action, renderer_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiTypes, inline_serializer

from .models import Book, Chapter, Illustration, GlobalSettings
from .serializers import (
    BookSerializer, ChapterSerializer, IllustrationSerializer,
    GlobalSettingsSerializer, UserAdminSerializer
)
from .permissions import IsSuperUser, IsUploaderOrSuperUser
from .services import BookDownloadService

    
class PassthroughRenderer(renderers.BaseRenderer):
    """
    透传渲染器：不做任何数据处理，直接返回。
    用于绕过 DRF 的内容协商，允许直接返回 FileResponse 或 StreamingHttpResponse。
    """
    media_type = '*/*'
    format = 'binary'
    charset = None
    render_style = 'binary'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


@extend_schema(tags=['书籍管理 (Admin)'])
class BookManageViewSet(viewsets.ModelViewSet):
    """
    书籍管理接口，提供书籍的增删改查。
    普通管理员只能操作自己上传的书籍，超级管理员可操作所有。
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, IsUploaderOrSuperUser]

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']

    @extend_schema(
        summary="上传书籍",
        description="创建一个新的书籍条目。创建者将自动被记录为该书的 uploader。",
        request=BookSerializer,
        responses={201: BookSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="获取书籍列表",
        description="获取所有书籍的列表。"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="查看书籍详情",
        description="获取指定 ID 书籍的详细信息。"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="修改书籍信息",
        description="修改书籍标题、简介或封面。仅限上传者或超管。"
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="删除书籍",
        description="删除书籍将级联删除其下所有章节和插图。仅限上传者或超管。"
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        # 保存时，自动将当前登录用户设为上传者
        serializer.save(uploader=self.request.user)
    
    # url_path='download' -> /api/admin/books/{id}/download/
    @extend_schema(
        summary="下载书籍 TXT",
        description="将整本书籍（含章节和插图）打包下载。若仅有文字，下载 TXT 文件; 否则下载 ZIP 文件。",
        responses={(200, 'application/octet-stream'): OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser], renderer_classes=[PassthroughRenderer])
    def download(self, request, pk=None):
        book = self.get_object()
        return BookDownloadService.generate_download_response(book, need_text=True, need_img=True)
    
    @extend_schema(
        summary="批量下载书籍",
        description="将多本书籍（含章节和插图）打包为一个 ZIP 文件下载。请在请求体中以 JSON 格式提供书籍 ID 列表。",
        request=inline_serializer(
            name="BatchDownloadRequest",
            fields={
                "ids": serializers.ListField(
                    child=serializers.IntegerField(),
                    help_text="书籍 ID 列表，例如: [1, 2, 3]",
                    allow_empty=False
                )
            }
        ),
        responses={(200, 'application/zip'): OpenApiTypes.BINARY}
    )
    @action(detail=False, methods=['post'], url_path='batch-download', permission_classes=[IsAdminUser], renderer_classes=[PassthroughRenderer])
    def batch_download(self, request):
        raw_ids = request.data.get('ids')
        ids = []

        if isinstance(raw_ids, str):
            try:
                # 分割字符串并转为整数
                ids = [int(i.strip()) for i in raw_ids.split(',') if i.strip()]
            except ValueError:
                return Response({"error": "ids 参数格式错误，必须是整数或逗号分隔的整数"}, status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(raw_ids, list):
            ids = raw_ids
        else:
            return Response({"error": "缺少 ids 参数"}, status=status.HTTP_400_BAD_REQUEST)
        
        books = self.get_queryset().filter(id__in=ids)
        if not books.exists():
            return Response(
                {"detail": "未找到匹配的书籍，或您没有权限下载这些书籍。"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        return BookDownloadService.generate_multi_books_download_response(
            books, 
            need_text=True, 
            need_img=True
        )


@extend_schema(tags=['章节管理 (Admin)'])
class ChapterManageViewSet(viewsets.ModelViewSet):
    """
    章节管理接口，提供章节的增删改查。
    普通管理员只能操作自己上传的书籍中的章节，超级管理员可操作所有。
    """
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, IsUploaderOrSuperUser]

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']

    @extend_schema(
        summary="上传章节",
        description="向指定书籍添加章节。如果 index 未填，将自动追加到最后。",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="修改章节内容")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
  
    @extend_schema(summary="删除章节")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        user = self.request.user
        
        # 权限校验
        if not user.is_superuser and book.uploader != user:
            raise serializers.ValidationError("你无权向这本书添加章节。")
            
        # 自动生成 index 为 max_index + 1
        if 'index' not in serializer.validated_data:
            max_index = Chapter.objects.filter(book=book).aggregate(Max('index'))['index__max']
            new_index = 1 if max_index is None else max_index + 1
            serializer.save(index=new_index)
        else:
            serializer.save()


@extend_schema(tags=['插图管理 (Admin)'])
class IllustrationManageViewSet(viewsets.ModelViewSet):
    """
    插图管理接口，提供插图的增删。
    普通管理员只能操作自己上传的书籍中的插图，超级管理员可操作所有。
    """
    queryset = Illustration.objects.all()
    serializer_class = IllustrationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, IsUploaderOrSuperUser]

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    @extend_schema(
        summary="上传插图",
        description="上传插图到指定书籍的指定卷。",
        request=IllustrationSerializer,
        responses={201: IllustrationSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(summary="删除插图")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        user = self.request.user

        # 权限校验
        if not user.is_superuser and book.uploader != user:
            raise serializers.ValidationError("你无权向这本书添加插图。")
        
        # 自动生成 index: 本书本卷下最大索引+1
        if 'index' not in serializer.validated_data:
            volume_name = serializer.validated_data.get('volume_name', '')
            max_index = Illustration.objects.filter(
                book=book, 
                volume_name=volume_name
            ).aggregate(Max('index'))['index__max']
            new_index = 1 if max_index is None else max_index + 1
            serializer.save(index=new_index)
        else:
            serializer.save()


@extend_schema(tags=['系统设置 (Superuser)'])
class GlobalSettingsViewSet(viewsets.GenericViewSet):
    """
    系统全局设置，仅限超级管理员操作。
    只允许 GET 和 PUT/PATCH 。
    """
    serializer_class = GlobalSettingsSerializer
    permission_classes = [IsSuperUser]

    @extend_schema(
        summary="查看当前设置",
        description="获取当前的注册模式和邀请码设置。",
        responses={200: GlobalSettingsSerializer}
    )
    def list(self, request):
        settings = GlobalSettings.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    @extend_schema(
        summary="修改全局设置",
        description="修改注册模式 (open/invite/closed) 或 邀请码。",
        request=GlobalSettingsSerializer,
        responses={200: GlobalSettingsSerializer}
    )
    @action(detail=False, methods=['post', 'put', 'patch'], url_path='update')
    def update_settings(self, request):
        settings = GlobalSettings.load()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['用户管理 (Superuser)'])
class UserAdminViewSet(viewsets.ModelViewSet):
    """
    用户管理接口：增删改查及封禁。
    仅限超级管理员操作。
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsSuperUser]

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']

    @extend_schema(summary="获取用户列表")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="创建管理员/用户",
        description="可以直接创建并指定是否为 staff (Admin)。"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="封禁用户",
        description="将用户状态设为 inactive，禁止登录。",
        responses={
            200: inline_serializer(
                name='UserBanResponse',
                fields={'status': serializers.CharField(), 'error': serializers.CharField(required=False)}
            )
        },
        request=None
    )
    @action(detail=True, methods=['post'])
    def ban(self, request, pk=None):
        user = self.get_object()
        
        if user == request.user:
            return Response({"error": "你不能封禁自己。"}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save()
        return Response({"status": f"用户 {user.username} 已被封禁。"})
    
    @extend_schema(
        summary="解封用户",
        description="恢复用户登录权限。",
        responses={
            200: inline_serializer(
                name='UserUnbanResponse',
                fields={'status': serializers.CharField()}
            )
        },
        request=None
    )
    @action(detail=True, methods=['post'])
    def unban(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({"status": f"用户 {user.username} 已解封。"})