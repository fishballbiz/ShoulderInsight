from django.contrib import admin
from .models import Patient, Examination, Image, Diagnosis

class ImageInline(admin.TabularInline):
    model = Image
    extra = 0
    readonly_fields = ('uploaded_at',)

class DiagnosisInline(admin.StackedInline):
    model = Diagnosis
    can_delete = False
    verbose_name_plural = '診斷結果'

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'birth_date', 'created_at')
    search_fields = ('name', 'phone')

@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'therapist', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'therapist')
    search_fields = ('patient__name', 'therapist__username', 'therapist__email')
    inlines = [ImageInline, DiagnosisInline]
    readonly_fields = ('id', 'created_at')

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('examination', 'slot_type', 'uploaded_at')
    list_filter = ('slot_type', 'uploaded_at')
    search_fields = ('examination__patient__name',)

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ('examination', 'created_at')
    search_fields = ('examination__patient__name',)
