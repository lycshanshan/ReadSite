import base64
from random import sample
from urllib.parse import unquote

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.http import JsonResponse, StreamingHttpResponse

from .models import *


def index(request):
    """
    处理首页的 GET 请求。
    功能：展示书籍列表（支持分页）、处理顶部搜索框的搜索请求、展示推荐书籍。
    """
    query = request.GET.get('q', '')
    if query:
        book_list = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ).order_by('-created_at')
        is_search = True
        recommended_books = []
    else:
        book_list = Book.objects.all().order_by('-created_at')

        # 推荐书籍取用逻辑：取前四本推荐书籍，若不满四本则从其他书籍中随机抽取，尽可能填满4本
        recommended_books = Book.objects.filter(is_recommended=True).order_by('-created_at')[:4]
        length_rec = recommended_books.count()
        if length_rec < 4:
            need = 4 - length_rec
            other_ids = list(Book.objects.exclude(is_recommended=True).values_list('id', flat=True))
            if len(other_ids) <= need:
                random_ids = other_ids
            else:
                random_ids = sample(other_ids, need)
            recommended_books = Book.objects.filter(
                Q(id__in=random_ids) | Q(is_recommended=True)
            ).order_by('-created_at')
        is_search = False

    paginator = Paginator(book_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,  # 分页后的书籍列表
        'recommended_books': recommended_books,  # 推荐书籍
        'is_search': is_search,  # 是否处于搜索状态
        'search_query': query,  # 搜索词回填
    }
    return render(request, 'index.html', context)


def book_detail(request, book_id):
    """
    处理书籍详情页请求。
    功能：章节按卷分组、插图检查、获取阅读进度和是否在书架
    """
    book = get_object_or_404(Book, pk=book_id)
    query = request.GET.get('q', '')

    chapters = book.chapters.all().order_by('index')
    if query:
        chapters = chapters.filter(title__icontains=query)
    first_chapter = chapters.first()

    # 将章节按卷名分组
    volumes = {}
    grouped_chapters = []

    for chapter in chapters:
        vol_name = chapter.volume_name
        if vol_name not in volumes:
            volumes[vol_name] = []
        volumes[vol_name].append(chapter)

    for volume_name, chapter_list in volumes.items():
        # 检查插图
        has_illustration = (query in f"{volume_name} 插图") and Illustration.objects.filter(book=book,
                                                                                            volume_name=volume_name).exists()
        grouped_chapters.append({
            'volume_name': volume_name,
            'chapters': chapter_list,
            'has_illustration': has_illustration,
        })

    # 获取阅读进度
    progress = None
    if request.user.is_authenticated:
        try:
            progress = UserProgress.objects.get(user=request.user, book=book)
        except UserProgress.DoesNotExist:
            pass

    # 检查是否在书架
    in_bookshelf = False
    if request.user.is_authenticated:
        in_bookshelf = Bookshelf.objects.filter(user=request.user, book=book).exists()

    context = {
        'book': book,
        'grouped_chapters': grouped_chapters,
        'first_chapter': first_chapter,
        'progress': progress,
        'in_bookshelf': in_bookshelf,
        'search_query': query,
    }
    return render(request, 'book_detail.html', context)


@login_required
def book_download(request, book_id):
    """
    处理小说下载请求。
    功能：价格计算、积分校验、扣费。
    GET请求返回价格信息到前端，POST请求扣费并下载。
    """
    book = get_object_or_404(Book, pk=book_id)
    user_points = get_object_or_404(UserPoints, user=request.user)

    # 计费规则：每 20 万字 1 积分，每 10 张插图 1 积分（保底 1 积分）
    text_price = max(book.word_count // 200000, 1)
    img_price = max(book.illustration_count // 10, 1)

    # 收到 POST 请求，表明用户确认支付并下载
    if request.method == 'POST':
        need_text = request.POST.get('need_text') == 'on' or book.illustration_count == 0
        need_img = request.POST.get('need_img') == 'on'
        if not need_text and not need_img:
            return JsonResponse({'status': 'fail', 'msg': '请至少选择一项下载内容！'})

        # 计算总金额、校验余额、扣费
        price = 0
        if need_text:
            price += text_price
        if need_img:
            price += img_price

        if user_points.point < price:
            return JsonResponse({'status': 'fail', 'msg': '积分不足！'})
        if price > 0:
            user_points.point -= price
            user_points.save()

        # 文件生成器
        def file_iterator():
            yield f"《{book.title}》\n作者：{book.author}\n\n".encode('utf-8')
            yield f"简介：\n{book.description}\n\n".encode('utf-8')

            chapters = book.chapters.all().order_by('index').iterator()
            vol_name = ''
            volumes = []

            for chapter in chapters:
                if chapter.volume_name != vol_name:
                    vol_name = chapter.volume_name
                    volumes.append(vol_name)

            if need_text:
                chapters = book.chapters.all().order_by('index').iterator()
                for chapter in chapters:
                    if chapter.volume_name != vol_name:
                        vol_name = chapter.volume_name
                        yield f"{'-' * 20}\n\n".encode('utf-8')
                        yield f"{vol_name}\n\n".encode('utf-8')
                    text = f"{chapter.title}\n\n{chapter.content}\n\n\n"
                    yield text.encode('utf-8')

            if need_img and book.illustration_count > 0:
                yield f"{'-' * 20}以下为小说插图，以base64编码形式展示{'-' * 20}\n\n"
                for volume in volumes:
                    vol_ills = Illustration.objects.filter(book=book, volume_name=volume).order_by('index').iterator()
                    yield f"{'-' * 20}{volume}{'-' * 20}\n\n"
                    for ill in vol_ills:
                        ill_path = ill.image.path
                        ill_index = ill.index
                        with open(ill_path, 'rb') as f:
                            image_data = f.read()
                            base64_str = base64.b64encode(image_data).decode('utf-8')
                            yield f"{'-' * 10}{volume} 插图{ill_index}{'-' * 10} start\n"
                            yield base64_str
                            yield f"\n{'-' * 10}{volume} 插图{ill_index}{'-' * 10} end\n"
                        yield "\n"
                    yield "\n\n"

        response = StreamingHttpResponse(file_iterator(), content_type='text/plain')
        suffix = ""
        if need_text and not need_img: suffix = "_text"
        if not need_text and need_img: suffix = "_img"
        filename = f"{book.id}{suffix}.txt"
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
        return response

    # 收到 GET 请求，返回价格信息给前端弹窗用
    return JsonResponse({
        'status': 'ok',
        'word_count': book.word_count,
        'illustration_count': book.illustration_count,
        'text_price': text_price,
        'img_price': img_price,
        'user_point': user_points.point
    })


def read_chapter(request, chapter_id):
    """
    处理阅读页面请求。
    功能：获取当前正文、下一章、上一章信息；保存阅读进度。
    """
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    book = chapter.book

    # 保存进度 (仅登录时)
    is_bookmarked = False
    if request.user.is_authenticated:
        UserProgress.objects.update_or_create(
            user=request.user,
            book=book,
            defaults={'chapter': chapter}
        )
        is_bookmarked = Bookmark.objects.filter(user=request.user, chapter=chapter).exists()

    # 查找上一章和下一章
    prev_chapter = Chapter.objects.filter(
        book=book,
        index__lt=chapter.index
    ).order_by('-index').first()
    next_chapter = Chapter.objects.filter(
        book=book,
        index__gt=chapter.index
    ).order_by('index').first()

    context = {
        'book': book,
        'chapter': chapter,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'read_chapter.html', context)


def view_illustration(request, book_id, volume_name):
    """
    处理插图页面请求。
    功能：展示某一分卷内的所有插图。
    """
    # URL 解码
    if volume_name == '_default_':
        volume_name = ""
    else:
        volume_name = unquote(volume_name)

    book = get_object_or_404(Book, pk=book_id)
    images = Illustration.objects.filter(book=book, volume_name=volume_name).order_by('index')

    context = {
        'book': book,
        'volume_name': volume_name,
        'images': images,
    }
    return render(request, 'illustration_gallery.html', context)


def signup(request):
    """
    用户注册视图，受 GlobalSettings (全站设置) 控制。
    """
    settings = GlobalSettings.load()
    mode = settings.registration_mode

    if mode == GlobalSettings.MODE_CLOSED:
        return render(request, 'signup_closed.html')

    # POST 请求为提交了注册表单，GET请求为访问页面
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        # 如果是邀请码模式，校验邀请码
        if mode == GlobalSettings.MODE_INVITE:
            user_code = request.POST.get('invite_code', '').strip()
            correct_code = settings.invite_code
            if user_code != correct_code:
                messages.error(request, "邀请码错误！")
                return render(request, 'signup.html', {
                    'form': form,
                    'mode': mode
                })

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form, 'mode': mode})


@login_required
def profile(request):
    user_points, created = UserPoints.objects.get_or_create(user=request.user)
    context = {
        'user': request.user,
        'user_points': user_points
    }
    return render(request, 'profile.html', context)


@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    return redirect('index')


