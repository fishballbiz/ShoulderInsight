from django.db import models
from django.contrib.auth.models import AbstractUser

class Clinic(models.Model):
    """
    Clinic model (診所).
    """
    name = models.CharField(max_length=255, verbose_name='診所名稱')

    class Meta:
        verbose_name = '診所'
        verbose_name_plural = '診所'

    def __str__(self):
        return self.name

class Role(models.Model):
    """
    Role model (角色).
    """
    name = models.CharField(max_length=50, unique=True, verbose_name='角色名稱')
    description = models.TextField(blank=True, verbose_name='描述')
    is_therapist = models.BooleanField(default=False, verbose_name='是否為治療師')

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色'

    def __str__(self):
        return self.name

class User(AbstractUser):
    """
    Custom user model (使用者).
    """
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name='角色')
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name='診所')

    class Meta:
        verbose_name = '使用者'
        verbose_name_plural = '使用者'

    def __str__(self):
        return self.username
