from rest_framework import permissions

class IsSuperUser(permissions.BasePermission):
    """
    允许超级管理员进行任何操作
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)

class IsUploaderOrSuperUser(permissions.BasePermission):
    """
    对象级权限：
    1. 超级管理员可以操作任何对象。
    2. 普通员工只能操作自己上传的对象。
    """
    def has_object_permission(self, request, view, obj):
        # 如果是超级管理员，直接通行
        if request.user.is_superuser:
            return True
        
        # 检查对象是否属于当前用户
        # 注意：这里假设 obj 是 Book 实例，或者有 uploader 属性，或者能关联到 Book
        
        # 情况 A: 操作的是 Book 对象
        if hasattr(obj, 'uploader'):
            return obj.uploader == request.user
            
        # 情况 B: 操作的是 Chapter 或 Illustration (它们通过 .book 关联)
        if hasattr(obj, 'book') and hasattr(obj.book, 'uploader'):
            return obj.book.uploader == request.user
            
        return False
