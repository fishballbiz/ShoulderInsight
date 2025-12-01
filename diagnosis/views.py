
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Patient, Examination, Image
from datetime import datetime

def upload_view(request):
    """
    Upload page for examination images.
    """
    if request.method == 'POST':
        patient_name = request.POST.get('patient_name')
        
        if not patient_name:
            messages.error(request, '請輸入病患姓名')
            return redirect('diagnosis:upload')
        
        # Get or create patient
        patient, created = Patient.objects.get_or_create(name=patient_name)
        
        # Create examination
        # Note: therapist should be request.user when authentication is implemented
        examination = Examination.objects.create(
            patient=patient,
            therapist=None,  # TODO: Set to request.user when auth is ready
            status='PROCESSING'
        )
        
        # Handle uploaded images
        slots = {
            'slot_a': 'SLOT_A',
            'slot_b': 'SLOT_B',
            'slot_c': 'SLOT_C',
        }
        
        uploaded_count = 0
        for field_name, slot_type in slots.items():
            file = request.FILES.get(field_name)
            if file:
                Image.objects.create(
                    examination=examination,
                    image=file,
                    slot_type=slot_type
                )
                uploaded_count += 1
        
        if uploaded_count == 0:
            messages.error(request, '請至少上傳一張圖片')
            examination.delete()
            return redirect('diagnosis:upload')
        
        # Redirect to analyzing page
        return redirect('diagnosis:analyzing', examination_id=examination.id)
    
    return render(request, 'diagnosis/upload.html')

def analyzing_view(request, examination_id):
    """
    Analyzing page with loading animation.
    """
    examination = get_object_or_404(Examination, id=examination_id)
    return render(request, 'diagnosis/analyzing.html', {
        'examination': examination,
        'examination_id': examination_id
    })

def result_view(request, examination_id):
    # Mock data for demonstration
    mock_data = {
        'patient': {
            'name': '陳大明',
            'id': 'P-2024-001',
            'age': 45,
            'gender': '男',
            'date': datetime.now().strftime("%Y-%m-%d"),
        },
        'risk_assessment': {
            'level': 'High',  # Low, Medium, High
            'score': 85,
            'color': '#ff4d4d', # Red for high risk
            'label': '高風險'
        },
        'metrics': [
            {'name': '肩關節活動度 (ROM)', 'value': '120°', 'status': 'Warning', 'trend': 'down'},
            {'name': '疼痛指數 (VAS)', 'value': '7/10', 'status': 'Critical', 'trend': 'up'},
            {'name': '動作流暢度', 'value': '65%', 'status': 'Warning', 'trend': 'flat'},
            {'name': '復健達成率', 'value': '40%', 'status': 'Critical', 'trend': 'down'},
        ],
        'ai_analysis': {
            'summary': '根據上傳的復健數據分析，患者目前的肩部活動度受限明顯，且疼痛指數偏高。熱圖顯示三角肌区域有明顯的代償性用力，建議調整復健強度，避免過度代償導致二次傷害。',
            'recommendations': [
                '暫停高強度的舉手動作，改為被動關節活動。',
                '加強肩胛骨穩定肌群的訓練。',
                '建議進行超音波檢查以排除旋轉肌袖撕裂的可能性。'
            ]
        }
    }
    return render(request, 'diagnosis/result.html', {'examination_id': examination_id, 'data': mock_data})
