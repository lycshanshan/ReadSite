from django.contrib import admin
from .models import Book, Chapter, UserProgress, Bookshelf, Illustration, GlobalSettings, UserPoints, Bookmark

admin.site.register(Book)
admin.site.register(Chapter)
admin.site.register(UserProgress)
admin.site.register(Bookshelf)
admin.site.register(Illustration)
admin.site.register(UserPoints)
admin.site.register(Bookmark)

@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    # 禁止添加新记录 (如果已经有一条的话)
    def has_add_permission(self, request):
        # 如果已经有记录了，就不能再点了
        if GlobalSettings.objects.exists():
            return False
        return True
    # 禁止删除
    def has_delete_permission(self, request, obj=None):
        return False