from rest_framework import permissions

class IsSuperUser(permissions.BasePermission):
    """
    允许超级管理员进行任何操作
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)

class IsUploaderOrSuperUser(permissions.BasePermission):
    """
    超级管理员可以操作任何对象。
    普通员工只能操作自己上传的对象。
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if hasattr(obj, 'uploader'):
            return obj.uploader == request.user
        if hasattr(obj, 'book') and hasattr(obj.book, 'uploader'):
            return obj.book.uploader == request.user
        return False
