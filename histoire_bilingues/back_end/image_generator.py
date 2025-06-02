import requests
import os
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Charger les variables d’environnement
load_dotenv()

CLIPDROP_API_KEY = os.getenv("CLIPDROP_API_KEY")

def generate_image_from_prompt(prompt: str) -> Image.Image:
    """
    Génère une image à partir d’un prompt via l’API ClipDrop.
    """
    response = requests.post(
        'https://clipdrop-api.co/text-to-image/v1',
        files={'prompt': (None, prompt, 'text/plain')},
        headers={'x-api-key': CLIPDROP_API_KEY}
    )

    if not response.ok:
        raise RuntimeError(f"❌ Erreur ClipDrop : {response.status_code} - {response.text}")

    return Image.open(BytesIO(response.content))

def split_story_to_chunks(story, n=2):
    """
    Découpe l’histoire en `n` parties approximativement égales pour illustrer chaque scène.
    """
    import math
    length = len(story)
    chunk_size = math.ceil(length / n)
    return [story[i:i + chunk_size] for i in range(0, length, chunk_size)]

def generate_image_prompt(text: str) -> str:
    """
    Transforme un passage d’histoire en prompt illustratif (style enfant, sans texte visible).
    """
    base_prompt = (
        "A beautiful children's storybook illustration with soft pastel colors and a cute, dreamy style. "
        "Do not include any text, words, characters, numbers, letters, or symbols. "
        "No captions, no speech bubbles, no writing, no logos, no watermarks. "
        "Just a clean visual scene. Scene: "
    )
    return base_prompt + text.strip()[:200]
