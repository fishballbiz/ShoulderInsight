import logging
import os
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from .ai_service import analyze_training_image
from .disease_mapping import (
    accumulate_disease_scores,
    find_matching_diseases_by_hand,
    get_all_diseases,
)
from .image_processing import parse_grid, calibrate_from_samples, process_image

logger = logging.getLogger(__name__)


def upload_view(request):
    """Upload page for multiple examination images."""
    if request.method == 'POST':
        operator_name = request.POST.get('operator_name')
        image_files = request.FILES.getlist('image')

        if not operator_name:
            messages.error(request, '請輸入操作者姓名')
            return redirect('diagnosis:upload')

        if not image_files:
            messages.error(request, '請上傳至少一張圖片')
            return redirect('diagnosis:upload')

        examination_id = str(uuid.uuid4())

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        image_paths = []
        for idx, image_file in enumerate(image_files):
            ext = os.path.splitext(image_file.name)[1]
            filename = f"{examination_id}_{idx}{ext}"
            image_path = os.path.join(upload_dir, filename)

            with open(image_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)

            image_paths.append(image_path)

        request.session['examination_id'] = examination_id
        request.session['operator_name'] = operator_name
        request.session['image_paths'] = image_paths
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

    if request.session.get('accumulated_scores'):
        return redirect('diagnosis:result', examination_id=examination_id)

    image_count = len(request.session.get('image_paths', []))
    return render(request, 'diagnosis/analyzing.html', {
        'examination_id': examination_id,
        'image_count': image_count,
    })


@require_POST
def analyze_api(request, examination_id):
    """
    API endpoint to trigger batch AI analysis and grid parsing.
    Processes all uploaded images and accumulates scores.
    """
    session_exam_id = request.session.get('examination_id')
    if session_exam_id != str(examination_id):
        return JsonResponse({'error': '無效的分析請求'}, status=400)

    if request.session.get('accumulated_scores'):
        return JsonResponse({
            'success': True,
            'redirect_url': f'/diagnosis/result/{examination_id}/'
        })

    image_paths = request.session.get('image_paths', [])
    if not image_paths:
        return JsonResponse({'error': '找不到上傳的圖片'}, status=400)

    parsed_grids = []
    ai_results = []

    for image_path in image_paths:
        if not os.path.exists(image_path):
            continue

        parsed_result = parse_grid(image_path)
        stripped = {
            'success': parsed_result.get('success', False),
            'grid_color': parsed_result.get('grid_color', [None] * 81),
            'grid_size': parsed_result.get('grid_size', [0] * 81),
        }
        parsed_grids.append(stripped)

        try:
            ai_result = analyze_training_image(image_path)
            ai_results.append(ai_result)
        except Exception as e:
            logger.exception("AI analysis failed for %s", image_path)
            ai_results.append({'error': str(e)})

    accumulated = accumulate_disease_scores(parsed_grids)

    request.session['parsed_grids'] = parsed_grids
    request.session['ai_results'] = ai_results
    request.session['accumulated_scores'] = accumulated

    return JsonResponse({
        'success': True,
        'redirect_url': f'/diagnosis/result/{examination_id}/'
    })


def result_view(request, examination_id):
    """Result page displaying accumulated diagnosis results."""
    session_exam_id = request.session.get('examination_id')
    if session_exam_id != str(examination_id):
        messages.error(request, '無效的分析請求')
        return redirect('diagnosis:upload')

    operator_name = request.session.get('operator_name', '未知')
    ai_results = request.session.get('ai_results', [])
    accumulated = request.session.get('accumulated_scores', {})
    parsed_grids = request.session.get('parsed_grids', [])

    has_error = not any(g.get('success') for g in parsed_grids) if parsed_grids else True

    image_paths = request.session.get('image_paths', [])
    image_urls = []
    for path in image_paths:
        if path and os.path.exists(path):
            filename = os.path.basename(path)
            image_urls.append(f'{settings.MEDIA_URL}uploads/{filename}')

    left_hand = accumulated.get('left_hand', {
        'diseases': [], 'all_diseases': [], 'dot_count': 0
    })
    right_hand = accumulated.get('right_hand', {
        'diseases': [], 'all_diseases': [], 'dot_count': 0
    })
    merged_grid = accumulated.get('merged_grid', {
        'grid_color': [None] * 81, 'grid_size': [0] * 81
    })

    context = {
        'examination_id': examination_id,
        'operator_name': operator_name,
        'ai_results': ai_results,
        'has_error': has_error,
        'left_hand': left_hand,
        'right_hand': right_hand,
        'merged_grid': merged_grid,
        'image_urls': image_urls,
        'image_count': accumulated.get('image_count', len(image_paths)),
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
    calibration = None

    if test_images_dir.exists():
        image_paths = sorted(test_images_dir.glob('*.jpeg'))

        # Run calibration on all images
        calibration = calibrate_from_samples([str(p) for p in image_paths])

        # Process first 6 images for display
        for image_path in image_paths[:6]:
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

    return render(request, 'diagnosis/grid_poc.html', {
        'results': results,
        'calibration': calibration
    })
