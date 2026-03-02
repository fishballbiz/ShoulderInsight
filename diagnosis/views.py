import base64
import json
import logging
import os
import random
import uuid
from pathlib import Path

import cv2
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .ai_service import analyze_training_image
from .disease_mapping import (
    accumulate_disease_scores,
    get_all_diseases,
    simulate_disease_scores,
)
from .image_processing import parse_grid, process_image

logger = logging.getLogger(__name__)


MAX_UPLOAD_FILES = 10
MAX_OPERATOR_NAME_LENGTH = 50
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG\r\n\x1a\n': 'png',
}


def _validate_image_magic_bytes(file_obj: object) -> bool:
    header = file_obj.read(8)
    file_obj.seek(0)
    return any(header.startswith(sig) for sig in MAGIC_BYTES)


def upload_view(request):
    """Upload page for multiple examination images."""
    if request.method == 'POST':
        operator_name = (
            request.POST.get('operator_name', '')[:MAX_OPERATOR_NAME_LENGTH]
        )
        image_files = request.FILES.getlist('image')

        if not operator_name.strip():
            messages.error(request, '請輸入操作者姓名')
            return redirect('diagnosis:upload')

        if not image_files:
            messages.error(request, '請上傳至少一張圖片')
            return redirect('diagnosis:upload')

        if len(image_files) > MAX_UPLOAD_FILES:
            messages.error(
                request, f'最多上傳 {MAX_UPLOAD_FILES} 張圖片'
            )
            return redirect('diagnosis:upload')

        for image_file in image_files:
            ext = os.path.splitext(image_file.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                messages.error(request, '僅支援 JPG、PNG 格式的圖片')
                return redirect('diagnosis:upload')
            if not _validate_image_magic_bytes(image_file):
                messages.error(request, '檔案內容不是有效的圖片格式')
                return redirect('diagnosis:upload')

        examination_id = str(uuid.uuid4())

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        image_paths = []
        for idx, image_file in enumerate(image_files):
            ext = os.path.splitext(image_file.name)[1].lower()
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
        request.session['accumulated_scores'] = None
        request.session['parsed_grids'] = None
        request.session['ai_results'] = None

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
        redirect_url = reverse(
            'diagnosis:result', kwargs={'examination_id': examination_id}
        )
        return JsonResponse({'success': True, 'redirect_url': redirect_url})

    image_paths = request.session.get('image_paths', [])
    if not image_paths:
        return JsonResponse({'error': '找不到上傳的圖片'}, status=400)

    parsed_grids = []
    ai_results = []

    for image_path in image_paths:
        if not os.path.exists(image_path):
            logger.warning("Image file missing: %s", image_path)
            continue

        try:
            parsed_result = parse_grid(image_path)
        except Exception as e:
            logger.exception("Grid parsing failed for %s", image_path)
            parsed_result = {
                'success': False,
                'grid_color': [None] * 81,
                'grid_size': [0] * 81,
            }

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

    if not parsed_grids:
        return JsonResponse({'error': '所有圖片處理失敗'}, status=500)

    accumulated = accumulate_disease_scores(parsed_grids)

    request.session['parsed_grids'] = parsed_grids
    request.session['ai_results'] = ai_results
    request.session['accumulated_scores'] = accumulated

    redirect_url = reverse(
        'diagnosis:result', kwargs={'examination_id': examination_id}
    )
    return JsonResponse({'success': True, 'redirect_url': redirect_url})


@never_cache
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

    empty_hand = {
        'possible_diseases': [],
        'attention_diseases': [],
        'all_diseases': [],
        'dot_count': 0,
    }
    left_hand = accumulated.get('left_hand', empty_hand)
    right_hand = accumulated.get('right_hand', empty_hand)
    merged_grid = accumulated.get('merged_grid', {
        'grid_color': [None] * 81, 'grid_size': [0] * 81
    })

    is_healthy = (
        not left_hand.get('possible_diseases')
        and not left_hand.get('attention_diseases')
        and not right_hand.get('possible_diseases')
        and not right_hand.get('attention_diseases')
    )

    health_tip = None
    if is_healthy:
        tips_path = os.path.join(settings.BASE_DIR, 'data', 'health_tips.json')
        with open(tips_path, 'r', encoding='utf-8') as f:
            tips = json.load(f)
        health_tip = random.choice(tips)

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
        'is_healthy': is_healthy,
        'health_tip': health_tip,
        'git_commit': settings.GIT_COMMIT,
    }

    return render(request, 'diagnosis/result.html', context)


def diseases_view(request):
    """
    Display all supported diseases with grid patterns and descriptions.
    """
    diseases = get_all_diseases()
    return render(request, 'diagnosis/diseases.html', {'diseases': diseases})


def analyze_verify_view(request):
    """
    Proof of concept page for grid detection testing.
    Processes test images and displays detection results.
    """
    test_images_dir = Path(settings.BASE_DIR) / 'data' / 'test_inputs'
    results = []

    if test_images_dir.exists():
        image_paths = sorted(test_images_dir.glob('*.jpeg'))

        for image_path in image_paths:
            result = process_image(str(image_path))

            if 'error' in result:
                results.append({
                    'filename': image_path.name,
                    'error': result['error']
                })
            else:
                viz = result['visualization']
                _, buffer = cv2.imencode('.jpg', viz)
                viz_base64 = base64.b64encode(
                    buffer
                ).decode('utf-8')

                original = cv2.imread(str(image_path))
                _, orig_buffer = cv2.imencode('.jpg', original)
                orig_base64 = base64.b64encode(
                    orig_buffer
                ).decode('utf-8')

                results.append({
                    'filename': image_path.name,
                    'original_base64': orig_base64,
                    'visualization_base64': viz_base64,
                    'grid_info': {
                        'bounds': result['grid_info']['bounds'],
                        'cell_size': (
                            result['grid_info']['cell_size']
                        ),
                    },
                    'grid_color': (
                        result['analysis']['grid_color']
                    ),
                    'grid_size': (
                        result['analysis']['grid_size']
                    ),
                    'cell_details': (
                        result['analysis']['cell_details']
                    ),
                })

    return render(request, 'diagnosis/analyze_verify.html', {
        'results': results,
    })


def score_simulator_view(request):
    """Score simulator page for interactive disease scoring."""
    diseases = get_all_diseases()
    return render(request, 'diagnosis/score_simulator.html', {
        'diseases': diseases,
    })


def _safe_int(value: str, default: int, min_val: int, max_val: int) -> int:
    try:
        n = int(value)
    except (ValueError, TypeError):
        return default
    return max(min_val, min(n, max_val))


@require_POST
def score_simulator_api(request):
    """API endpoint for score simulation via htmx."""
    try:
        user_grid = json.loads(
            request.POST.get('user_grid', '[]')
        )
    except (json.JSONDecodeError, TypeError):
        user_grid = [0] * 81
    if not isinstance(user_grid, list) or len(user_grid) != 81:
        user_grid = [0] * 81
    result = simulate_disease_scores(
        user_grid=user_grid,
        light_min=_safe_int(
            request.POST.get('light_min'), 4, 1, 99
        ),
        light_max=_safe_int(
            request.POST.get('light_max'), 8, 1, 99
        ),
        mild_max=_safe_int(
            request.POST.get('mild_max'), 18, 1, 99
        ),
    )
    for d in result['scored']:
        d['grid_color_json'] = json.dumps(d['grid_color'])
    return render(
        request, 'diagnosis/_score_results.html', result,
    )
