from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Patient, Examination, Image

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
            status='PENDING'
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
        
        messages.success(request, f'成功上傳 {uploaded_count} 張圖片！檢查 ID: {examination.id}')
        # TODO: Redirect to result page when implemented
        return redirect('diagnosis:upload')
    
    return render(request, 'diagnosis/upload.html')
