from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import os

def image_upload_path(instance, filename):
    """
    Generate upload path with UUID filename.
    Format: uploads/YYYY/MM/DD/uuid.ext
    """
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4()}{ext}"
    now = timezone.now()
    return f"uploads/{now.strftime('%Y/%m/%d')}/{new_filename}"

class Patient(models.Model):
    """
    Patient model (病患).
    """
    name = models.CharField(max_length=255, verbose_name='姓名')
    gender = models.CharField(max_length=10, choices=[('M', '男'), ('F', '女'), ('O', '其他')], blank=True, verbose_name='性別')
    birth_date = models.DateField(null=True, blank=True, verbose_name='出生日期')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '病患'
        verbose_name_plural = '病患'

    def __str__(self):
        return self.name

class Examination(models.Model):
    """
    Examination model (檢查).
    """
    STATUS_CHOICES = [
        ('PENDING', '待處理'),
        ('PROCESSING', '處理中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失敗'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='檢查ID')
    therapist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='examinations', verbose_name='治療師', null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='examinations', verbose_name='病患')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='檢查時間')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='狀態')

    class Meta:
        verbose_name = '檢查'
        verbose_name_plural = '檢查'

    def __str__(self):
        return f"{self.patient.name} - {self.created_at.strftime('%Y-%m-%d')}"

class Image(models.Model):
    """
    Image model (圖檔).
    """
    SLOT_CHOICES = [
        ('SLOT_A', 'Slot A: 基本資料/訓練量'),
        ('SLOT_B', 'Slot B: 軌跡與熱圖'),
        ('SLOT_C', 'Slot C: 綜合分析'),
    ]

    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='images', verbose_name='檢查')
    image = models.ImageField(upload_to=image_upload_path, verbose_name='圖片')
    slot_type = models.CharField(max_length=10, choices=SLOT_CHOICES, verbose_name='圖片類型')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上傳時間')

    class Meta:
        verbose_name = '圖檔'
        verbose_name_plural = '圖檔'

    def __str__(self):
        return f"{self.examination.patient.name} - {self.get_slot_type_display()}"

class Diagnosis(models.Model):
    """
    Diagnosis model (診斷).
    """
    examination = models.OneToOneField(Examination, on_delete=models.CASCADE, related_name='diagnosis', verbose_name='檢查')
    raw_data = models.JSONField(default=dict, blank=True, verbose_name='原始數據')
    clinical_summary = models.TextField(blank=True, verbose_name='臨床摘要')
    risk_assessment = models.JSONField(default=dict, blank=True, verbose_name='風險評估')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='生成時間')

    class Meta:
        verbose_name = '診斷'
        verbose_name_plural = '診斷'

    def __str__(self):
        return f"Diagnosis for {self.examination.patient.name}"
