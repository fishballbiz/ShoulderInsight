from django.contrib import admin
from .models import DiagnosticEvent, UploadedImage, AnalysisResult

class UploadedImageInline(admin.TabularInline):
    model = UploadedImage
    extra = 0
    readonly_fields = ('uploaded_at',)

class AnalysisResultInline(admin.StackedInline):
    model = AnalysisResult
    can_delete = False
    verbose_name_plural = 'Analysis Result'

@admin.register(DiagnosticEvent)
class DiagnosticEventAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'therapist', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'therapist')
    search_fields = ('patient_name', 'therapist__username', 'therapist__email')
    inlines = [UploadedImageInline, AnalysisResultInline]
    readonly_fields = ('id', 'created_at')

@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ('event', 'slot_type', 'uploaded_at')
    list_filter = ('slot_type', 'uploaded_at')
    search_fields = ('event__patient_name',)

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('event', 'created_at')
    search_fields = ('event__patient_name',)
