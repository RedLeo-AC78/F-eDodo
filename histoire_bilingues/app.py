# Fichier principal Streamlit (point d'entrée)

import os
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS

import re

def clean_text_for_tts(text: str) -> str:
    # 1) Supprime les # d’en-tête Markdown
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # 2) Retire *, **, ___, etc.
    text = re.sub(r'(\*|_){1,3}', '', text)
    # 3) Supprime les backticks
    text = text.replace('`', '')
    # 4) Transforme [texte](url) en “texte”
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # 5) Enlève les balises HTML éventuelles
    text = re.sub(r'<[^>]+>', '', text)
    return text


# Chargement des variables d'environnement
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialisation du client Groq
client = Groq(api_key=GROQ_API_KEY)

# Fonctions utilitaires
def generate_story(keywords: list[str]) -> str:
    """
    Appelle l'API Groq pour générer une histoire enfantine (~500 mots).
    """
    prompt = (
        "Vous êtes un assistant conteur pour un public enfantin. "
        "Crée une histoire d'environ 500 mots en utilisant les thèmes suivants : "
        + ", ".join(keywords)
    )
    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Vous êtes un assistant pour raconter des histoires pour enfants."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.7,
    )
    return chat_completion.choices[0].message.content

def text_to_speech(text: str) -> BytesIO:
    """
    Génère un flux audio MP3 via gTTS et le renvoie dans un buffer.
    """
    tts = gTTS(text=text, lang="fr")
    buffer = BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---

st.set_page_config(page_title="Générateur d'histoires IA", layout="wide")
st.title("📖 Générateur d’histoires enfantines")

# Session state pour conserver histoire et audio
if "story" not in st.session_state:
    st.session_state.story = None
    st.session_state.audio = None

# 1) Saisie des mots-clés
keywords_input = st.text_input(
    "Entrez des mots-clés (séparés par des virgules) :",
    placeholder="ex. cape, épée, dragon"
)

# 2) Bouton de génération
if st.button("Générer l’histoire"):
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        st.error("Veuillez saisir au moins un mot-clé.")
    else:
        with st.spinner("🔄 Génération de l’histoire en cours..."):
            st.session_state.story = generate_story(keywords)
            st.session_state.audio = None  # reset audio
        st.success("✔️ Histoire générée !")

# 3) Affichage du texte + bouton lecture
if st.session_state.story:
    st.subheader("Votre histoire")
    st.write(st.session_state.story)

    if st.button("🎧 Écouter la narration"):
        with st.spinner("🔊 Synthèse vocale en cours..."):
        # 1) On nettoie le texte avant TTS
            story_clean = clean_text_for_tts(st.session_state.story)
        # 2) Puis on génère l’audio
            st.session_state.audio = text_to_speech(story_clean)
        st.success("✔️ Audio prêt !")

    # 4) Lecture inline et téléchargement
    if st.session_state.audio:
        st.audio(st.session_state.audio, format="audio/mp3")
        st.download_button(
            label="⬇️ Télécharger l’audio",
            data=st.session_state.audio,
            file_name="narration.mp3",
            mime="audio/mp3"
        )
