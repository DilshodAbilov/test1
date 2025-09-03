from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)  # API orqali admin (test yaratadi, natijalarni ko‘radi)
    is_user = models.BooleanField(default=False)   # Oddiy user (test ishlaydi, faqat o‘z natijasini ko‘radi)

    def __str__(self):
        if self.is_superuser:
            return f"{self.username} (Superuser)"
        elif self.is_admin:
            return f"{self.username} (Admin)"
        elif self.is_user:
            return f"{self.username} (User)"
        return self.username
