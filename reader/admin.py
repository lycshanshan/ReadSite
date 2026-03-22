from django.contrib import admin, messages
from django.urls import path
from django.utils.html import format_html

from .models import *
from .services import BookDownloadService


admin.site.register(UserProgress)
admin.site.register(Bookshelf)
admin.site.register(UserPoints)
admin.site.register(Bookmark)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'uploader', 'created_at', 'download_button')
    search_fields = ('title', 'author')
    list_filter = ('created_at',)
    actions = ['batch_download_books']

    def save_model(self, request, obj, form, change):
        """新增书籍时，如果没有指定上传者，自动绑定为当前用户"""
        if not obj.pk and not obj.uploader:
            obj.uploader = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        """普通 Staff 不能修改 uploader 字段，字数等统计字段强制只读"""
        readonly = ['word_count', 'illustration_count']
        if not request.user.is_superuser:
            readonly.append('uploader')
        return readonly

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        return True
    
    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.uploader == request.user

    def has_delete_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.uploader == request.user
    
    @admin.action(description="批量下载")
    def batch_download_books(self, request, queryset):
        return BookDownloadService.generate_multi_books_download_response(
            books=queryset, 
            need_text=True, 
            need_img=True
        )

    def download_button(self, obj):
        """
        下载按钮。
        format_html 防止 XSS 注入，生成一个直达下载路由的 a 标签
        """
        return format_html(
            '<a class="button" style="background-color:#2c3e50; color:white; padding:4px 8px; border-radius:4px;" href="{}/admin-download/">下载</a>',
            obj.pk
        )
    download_button.short_description = "下载书籍"
    
    def get_urls(self):
        """注册后台路由"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/admin-download/',
                self.admin_site.admin_view(self.download_book_view),
                name='book-admin-download',
            ),
        ]
        return custom_urls + urls

    def download_book_view(self, request, object_id):
        book = self.get_object(request, object_id)
        return BookDownloadService.generate_download_response(book, need_text=True, need_img=True)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('book', 'title', 'volume_name', 'index')
    list_filter = ('book',)
    search_fields = ('title', 'book__title')

    def get_readonly_fields(self, request, obj=None):
        """如果修改已存在的章节, 且不是超管, 则所属书籍禁止修改"""
        if obj and not request.user.is_superuser:
            return ('book',)
        return ()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """新增章节时, Staff 下拉框里只能看到自己上传的书"""
        if db_field.name == "book" and not request.user.is_superuser:
            kwargs["queryset"] = Book.objects.filter(uploader=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        return True
    
    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.book.uploader == request.user

    def has_delete_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.book.uploader == request.user


@admin.register(Illustration)
class IllustrationAdmin(admin.ModelAdmin):
    list_display = ('book', 'volume_name', 'index', 'image')
    list_filter = ('book',)
    search_fields = ('book__title',)
    
    # 逻辑与 Chapter 一致
    def get_readonly_fields(self, request, obj=None):
        """如果修改已存在的插图, 且不是超管, 则所属书籍禁止修改"""
        if obj and not request.user.is_superuser:
            return ('book',)
        return ()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """新增插图时, Staff 下拉框里只能看到自己上传的书"""
        if db_field.name == "book" and not request.user.is_superuser:
            kwargs["queryset"] = Book.objects.filter(uploader=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        return True
    
    def has_add_permission(self, request, obj=None):
        return True
    
    def has_change_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.book.uploader == request.user

    def has_delete_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.book.uploader == request.user


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    # 禁止添加新记录
    def has_add_permission(self, request):
        if GlobalSettings.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaffApplication)
class StaffApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at')
    list_filter = ('status',)
    actions = ['approve_applications', 'reject_applications']

    def has_module_permission(self, request):
        return request.user.is_superuser

    @admin.action(description="通过申请")
    def approve_applications(self, request, queryset):
        """将用户设为 staff 并更新申请状态"""
        for app in queryset.filter(status='pending'):
            user = app.user
            user.is_staff = True
            user.save()
            app.status = 'approved'
            app.save()
        self.message_user(request, "选中的申请已通过，相关用户已获得 Staff 权限。", messages.SUCCESS)
    
    @admin.action(description="拒绝申请")
    def reject_applications(self, request, queryset):
        """拒绝用户的 staff 申请并更新申请状态"""
        for app in queryset.filter(status='pending'):
            app.status = 'rejected'
            app.save()
        self.message_user(request, "选中的申请已被拒绝。", messages.SUCCESS)