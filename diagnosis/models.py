from django.db import models
from django.conf import settings
import uuid

class DiagnosticEvent(models.Model):
    """
    Represents a diagnostic session for a patient.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    therapist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='diagnostic_events')
    patient_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"{self.patient_name} - {self.created_at.strftime('%Y-%m-%d')}"

class UploadedImage(models.Model):
    """
    Stores images uploaded for a diagnostic event.
    """
    SLOT_CHOICES = [
        ('SLOT_A', 'Slot A: Basic Info/Training Volume'),
        ('SLOT_B', 'Slot B: Trajectory & Heatmap'),
        ('SLOT_C', 'Slot C: Comprehensive Analysis'),
    ]

    event = models.ForeignKey(DiagnosticEvent, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='uploads/%Y/%m/%d/')
    slot_type = models.CharField(max_length=10, choices=SLOT_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event.patient_name} - {self.get_slot_type_display()}"

class AnalysisResult(models.Model):
    """
    Stores the AI analysis results for a diagnostic event.
    """
    event = models.OneToOneField(DiagnosticEvent, on_delete=models.CASCADE, related_name='result')
    raw_data = models.JSONField(default=dict, blank=True)
    clinical_summary = models.TextField(blank=True)
    risk_assessment = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.event.patient_name}"
