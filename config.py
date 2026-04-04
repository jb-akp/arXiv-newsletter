import os
from datetime import datetime, timedelta, timezone

# --- Search Config ---
TOPIC_TERMS = (
    '(ti:"talking head" OR ti:"talking avatar" OR ti:"talking face" OR '
    'ti:"audio driven face" OR ti:"speech driven animation" OR ti:"face reenactment" OR '
    'ti:"lip sync" OR ti:"neural avatar" OR '
    'ti:"audio-driven avatar" OR ti:"voice-driven avatar" OR ti:"head reenactment" OR '
    'ti:"portrait animation" OR ti:"video-driven avatar" OR '
    'ti:"facial animation" OR ti:"head synthesis" OR '
    'ti:"face synthesis" OR ti:"gaussian splatting face" OR ti:"neural radiance face" OR '
    'ti:"digital human" OR ti:"face generation" OR ti:"audio-visual speech")'
)
CAT_FILTER = '(cat:cs.CV OR cat:cs.GR OR cat:cs.MM OR cat:cs.AI)'

DATE_WINDOWS = [
    {'label': 'today', 'days_back_from': 1, 'days_back_to': 0, 'max': 15},
    {'label': 'week',  'days_back_from': 8, 'days_back_to': 1, 'max': 20},
    {'label': 'month', 'days_back_from': 30, 'days_back_to': 8, 'max': 20},
]

# --- Email Config ---
GMAIL_USER = os.environ.get('GMAIL_USER', '')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')
GMAIL_TO = os.environ.get('GMAIL_TO', 'william@akapulu.com')
GMAIL_SENDER_NAME = 'Akapulu Digital Humans Digest'

# --- Claude Config ---
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 16000
TEMPERATURE = 0.5

def date_str(days_back: int) -> str:
    d = datetime.now(timezone.utc) - timedelta(days=days_back)
    return d.strftime('%Y%m%d')
