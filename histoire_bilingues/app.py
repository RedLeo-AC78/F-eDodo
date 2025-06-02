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

# Nettoyage du texte pour le TTS
def clean_text_fortts(text: str) -> str:
    text = re.sub(r'^#{1,6}\s', '', text, flags=re.MULTILINE)
    text = re.sub(r'[*_]+', '', text)
    text = text.replace('`', '')
    text = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text

# Chargement des variables d'environnement
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Traduction via Google Translate API gratuite
def translate_text(text: str, target_lang: str) -> str:
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "fr",
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return ''.join([part[0] for part in response.json()[0]])
    else:
        return "[Translation failed]"

# TTS avec langue personnalisée
def text_to_speech(text: str, lang: str = "fr") -> BytesIO:
    clean = clean_text_fortts(text)
    tts = gTTS(text=clean, lang=lang)
    buffer = BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer

# Génération de l’histoire avec Mistral/Groq
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

# Configuration de la page Streamlit
st.set_page_config(page_title="Générateur d’histoires IA", layout="wide")
st.title("📖 Générateur d’histoires illustrées et bilingues")

# Choix de langue avec drapeaux
LANGUAGES = {
    "🇫🇷 Français": "fr",
    "🇬🇧 English": "en",
    "🇪🇸 Español": "es",
    "🇩🇪 Deutsch": "de",
    "🇸🇦 العربية": "ar"
}

selected_lang_display = st.selectbox("🌍 Choisissez la langue de traduction :", list(LANGUAGES.keys()))
selected_lang_code = LANGUAGES[selected_lang_display]

# Initialisation session state
if "story" not in st.session_state:
    st.session_state.story = None
    st.session_state.story_translated = None
    st.session_state.audio_fr = None
    st.session_state.audio_trad = None
    st.session_state.images = []

# Entrée utilisateur
keywords_input = st.text_input("Mots-clés (ex. singe, Normandie, aventure) :")

# Génération de l’histoire
if st.button("🚀 Générer l’histoire"):
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        st.error("⚠️ Veuillez entrer au moins un mot-clé.")
    else:
        with st.spinner("Génération de l’histoire..."):
            story_fr = generate_story(keywords)
            if selected_lang_code == "fr":
                story_translated = story_fr
            else:
                story_translated = translate_text(story_fr, target_lang=selected_lang_code)
            st.session_state.story = story_fr
            st.session_state.story_translated = story_translated
            st.session_state.audio_fr = None
            st.session_state.audio_trad = None
            st.session_state.images = []
        st.success("✅ Histoire générée !")

# Affichage de l’histoire et audio
if st.session_state.story:
    st.subheader("📝 Histoire en français")
    st.write(st.session_state.story)

    st.subheader(f"🌍 Version en {selected_lang_display}")
    st.write(st.session_state.story_translated)

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
        if st.button(f"🎿 Écouter en {selected_lang_display}"):
            with st.spinner("Création audio..."):
                st.session_state.audio_trad = text_to_speech(st.session_state.story_translated, lang=selected_lang_code)

        if st.session_state.audio_trad:
            st.audio(st.session_state.audio_trad, format="audio/mp3")
            st.download_button(
                label=f"⬇️ Télécharger l’audio en {selected_lang_display}",
                data=st.session_state.audio_trad,
                file_name=f"histoire_{selected_lang_code}.mp3",
                mime="audio/mp3"
            )

    st.subheader("🖼️ Illustrations de l’histoire")
    if not st.session_state.images:
        with st.spinner("Création des illustrations IA via ClipDrop..."):
            parts = split_story_to_chunks(st.session_state.story, n=5)
            for idx, part in enumerate(parts):
                prompt = generate_image_prompt(part)
                try:
                    img = generate_image_from_prompt(prompt)
                    st.session_state.images.append((f"Scène {idx+1}", part, img))
                except Exception as e:
                    st.warning(f"Erreur image : {e}")

    for scene_title, scene_text, img in st.session_state.images:
        st.markdown(f"**{scene_title}** : _{scene_text[:80]}..._")
        st.image(img, caption="Illustration IA générée", use_column_width=True)
