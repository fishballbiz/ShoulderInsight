import logging
import os
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from .ai_service import analyze_training_image
from .disease_mapping import find_matching_diseases, get_all_diseases
from .image_processing.cell_analyzer import process_image

logger = logging.getLogger(__name__)


def upload_view(request):
    """
    Upload page for single examination image.
    Stores image path and operator name in session.
    """
    if request.method == 'POST':
        operator_name = request.POST.get('operator_name')
        image_file = request.FILES.get('image')

        print(f"POST: operator={operator_name}, FILES={list(request.FILES.keys())}, POST={list(request.POST.keys())}")

        if not operator_name:
            messages.error(request, '請輸入操作者姓名')
            return redirect('diagnosis:upload')

        if not image_file:
            messages.error(request, '請上傳一張圖片')
            return redirect('diagnosis:upload')

        # Generate unique ID for this analysis
        examination_id = str(uuid.uuid4())

        # Save image to media folder
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(image_file.name)[1]
        filename = f"{examination_id}{ext}"
        image_path = os.path.join(upload_dir, filename)

        with open(image_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # Store in session
        request.session['examination_id'] = examination_id
        request.session['operator_name'] = operator_name
        request.session['image_path'] = image_path
        request.session['ai_result'] = None

        return redirect('diagnosis:analyzing', examination_id=examination_id)

    return render(request, 'diagnosis/upload.html')


def analyzing_view(request, examination_id):
    """
    Analyzing page - displays loading animation.
    AI analysis is triggered via AJAX from the frontend.
    """
    session_exam_id = request.session.get('examination_id')
    if session_exam_id != str(examination_id):
        messages.error(request, '無效的分析請求')
        return redirect('diagnosis:upload')

    if request.session.get('ai_result'):
        return redirect('diagnosis:result', examination_id=examination_id)

    return render(request, 'diagnosis/analyzing.html', {
        'examination_id': examination_id
    })


@require_POST
def analyze_api(request, examination_id):
    """
    API endpoint to trigger AI analysis.
    Returns JSON with success status and redirect URL.
    """
    session_exam_id = request.session.get('examination_id')
    if session_exam_id != str(examination_id):
        return JsonResponse({'error': '無效的分析請求'}, status=400)

    if request.session.get('ai_result'):
        return JsonResponse({
            'success': True,
            'redirect_url': f'/diagnosis/result/{examination_id}/'
        })

    image_path = request.session.get('image_path')
    if not image_path or not os.path.exists(image_path):
        return JsonResponse({'error': '找不到上傳的圖片'}, status=400)

    try:
        ai_result = analyze_training_image(image_path)
        request.session['ai_result'] = ai_result
        return JsonResponse({
            'success': True,
            'redirect_url': f'/diagnosis/result/{examination_id}/'
        })
    except Exception as e:
        logger.exception("AI analysis failed")
        request.session['ai_result'] = {'error': str(e)}
        return JsonResponse({
            'success': True,
            'redirect_url': f'/diagnosis/result/{examination_id}/'
        })


def result_view(request, examination_id):
    """
    Result page displaying diagnosis results.
    """
    session_exam_id = request.session.get('examination_id')
    if session_exam_id != str(examination_id):
        messages.error(request, '無效的分析請求')
        return redirect('diagnosis:upload')

    operator_name = request.session.get('operator_name', '未知')
    raw_data = request.session.get('ai_result', {})
    has_error = 'error' in raw_data

    # Find matching diseases
    matched_diseases = []
    if not has_error:
        matched_diseases = find_matching_diseases(raw_data)

    context = {
        'examination_id': examination_id,
        'operator_name': operator_name,
        'raw_data': raw_data,
        'has_error': has_error,
        'matched_diseases': matched_diseases,
    }

    return render(request, 'diagnosis/result.html', context)


def diseases_view(request):
    """
    Display all supported diseases with grid patterns and descriptions.
    """
    diseases = get_all_diseases()
    return render(request, 'diagnosis/diseases.html', {'diseases': diseases})


def grid_poc_view(request):
    """
    Proof of concept page for grid detection testing.
    Processes test images and displays detection results.
    """
    import base64
    import cv2
    from pathlib import Path

    test_images_dir = Path(settings.BASE_DIR) / 'data' / 'test_inputs'
    results = []

    if test_images_dir.exists():
        for image_path in sorted(test_images_dir.glob('*.jpeg'))[:6]:
            result = process_image(str(image_path))

            if 'error' in result:
                results.append({
                    'filename': image_path.name,
                    'error': result['error']
                })
            else:
                # Encode visualization as base64
                viz = result['visualization']
                _, buffer = cv2.imencode('.jpg', viz)
                viz_base64 = base64.b64encode(buffer).decode('utf-8')

                # Also encode original for comparison
                original = cv2.imread(str(image_path))
                _, orig_buffer = cv2.imencode('.jpg', original)
                orig_base64 = base64.b64encode(orig_buffer).decode('utf-8')

                results.append({
                    'filename': image_path.name,
                    'original_base64': orig_base64,
                    'visualization_base64': viz_base64,
                    'grid_info': {
                        'bounds': result['grid_info']['bounds'],
                        'cell_size': result['grid_info']['cell_size']
                    },
                    'grid_color': result['analysis']['grid_color'],
                    'grid_size': result['analysis']['grid_size'],
                    'cell_details': result['analysis']['cell_details']
                })

    return render(request, 'diagnosis/grid_poc.html', {'results': results})
