from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, inline_serializer
from django.contrib.auth.models import User
from .models import Book, Chapter, Illustration, GlobalSettings, Tag, BookGroup


class BookSerializer(serializers.ModelSerializer):
    """
    书籍模型序列化器。  
    字段：`id`, `title`, `author`, `description`, `cover`, `tags`, `tag_names`, `uploader`, `recos`  
    只读字段：`id`, `uploader`, `tags`, `recos`  
    只写字段：`tag_names`
    - `tag_names` 字段接收传来的列表并处理标签的创建与绑定; `tag` 字段用于接口返回。
    """
    # 用于在接口返回时展示标签列表(只读)
    tags = serializers.SerializerMethodField(read_only=True)
    
    # 用于接收前端传来的标签数据(只写)
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
        help_text="传入标签名称的列表。不存在的标签将被自动创建。"
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'description', 'cover', 'tags', 'tag_names', 'uploader', 'recos']
        # uploader (上传者) 字段设为只读，由 API 视图在 perform_create 时自动绑定当前用户，防止伪造。
        read_only_fields = ['id', 'tags', 'uploader', 'recos']
    
    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_tags(self, obj):
        # 返回类似 ["魔法", "异世界"] 的格式
        return [tag.name for tag in obj.tags.all()]

    def _handle_tags(self, book, tag_names_data):
        """内部方法：处理标签的获取、创建与绑定"""
        if tag_names_data is not None:
            processed_tags = []
            # 处理 multipart/form-data 可能传来的逗号分隔字符串 
            for item in tag_names_data:
                for tag_name in item.split(','):
                    tag_name = tag_name.strip()
                    if tag_name:
                        processed_tags.append(tag_name)
            
            processed_tags = list(dict.fromkeys(processed_tags))
            processed_tags = processed_tags[:6]

            tag_objs = []
            for name in set(processed_tags):
                tag_obj, created = Tag.objects.get_or_create(name=name)
                tag_objs.append(tag_obj)

            book.tags.set(tag_objs)

    def create(self, validated_data):
        """
        重写创建方法, 处理书籍标签。
        """
        # 拦截 tag_names 并从 validated_data 中移除
        tag_names = validated_data.pop('tag_names', None)
        book = super().create(validated_data)
        self._handle_tags(book, tag_names)
        return book

    def update(self, instance, validated_data):
        """
        重写更新方法, 处理书籍标签。
        """
        tag_names = validated_data.pop('tag_names', None)
        book = super().update(instance, validated_data)
        if tag_names is not None:
            self._handle_tags(book, tag_names)
        return book


class ChapterSerializer(serializers.ModelSerializer):
    """
    章节模型序列化器。  
    字段：`id`, `book`, `title`, `content`, `index`, `volume_name`  
    只读字段：`id`
    """
    index = serializers.IntegerField(required=False)

    class Meta:
        model = Chapter
        fields = ['id', 'book', 'title', 'content', 'index', 'volume_name']
        read_only_fields = ['id']
    
    def update(self, instance, validated_data):
        """
        重写更新方法，增加业务安全逻辑。
        安全限制：禁止在更新章节时将其移动到其他书籍下。
        """
        validated_data.pop('book', None)
        return super().update(instance, validated_data)


class IllustrationSerializer(serializers.ModelSerializer):
    """
    插图模型序列化器。  
    字段：`id`, `book`, `image`, `index`, `volume_name`  
    只读字段：`id`
    """
    index = serializers.IntegerField(required=False)

    class Meta:
        model = Illustration
        fields = ['id', 'book', 'image', 'index', 'volume_name']
        read_only_fields = ['id']
    
    def update(self, instance, validated_data):
        """
        重写更新方法，增加业务安全逻辑。
        安全限制：禁止在更新插图时将其移动到其他书籍下
        """
        validated_data.pop('book', None)
        return super().update(instance, validated_data)


