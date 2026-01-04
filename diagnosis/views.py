import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Patient, Examination, Image, Diagnosis
from .ai_service import analyze_training_image

logger = logging.getLogger(__name__)


def upload_view(request):
    """
    Upload page for single examination image.
    """
    if request.method == 'POST':
        operator_name = request.POST.get('operator_name')
        image_file = request.FILES.get('image')

        if not operator_name:
            messages.error(request, '請輸入操作者姓名')
            return redirect('diagnosis:upload')

        if not image_file:
            messages.error(request, '請上傳一張圖片')
            return redirect('diagnosis:upload')

        # Create a placeholder patient (will be identified from image later)
        patient, _ = Patient.objects.get_or_create(
            name='待辨識',
            defaults={'phone': '', 'gender': ''}
        )

        # Create examination
        examination = Examination.objects.create(
            patient=patient,
            therapist=None,
            status='PENDING'
        )

        # Store operator name in session
        request.session['operator_name'] = operator_name

        # Save the uploaded image
        Image.objects.create(
            examination=examination,
            image=image_file,
            slot_type='SLOT_A'
        )

        return redirect('diagnosis:analyzing', examination_id=examination.id)

    return render(request, 'diagnosis/upload.html')


def analyzing_view(request, examination_id):
    """
    Analyzing page - triggers AI analysis and displays loading animation.
    """
    examination = get_object_or_404(Examination, id=examination_id)

    # Check if analysis already done
    if hasattr(examination, 'diagnosis') and examination.diagnosis:
        return redirect('diagnosis:result', examination_id=examination_id)

    # Check if already processing
    if examination.status == 'PROCESSING':
        return render(request, 'diagnosis/analyzing.html', {
            'examination': examination,
            'examination_id': examination_id
        })

    # Start processing
    examination.status = 'PROCESSING'
    examination.save()

    # Get the uploaded image
    image_obj = examination.images.first()
    if not image_obj:
        examination.status = 'FAILED'
        examination.save()
        messages.error(request, '找不到上傳的圖片')
        return redirect('diagnosis:upload')

    # Call AI service
    try:
        image_path = image_obj.image.path
        ai_result = analyze_training_image(image_path)

        # Create diagnosis record
        if 'error' in ai_result:
            Diagnosis.objects.create(
                examination=examination,
                raw_data=ai_result,
                clinical_summary=f"分析失敗: {ai_result.get('error', '未知錯誤')}",
                risk_assessment={'error': True}
            )
            examination.status = 'FAILED'
        else:
            Diagnosis.objects.create(
                examination=examination,
                raw_data=ai_result,
                clinical_summary='AI 分析完成',
                risk_assessment={}
            )
            examination.status = 'COMPLETED'

        examination.save()
        return redirect('diagnosis:result', examination_id=examination_id)

    except Exception as e:
        logger.exception("AI analysis failed")
        examination.status = 'FAILED'
        examination.save()
        Diagnosis.objects.create(
            examination=examination,
            raw_data={'error': str(e)},
            clinical_summary=f"系統錯誤: {e}",
            risk_assessment={'error': True}
        )
        return redirect('diagnosis:result', examination_id=examination_id)


def result_view(request, examination_id):
    """
    Result page displaying diagnosis results.
    """
    examination = get_object_or_404(Examination, id=examination_id)
    operator_name = request.session.get('operator_name', '未知')

    # Get diagnosis data
    diagnosis = getattr(examination, 'diagnosis', None)
    raw_data = diagnosis.raw_data if diagnosis else {}

    # Check for error
    has_error = 'error' in raw_data

    context = {
        'examination_id': examination_id,
        'examination': examination,
        'operator_name': operator_name,
        'diagnosis': diagnosis,
        'raw_data': raw_data,
        'has_error': has_error,
    }

    return render(request, 'diagnosis/result.html', context)
