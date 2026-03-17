"""
URL configuration for novel_proj project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from reader import views, api_views

# ViewSet 路由
router = DefaultRouter()
router.register(r'admin/books', api_views.BookManageViewSet)
router.register(r'admin/chapters', api_views.ChapterManageViewSet)
router.register(r'admin/illustrations', api_views.IllustrationManageViewSet)
router.register(r'admin/settings', api_views.GlobalSettingsViewSet, basename='settings')
router.register(r'admin/users', api_views.UserAdminViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('book/<int:book_id>/download/', views.book_download, name='book_download'),
    path('read/<int:chapter_id>/', views.read_chapter, name='read_chapter'),
    path('illustration/<int:book_id>/<str:volume_name>/', views.view_illustration, name='view_illustration'),

    # 引入 Django 自带的认证 URL，自动处理 login, logout, password_change 等路由
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 注册页面
    path('signup/', views.signup, name='signup'),

    path('library/', views.show_library, name='show_library'),

    # 个人中心页面
    path('profile/', views.profile, name='profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('checkin/', views.checkin, name='checkin'),

    # 书架
    path('bookshelf/', views.my_bookshelf, name='my_bookshelf'),
    path('bookshelf/toggle/<int:book_id>/', views.toggle_bookshelf, name='toggle_bookshelf'),
    path('bookmark/toggle/<int:chapter_id>/', views.toggle_bookmark, name='toggle_bookmark'),

    # API
    path('api/', include(router.urls)),
    # 下载 Schema 文件的接口
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Redoc UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# 开发模式下，让浏览器能直接访问到上传的图片
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)