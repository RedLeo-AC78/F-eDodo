import os
from io import BytesIO
import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
from back_end.image_generator import (
    generate_image_from_prompt,
    split_story_to_chunks,
    generate_image_prompt
)
import re

def clean_text_fortts(text: str) -> str:
    text = re.sub(r'^#{1,6}\s', '', text, flags=re.MULTILINE)  # Supprime titres Markdown
    text = re.sub(r'[*_]+', '', text)                          # Supprime *, **, etc.
    text = text.replace('`', '')                               # Supprime les backticks
    text = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', text)        # [texte](lien) => texte
    text = re.sub(r'<[^>]+>', '', text)                        # Supprime HTML
    return text

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def translate_fr_to_en(text: str) -> str:
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "fr",
        "tl": "en",
        "dt": "t",
        "q": text
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return ''.join([part[0] for part in response.json()[0]])
    else:
        return "[Translation failed]"

def text_to_speech(text: str, lang: str = "fr") -> BytesIO:
    clean = clean_text_fortts(text)
    tts = gTTS(text=clean, lang=lang)
    buffer = BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer

def generate_story(keywords: list[str]) -> str:
    prompt = (
        "Tu es un assistant conteur pour enfants. Rédige une histoire de 500 mots avec les mots-clés suivants : "
        + ", ".join(keywords)
    )
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "Tu écris des histoires captivantes pour enfants."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )
    return response.choices[0].message.content

st.set_page_config(page_title="Générateur d’histoires IA", layout="wide")
st.title("📖 Générateur d’histoires illustrées et bilingues")

if "story" not in st.session_state:
    st.session_state.story = None
    st.session_state.story_en = None
    st.session_state.audio_fr = None
    st.session_state.audio_en = None
    st.session_state.images = []

keywords_input = st.text_input("Mots-clés (ex. singe, Normandie, aventure) :")

# Choix du moteur d’image
image_provider = st.selectbox("🎨 Choisissez le moteur d’illustration IA :", ["huggingface", "clipdrop"])

if st.button("🚀 Générer l’histoire"):
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        st.error("⚠️ Veuillez entrer au moins un mot-clé.")
    else:
        with st.spinner("Génération de l’histoire..."):
            story_fr = generate_story(keywords)
            story_en = translate_fr_to_en(story_fr)
            st.session_state.story = story_fr
            st.session_state.story_en = story_en
            st.session_state.audio_fr = None
            st.session_state.audio_en = None
            st.session_state.images = []
        st.success("✅ Histoire générée !")

if st.session_state.story:
    st.subheader("📝 Histoire en français")
    st.write(st.session_state.story)

    st.subheader("🌍 Version anglaise")
    st.write(st.session_state.story_en)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎿 Écouter en français"):
            with st.spinner("Création audio FR..."):
                st.session_state.audio_fr = text_to_speech(st.session_state.story, lang="fr")

        if st.session_state.audio_fr:
            st.audio(st.session_state.audio_fr, format="audio/mp3")
            st.download_button(
                label="⬇️ Télécharger l’audio en français",
                data=st.session_state.audio_fr,
                file_name="histoire_fr.mp3",
                mime="audio/mp3"
            )

    with col2:
        if st.button("🎿 Listen in English"):
            with st.spinner("Creating English audio..."):
                st.session_state.audio_en = text_to_speech(st.session_state.story_en, lang="en")

        if st.session_state.audio_en:
            st.audio(st.session_state.audio_en, format="audio/mp3")
            st.download_button(
                label="⬇️ Download English audio",
                data=st.session_state.audio_en,
                file_name="story_en.mp3",
                mime="audio/mp3"
            )

    st.subheader("🖼️ Illustrations de l’histoire")
    if not st.session_state.images:
        with st.spinner(f"Création des illustrations IA via {image_provider}..."):
            parts = split_story_to_chunks(st.session_state.story, n=5)
            for idx, part in enumerate(parts):
                prompt = generate_image_prompt(part)
                try:
                    img = generate_image_from_prompt(prompt, provider=image_provider)
                    st.session_state.images.append((f"Scène {idx+1}", part, img))
                except Exception as e:
                    st.warning(f"Erreur image : {e}")

    for scene_title, scene_text, img in st.session_state.images:
        st.markdown(f"**{scene_title}** : _{scene_text[:80]}..._")
        st.image(img, caption="Illustration IA générée", use_column_width=True)
