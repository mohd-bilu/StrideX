from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("User_panel.Authentication.urls")),
    path("products/", include(("User_panel.Product.urls", "product"), namespace="product")),
    path("cart/",include("User_panel.Cart.urls")),
    path("checkout/", include(("User_panel.Checkout.urls", "checkout"), namespace="checkout")),
    path("order/", include("User_panel.Order.urls")),
    path("wallet/", include("User_panel.Wallet.urls")),
    path("accounts/", include("allauth.urls")),

    path("admin-panel/", include("Admin_panel.Admin_account.urls")),
    path("admin-panel/categories/", include("Admin_panel.category.urls")),
    path("admin-panel/products/",include("Admin_panel.product.urls")),
    path("admin-panel/orders/", include("Admin_panel.order.urls")),
    path("admin-panel/coupons/", include("Admin_panel.coupon_offer.urls")),
    path("admin-panel/sales-report/", include("Admin_panel.sales_report.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

handler400 = "StrideX.views.error_400"
handler403 = "StrideX.views.error_403"
handler404 = "StrideX.views.error_404"
handler500 = "StrideX.views.error_500"