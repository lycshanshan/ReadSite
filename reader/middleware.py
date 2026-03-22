from django.shortcuts import redirect
from django.urls import reverse

class AdminAccessMiddleware:
    """
    拦截普通用户访问 /admin/
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if request.user.is_authenticated and not request.user.is_staff:
                return redirect('joinus')
        
        response = self.get_response(request)
        return response