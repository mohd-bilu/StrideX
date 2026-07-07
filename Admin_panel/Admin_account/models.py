from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone


class AdminPasswordResetOTP(models.Model):
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_password_reset_otps"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expired_at:
            self.expired_at = timezone.now() + timedelta(minutes=2)

        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() >= self.expired_at

    def __str__(self):
        return f"{self.admin.email} - {self.code}"