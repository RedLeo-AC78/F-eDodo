# Génère les images par IA (DALL·E / Stable Diffusion)
import requests
import os
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Charger les variables d’environnement
load_dotenv()

# Tokens API
HUGGINGFACE_API_TOKEN = os.getenv("HF_API_TOKEN")
CLIPDROP_API_KEY = os.getenv("CLIPDROP_API_KEY")

# URL pour Hugging Face
hf_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
hf_headers = {
    "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"
}

def generate_image_from_prompt(prompt: str, provider: str = "huggingface") -> Image.Image:
    """
    Génère une image à partir d’un prompt, via Hugging Face ou ClipDrop.
    - provider = "huggingface" (par défaut) ou "clipdrop"
    """
    if provider == "huggingface":
        response = requests.post(hf_api_url, headers=hf_headers, json={"inputs": prompt})
        if response.status_code == 503:
            raise RuntimeError("⏳ Le modèle est en cours de chargement. Réessaie dans quelques secondes.")
        elif response.status_code == 404:
            raise RuntimeError("❌ Modèle non trouvé sur Hugging Face.")
        elif response.status_code == 401:
            raise RuntimeError("🔐 Token Hugging Face invalide ou manquant.")
        elif response.status_code != 200:
            raise RuntimeError(f"❌ Erreur Hugging Face : {response.status_code} - {response.text}")
        return Image.open(BytesIO(response.content))

    elif provider == "clipdrop":
        response = requests.post(
            'https://clipdrop-api.co/text-to-image/v1',
            files={'prompt': (None, prompt, 'text/plain')},
            headers={'x-api-key': CLIPDROP_API_KEY}
        )
        if not response.ok:
            raise RuntimeError(f"❌ Erreur ClipDrop : {response.status_code} - {response.text}")
        return Image.open(BytesIO(response.content))

    else:
        raise ValueError("❗ Provider non supporté. Utilisez 'huggingface' ou 'clipdrop'.")

def split_story_to_chunks(story, n=5):
    """
    Découpe l’histoire en `n` parties approximativement égales pour illustrer chaque scène.
    """
    import math
    length = len(story)
    chunk_size = math.ceil(length / n)
    return [story[i:i + chunk_size] for i in range(0, length, chunk_size)]

def generate_image_prompt(text: str) -> str:
    """
    Transforme un passage d’histoire en prompt illustratif (style histoire pour enfants).
    """
    return f"Storybook illustration for children: {text.strip()[:200]}"
