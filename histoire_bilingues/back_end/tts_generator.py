from gtts import gTTS
from io import BytesIO

# Fonction de génération audio (FR, EN, ES)
def generate_tts_audio(text: str, lang: str = "fr") -> BytesIO:
    try:
        tts = gTTS(text=text, lang=lang)
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp
    except Exception as e:
        raise RuntimeError(f"Erreur lors de la génération audio : {e}") 