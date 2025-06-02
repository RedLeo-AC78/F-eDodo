# back_end/translator.py
from deep_translator import GoogleTranslator

def translate_to_english(text):
    return GoogleTranslator(source='fr', target='en').translate(text)
