from django.shortcuts import redirect


class AdminUserSideRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/media/") or request.path.startswith("/static/"):
            return self.get_response(request)

        if request.user.is_authenticated:
            is_admin_path = request.path.startswith("/admin-panel/")
            is_django_admin_path = request.path.startswith("/admin/")

            if is_admin_path or is_django_admin_path:
                if not request.user.is_staff:
                    return redirect("home")
            else:
                if request.user.is_staff:
                    return redirect("admin_dashboard")

        return self.get_response(request)