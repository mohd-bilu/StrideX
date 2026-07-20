from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("User_panel.Authentication.urls")),
    path("products/", include(("User_panel.Product.urls", "product"), namespace="product")),

    path("accounts/", include("allauth.urls")),

    path("admin-panel/", include("Admin_panel.Admin_account.urls")),
    path("admin-panel/categories/", include("Admin_panel.category.urls")),
    path("admin-panel/products/",include("Admin_panel.product.urls"),),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )