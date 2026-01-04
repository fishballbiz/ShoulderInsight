"""
AI service for Gemini image analysis using Google GenAI SDK.
"""
import json
import logging
from pathlib import Path

from google import genai
from google.genai import types

from .prompts import get_extraction_prompt

logger = logging.getLogger(__name__)

API_KEY_PATH = Path(__file__).parent.parent / 'secret' / 'gemini_api.key'
MODEL_NAME = 'gemini-2.5-flash'


def _get_client() -> genai.Client:
    """Create and return a GenAI client."""
    api_key = API_KEY_PATH.read_text().strip()
    return genai.Client(api_key=api_key)


def analyze_training_image(image_path: str) -> dict:
    """
    Analyze a training result image using Gemini.

    Args:
        image_path: Path to the image file.

    Returns:
        Parsed JSON response from Gemini or error dict.
    """
    try:
        client = _get_client()

        image_data = Path(image_path).read_bytes()

        # Determine mime type from extension
        ext = Path(image_path).suffix.lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }.get(ext, 'image/jpeg')

        prompt = get_extraction_prompt()

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Part.from_bytes(data=image_data, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
            )
        )

        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            response_text = '\n'.join(lines)

        return json.loads(response_text)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return {'error': f'Invalid JSON response: {e}'}
    except FileNotFoundError:
        logger.error(f"API key file not found: {API_KEY_PATH}")
        return {'error': 'API key not configured'}
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {'error': str(e)}