class BookGroupSerializer(serializers.ModelSerializer):
    """
    书单模型序列化器。  
    字段：`id`, `name`, `description`, `books`, `book_ids`, `updated_at`, `uploader`  
    只读字段：`id`, `uploader`, `books`, `updated_at`  
    只写字段：`book_ids`
    - `book_ids` 字段接收传来的书籍ID列表并处理绑定; `books` 字段用于接口返回书单内书籍的简要信息。
    """
    # 用于在接口返回时展示书籍列表详情(只读)
    books = serializers.SerializerMethodField(read_only=True)
    
    # 用于接收前端传来的书籍ID数据(只写)
    book_ids = serializers.ListField(
        child=serializers.CharField(), # 使用CharField以兼容 "1,2,3" 这种逗号分隔格式
        write_only=True,
        required=False,
        help_text="传入书籍ID的列表，支持逗号分隔的字符串。不存在的ID将被自动忽略。"
    )
    class Meta:
        model = BookGroup
        fields = ['id', 'name', 'description', 'books', 'book_ids', 'updated_at', 'uploader']
        # uploader 设为只读，由 API 视图在 perform_create 时自动绑定当前用户
        read_only_fields = ['id', 'books', 'uploader', 'updated_at']
    
    @extend_schema_field(serializers.ListField(
        child=inline_serializer(
            name="BookGroupItem",
            fields={"id": serializers.IntegerField(), "title": serializers.CharField()}
        )
    ))
    def get_books(self, obj):
        # 返回类似 [{"id": 1, "title": "书名1"}, {"id": 2, "title": "书名2"}] 的格式
        return [{"id": book.id, "title": book.title} for book in obj.books.all()]
    
    def _handle_books(self, group, book_ids_data):
        """内部方法：处理书籍ID的解析与绑定"""
        if book_ids_data is not None:
            processed_ids = []
            # 处理 multipart/form-data 可能传来的逗号分隔字符串
            for item in book_ids_data:
                for b_id in str(item).split(','):
                    b_id = b_id.strip()
                    if b_id.isdigit(): # 确保是合法的整数ID
                        processed_ids.append(int(b_id))
            
            # 去重
            processed_ids = list(dict.fromkeys(processed_ids))
            # 过滤出数据库中真实存在的书籍ID并绑定
            valid_books = Book.objects.filter(id__in=processed_ids)
            group.books.set(valid_books)
    
    def create(self, validated_data):
        """
        重写创建方法, 处理书单绑定的书籍。
        """
        book_ids = validated_data.pop('book_ids', None)
        group = super().create(validated_data)
        self._handle_books(group, book_ids)
        return group
    
    def update(self, instance, validated_data):
        """
        重写更新方法, 处理书单绑定的书籍。
        """
        book_ids = validated_data.pop('book_ids', None)
        group = super().update(instance, validated_data)
        if book_ids is not None:
            self._handle_books(group, book_ids)
        return group


class GlobalSettingsSerializer(serializers.ModelSerializer):
    """
    全局设置序列化器。  
    用于暴露和修改全站的注册策略（开放、关闭、邀请码）。  
    字段：`registration_mode`, `invite_code`
    """
    class Meta:
        model = GlobalSettings
        fields = ['registration_mode', 'invite_code']


class UserAdminSerializer(serializers.ModelSerializer):
    """
    后台用户管理序列化器。  
    仅供超级管理员使用，用于对用户账户进行全面管理（分配权限、重置密码、封禁等）。  
    字段：`id`, `username`, `password`, `is_active`, `is_staff`, `is_superuser`, `date_joined`  
    只读字段：`date_joined`  
    只写字段：`password`
    """
    # 密码字段只允许写入，禁止在 API 返回中暴露
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'is_active', 'is_staff', 'is_superuser', 'date_joined']
        read_only_fields = ['date_joined']  # 账号注册时间不可修改

    def create(self, validated_data):
        """
        重写创建方法，确保用户密码被正确哈希加密。
        """
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)  # 使用 Django 内置方法进行哈希处理
            user.save()
        return user
    
    def update(self, instance, validated_data):
        """
        重写更新方法，支持在修改用户信息时重置密码。
        """
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user