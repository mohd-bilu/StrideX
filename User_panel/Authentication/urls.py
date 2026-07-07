from django.urls import path

from . import views


urlpatterns = [
    path("", views.signup, name="home"),
    path("signup/", views.signup, name="signup"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("home/", views.user_home, name="user_home"),

    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("forgot-password-verify-otp/", views.forgot_password_verify_otp, name="forgot_password_verify_otp"),
    path("forgot-password/resend-otp/", views.resend_forgot_password_otp, name="resend_forgot_password_otp"),
    path("reset-password/", views.reset_password, name="reset_password"),

    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),

    path("change-email/", views.change_email, name="change_email"),
    path("verify-email-otp/", views.verify_email_otp, name="verify_email_otp"),
    path("change-email/resend-otp/", views.resend_email_change_otp, name="resend_email_change_otp"),
    path("change-password/", views.change_password, name="change_password"),

    path("addresses/", views.address_list, name="address_list"),
    path("addresses/add/", views.add_address, name="add_address"),
    path("addresses/edit/<int:id>/", views.edit_address, name="edit_address"),
    path("addresses/delete/<int:id>/", views.delete_address, name="delete_address"),
    path("addresses/default/<int:id>/", views.make_default_address, name="make_default_address"),
]