from django.db import models
from django.contrib.auth.models import AbstractUser

class Clinic(models.Model):
    """
    Clinic model to store hospital/clinic details.
    """
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Role(models.Model):
    """
    Role model to define user roles.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_therapist = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class User(AbstractUser):
    """
    Custom user model extending AbstractUser.
    """
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    def __str__(self):
        return self.username
