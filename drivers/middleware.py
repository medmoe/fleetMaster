# middleware.py
from django.utils.deprecation import MiddlewareMixin


class DriverAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware that processes driver authentication cookies
    """

    def process_request(self, request):
        # If the driver_access cookie is present, add it to the Authorization header
        if 'driver_access' in request.COOKIES and 'Authorization' not in request.headers:
            token = request.COOKIES.get('driver_access')
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
