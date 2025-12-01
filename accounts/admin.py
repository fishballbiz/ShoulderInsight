from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, Clinic

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'clinic', 'is_staff')
    list_filter = ('role', 'clinic', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('專業資訊', {'fields': ('role', 'clinic')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('專業資訊', {'fields': ('role', 'clinic')}),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'clinic__name')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_therapist', 'description')
    list_filter = ('is_therapist',)
    search_fields = ('name',)

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
