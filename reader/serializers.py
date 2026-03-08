from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Chapter, Illustration, GlobalSettings

# 书籍序列化器
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'description', 'cover', 'uploader']
        read_only_fields = ['uploader', 'id'] # 上传者由后端自动指定，不允许前端传

# 章节序列化器
class ChapterSerializer(serializers.ModelSerializer):
    index = serializers.IntegerField(required=False)
    class Meta:
        model = Chapter
        fields = ['id', 'book', 'title', 'content', 'index', 'volume_name']
        read_only_fields = ['id']
    def update(self, instance, validated_data):
        # 安全优化：禁止通过 API 修改章节所属的书籍
        validated_data.pop('book', None)
        return super().update(instance, validated_data)

# 插图序列化器
class IllustrationSerializer(serializers.ModelSerializer):
    index = serializers.IntegerField(required=False)
    class Meta:
        model = Illustration
        fields = ['id', 'book', 'image', 'index', 'volume_name']
        read_only_fields = ['id']
    def update(self, instance, validated_data):
        # 安全优化：禁止通过 API 修改插图所属的书籍
        validated_data.pop('book', None)
        return super().update(instance, validated_data)

# 全局设置序列化器
class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = ['registration_mode', 'invite_code']

# 用户管理序列化器
class UserAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = User
        # 允许超管修改这些字段
        fields = ['id', 'username', 'password', 'is_active', 'is_staff', 'is_superuser', 'date_joined']
        read_only_fields = ['date_joined'] # 注册时间不可改

    def create(self, validated_data):
        password = validated_data.pop('password', None) # 取出密码
        user = super().create(validated_data) # 先创建用户对象
        
        if password:
            user.set_password(password) # 加密密码
            user.save() # 再次保存
            
        return user
    # 重写 update 方法：允许修改密码
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        
        if password:
            user.set_password(password)
            user.save()
            
        return user