def show_library(request):
    booklist = Book.objects.all().order_by('id')
    query = request.GET.get('q', '')

    if query:
        booklist = booklist.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query)
        )

    user_authenticated = request.user.is_authenticated

    booklist = [
    {
        'book': item,
        'shelved': Bookshelf.objects.filter(user=request.user, book=item.id).exists() if user_authenticated else False,
        'progress': UserProgress.objects.filter(user=request.user,book=item.id).first() if user_authenticated else None
    }for item in booklist]

    content = {'booklist': booklist,
               'search_query': query}
    return render(request, 'library.html', content)


# 书架列表页
@login_required
def my_bookshelf(request):
    """
    用户书架视图。
    功能：展示加入书架的书籍和阅读进度、书签。
    """
    query = request.GET.get('q', '')

    # 获取用户书架记录
    shelf_items = Bookshelf.objects.filter(user=request.user).select_related('book').order_by('-added_at')
    mark_items = Bookmark.objects.filter(user=request.user).select_related('chapter').order_by('-added_at')

    if query:
        shelf_items = shelf_items.filter(
            Q(book__title__icontains=query) |
            Q(book__author__icontains=query)
        )
        mark_items = mark_items.filter(
            Q(chapter__book__title__icontains=query) |
            Q(chapter__book__author__icontains=query) |
            Q(chapter__title__icontains=query)
        )

    # 查询阅读进度
    books_with_progress = []
    for item in shelf_items:
        book = item.book
        progress = UserProgress.objects.filter(user=request.user, book=book).first()
        books_with_progress.append({
            'book': book,
            'progress': progress,
        })

    content = {
        'books': books_with_progress,
        'marks': mark_items,
        'search_query': query,
    }

    return render(request, 'bookshelf.html', content)


# 加入/移出书架
@login_required
def toggle_bookshelf(request, book_id):
    """
    切换加入/移出书架状态（Toggle逻辑）。
    支持通过前端 AJAX 异步调用，或直接 HTML 表单提交。
    """
    book = get_object_or_404(Book, pk=book_id)
    shelf_item = Bookshelf.objects.filter(user=request.user, book=book).first()

    if shelf_item:
        shelf_item.delete()
        in_bookshelf = False
    else:
        Bookshelf.objects.create(user=request.user, book=book)
        in_bookshelf = True

    # 如果是 POST 请求，说明是前端 JS 发起的 AJAX，返回 JSON, 否则跳转回上一页
    if request.method == 'POST':
        return JsonResponse({
            'status': 'success',
            'in_bookshelf': in_bookshelf,
            'msg': "已加入书架" if in_bookshelf else "已移出书架"
        })
    return redirect(request.META.get('HTTP_REFERER', 'index'))


@login_required
def toggle_bookmark(request, chapter_id):
    """
    切换加入/移出书签状态，逻辑与书架相同。
    """
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    mark_item = Bookmark.objects.filter(user=request.user, chapter=chapter).first()

    if mark_item:
        mark_item.delete()
        in_bookmark = False
    else:
        Bookmark.objects.create(user=request.user, chapter=chapter)
        in_bookmark = True

    if request.method == 'POST':
        return JsonResponse({
            'status': 'success',
            'in_bookmark': in_bookmark,
            'msg': "已加入书签" if in_bookmark else "已移除书签"
        })
    return redirect(request.META.get('HTTP_REFERER', 'index'))


@login_required
@require_POST
def checkin(request):
    user_points, created = UserPoints.objects.get_or_create(user=request.user)

    now = timezone.now()
    if created or user_points.last_checkin_time.date() != now.date():
        # 增加积分和经验
        user_points.point += 10
        user_points.exp += 10
        user_points.last_checkin_time = now

        # 计算并更新等级
        exp = user_points.exp
        new_level = 'LV0'
        if exp > 1000:
            new_level = 'LV6'
        elif exp > 350:
            new_level = 'LV5'
        elif exp > 200:
            new_level = 'LV4'
        elif exp > 100:
            new_level = 'LV3'
        elif exp > 50:
            new_level = 'LV2'
        elif exp > 20:
            new_level = 'LV1'

        user_points.user_level = new_level
        user_points.save()
        return JsonResponse({
            'status': 'success',
            'msg': f'签到成功！积分+10，经验+10\n当前等级：{user_points.get_user_level_display()}',
            'current_point': user_points.point,
            'current_level_str': f"{user_points.get_user_level_display()}({user_points.exp}/{user_points.next_level_exp})"
        })
    else:
        return JsonResponse({'status': 'fail', 'msg': '今天已经签到过了，明天再来吧！'})
