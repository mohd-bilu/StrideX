from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("User_panel.Authentication.urls")),
    path("products/", include(("User_panel.Product.urls", "product"), namespace="product")),
    path("cart/",include("User_panel.Cart.urls")),
    path("order/", include("User_panel.Order.urls")),

    path("accounts/", include("allauth.urls")),

    path("admin-panel/", include("Admin_panel.Admin_account.urls")),
    path("admin-panel/categories/", include("Admin_panel.category.urls")),
    path("admin-panel/products/",include("Admin_panel.product.urls")),
    path("admin-panel/orders/", include("Admin_panel.order.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )