from django.contrib import admin
from .models import *

admin.site.register(Book)
admin.site.register(Chapter)
admin.site.register(UserProgress)
admin.site.register(Bookshelf)
admin.site.register(Illustration)
admin.site.register(UserPoints)
admin.site.register(Bookmark)
admin.site.register(Tag)

@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    # 禁止添加新记录
    def has_add_permission(self, request):
        if GlobalSettings.objects.exists():
            return False
        return True
    def has_delete_permission(self, request, obj=None):
        return False