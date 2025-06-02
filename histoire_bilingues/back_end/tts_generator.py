# Génère la voix en FR et autres
from gtts import gTTS
from io import BytesIO
import re

# Liste des langues supportées par gTTS
SUPPORTED_LANGS = {
    "fr": "Français",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "ar": "العربية"
}

# Fonction de nettoyage du texte
def clean_text_fortts(text: str) -> str:
    text = re.sub(r'^#{1,6}\s', '', text, flags=re.MULTILINE)
    text = re.sub(r'[*_]+', '', text)
    text = text.replace('`', '')
    text = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

# Fonction de génération TTS

def generate_tts_audio(text: str, lang: str = "fr") -> BytesIO:
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"Langue non supportée : {lang}")

    cleaned = clean_text_fortts(text)
    tts = gTTS(text=cleaned, lang=lang)
    buffer = BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer
