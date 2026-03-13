from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Chapter, Illustration, GlobalSettings

class BookSerializer(serializers.ModelSerializer):
    """
    书籍模型序列化器。  
    字段：`id`, `title`, `author`, `description`, `cover`, `uploader`  
    只读字段：`id`, `uploader`
    """
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'description', 'cover', 'uploader']
        # uploader (上传者) 字段设为只读，由 API 视图在 perform_create 时自动绑定当前用户，防止伪造。
        read_only_fields = ['uploader', 'id']

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
        read_only_fields = ['date_joined'] # 账号注册时间不可修改

    def create(self, validated_data):
        """
        重写创建方法，确保用户密码被正确哈希加密。
        """
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password) # 使用 Django 内置方法进行哈希处理
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