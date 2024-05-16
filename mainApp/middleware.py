from django.shortcuts import redirect
from django.urls import reverse

class CheckPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated and not request.user.has_usable_password():
            if request.path != reverse('set_password'):
                return redirect('set_password')

        return response
