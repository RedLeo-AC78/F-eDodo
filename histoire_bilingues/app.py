import os
from io import BytesIO
import base64
import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from back_end.tts_generator import generate_tts_audio
from back_end.image_generator import (
    generate_image_from_prompt,
    split_story_to_chunks,
    generate_image_prompt
)

# -------------------------------------------------------------------
# 1. LECTURE ET CONVERSION DE L'IMAGE DE FOND EN BASE64
# -------------------------------------------------------------------
# Indique ici le chemin vers ton image de fond (par ex. "background.png" dans le même dossier)
BACKGROUND_IMAGE_PATH = "background.png"
background_base64 = ""
if os.path.exists(BACKGROUND_IMAGE_PATH):
    with open(BACKGROUND_IMAGE_PATH, "rb") as img_file:
        background_bytes = img_file.read()
        background_base64 = base64.b64encode(background_bytes).decode()

# -------------------------------------------------------------------
# 2. CONFIGURATION DE LA PAGE ET INJECTION DU CSS AVEC LE BACKGROUND
# -------------------------------------------------------------------
st.set_page_config(page_title="FeedoDo - Histoire magique", layout="wide")

# Construction du CSS : si background_base64 n'est pas vide, on utilise l'image,
# sinon on tombe sur une couleur unie (#FFF8F0).
css_background = ""
if background_base64:
    css_background = f"""
        body {{
            background-image: url("data:image/png;base64,{background_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
    """
else:
    # Si l'image n'existe pas ou n'a pas pu être lue
    css_background = """
        body {
            background-color: #FFF8F0;
        }
    """

st.markdown(f"""
    <style>
    {css_background}

    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        display: flex;
        justify-content: center;
    }}
    h1, h2, h3 {{
        color: #5D3FD3;
        font-family: 'Comic Sans MS', cursive, sans-serif;
        text-align: center;
    }}
    .stButton > button {{
        background-color: #FFB347;
        color: white;
        font-size: 20px;
        padding: 0.6em 1.5em;
        border-radius: 12px;
        border: none;
        transition: background-color 0.3s;
        display: block;
        margin: 0 auto;
    }}
    .stButton > button:hover {{
        background-color: #FF9900;
    }}
    .stTextInput > div > input {{
        font-size: 20px;
        background-color: #FFF2CC;
        border-radius: 8px;
    }}
    .stSelectbox > div > div > div {{
        font-size: 18px;
    }}
    .stCheckbox > label {{
        font-size: 18px;
    }}
    .stAudio {{
        margin-top: 0.5em;
        margin-bottom: 1.5em;
    }}
    .stDownloadButton > button {{
        background-color: #FF69B4;
        color: white;
        font-size: 18px;
        padding: 0.5em 1em;
        border-radius: 10px;
    }}
    img {{
        border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    .parchment-container {{
        display: flex;
        justify-content: center;
        width: 100%;
        margin-bottom: 2rem;
    }}
    .parchment {{
        background-color: #f5f5dc;
        color: #000000;
        border: 10px solid #d2b48c;
        border-radius: 20px;
        padding: 20px;
        max-width: 800px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        font-size: 18px;
        line-height: 1.6;
    }}
    .parchment img {{
        max-width: 100%;
        height: auto;
        display: block;
        margin: 1rem auto;
    }}
    .parchment p {{
        text-align: center;
        margin-top: 1rem;
    }}
    .parchment h3 {{
        margin-bottom: 1rem;
    }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 3. CHARGEMENT DES VARIABLES D’ENVIRONNEMENT ET INITIALISATION CLIENT
# -------------------------------------------------------------------
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

LANGUAGES = {
    "🇫🇷 Français": "fr",
    "🇬🇧 English": "en",
    "🇪🇸 Español": "es"
}

# Texte des boutons téléchargement
download_labels = {
    "fr": "⬇️ Télécharger l'audio",
    "en": "⬇️ Download audio",
    "es": "⬇️ Descargar audio"
}

# -------------------------------------------------------------------
# 4. FONCTION DE TRADUCTION VIA API GOOGLE
# -------------------------------------------------------------------
def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": source_lang,
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return ''.join([part[0] for part in response.json()[0]])
    return "[Échec de la traduction]"

# -------------------------------------------------------------------
# 5. FONCTION DE GÉNÉRATION D’HISTOIRE VIA MISTRAL
# -------------------------------------------------------------------
def generate_story(keywords: list[str], lang_code: str) -> str:
    prompts = {
        "fr": "Tu es un assistant conteur pour enfants âgés de 1 à 6 ans. Rédige une histoire courte et adaptée avec ces mots-clés : ",
        "en": "You are a storytelling assistant for children aged 1 to 6. Write a short story using the following keywords: ",
        "es": "Eres un asistente que cuenta cuentos pour niños de 1 a 6 años. Escribe una historia corta con estas palabras clave: "
    }
    prompt = prompts[lang_code] + ", ".join(keywords)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.7
    )
    return response.choices[0].message.content

# -------------------------------------------------------------------
# 6. AFFICHAGE DE L’INTERFACE STREAMLIT
# -------------------------------------------------------------------

# Titre principal centré
st.title("📖 Bienvenue dans FeedoDo : l’usine à histoires magiques !")

# Choix de la langue
col1, col2 = st.columns(2)
with col1:
    lang_input_label = st.selectbox("🗣️ Langue de l’histoire :", list(LANGUAGES.keys()))
    lang_input_code = LANGUAGES[lang_input_label]

with col2:
    show_translation = st.checkbox("🧚‍♀️ Traduire dans une autre langue ?")
    if show_translation:
        lang_output_label = st.selectbox(
            "🌍 Langue de traduction :",
            [label for label in LANGUAGES if LANGUAGES[label] != lang_input_code]
        )
        lang_output_code = LANGUAGES[lang_output_label]
    else:
        lang_output_label = None
        lang_output_code = None

# Initialisation de la session
if "story" not in st.session_state:
    st.session_state.story = None
    st.session_state.story_translated = None
    st.session_state.audio_input = None
    st.session_state.audio_output = None
    st.session_state.images = []

# Saisie des mots-clés
keywords_input = st.text_input(f"📝 Mots-clés ({lang_input_label}) :")

# Bouton pour générer l’histoire
if st.button("🚀 Générer l’histoire magique"):
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        st.error("⚠️ Veuillez entrer au moins un mot-clé.")
    else:
        with st.spinner("🧠 Création de l’histoire magique en cours..."):
            story = generate_story(keywords, lang_input_code)
            story_trad = translate_text(story, lang_input_code, lang_output_code) if show_translation else None
            st.session_state.story = story
            st.session_state.story_translated = story_trad
            st.session_state.audio_input = None
            st.session_state.audio_output = None
            st.session_state.images = []
        st.success("✅ Histoire générée avec succès !")

# Affichage du résultat
if st.session_state.story:
    # Histoire originale
    st.header(f"📘 Histoire originale ({lang_input_label})")
    story_html = st.session_state.story.replace("\n", "<br>")
    st.markdown(f"""
        <div class="parchment-container">
            <div class="parchment">
                {story_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Version traduite si demandée
    if show_translation and st.session_state.story_translated:
        st.header(f"📗 Version traduite ({lang_output_label})")
        story_trad_html = st.session_state.story_translated.replace("\n", "<br>")
        st.markdown(f"""
            <div class="parchment-container">
                <div class="parchment">
                    {story_trad_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Boutons pour écouter et télécharger l’audio
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 🔊 Écoute en {lang_input_label}")
        if st.button(f"▶️ Lancer l’audio ({lang_input_label})"):
            with st.spinner("🎧 Génération audio..."):
                st.session_state.audio_input = generate_tts_audio(
                    st.session_state.story,
                    lang=lang_input_code
                )
        if st.session_state.audio_input:
            st.audio(st.session_state.audio_input, format="audio/mp3")
            st.download_button(
                label=download_labels.get(lang_input_code, "⬇️ Download"),
                data=st.session_state.audio_input,
                file_name=f"histoire_{lang_input_code}.mp3",
                mime="audio/mp3",
                use_container_width=True
            )
    with col2:
        if show_translation and st.session_state.story_translated:
            st.markdown(f"### 🔊 Écoute en {lang_output_label}")
            if st.button(f"▶️ Lancer l’audio ({lang_output_label})"):
                with st.spinner("🎧 Génération audio..."):
                    st.session_state.audio_output = generate_tts_audio(
                        st.session_state.story_translated,
                        lang=lang_output_code
                    )
            if st.session_state.audio_output:
                st.audio(st.session_state.audio_output, format="audio/mp3")
                st.download_button(
                    label=download_labels.get(lang_output_code, "⬇️ Download"),
                    data=st.session_state.audio_output,
                    file_name=f"histoire_{lang_output_code}.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )

    # Illustration et texte dans le parchemin
    st.header("🎨 Illustrations magiques de l’histoire")
    if not st.session_state.images:
        with st.spinner("🖼️ Création des images..."):
            parts = split_story_to_chunks(st.session_state.story, n=2)
            for idx, part in enumerate(parts):
                try:
                    prompt = generate_image_prompt(part)
                    image = generate_image_from_prompt(prompt)
                    st.session_state.images.append((f"Scène {idx+1}", part, image))
                except RuntimeError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.warning(f"Erreur inattendue lors de la génération d'image : {e}")

    for scene_title, scene_text, img in st.session_state.images:
        buffered = BytesIO()
        img.save(buffered, format='PNG')
        img_str = base64.b64encode(buffered.getvalue()).decode()
        html = f"""
            <div class="parchment-container">
                <div class="parchment">
                    <h3>{scene_title}</h3>
                    <img src="data:image/png;base64,{img_str}" />
                    <p>{scene_text}</p>
                </div>
            </div>
        """
        st.markdown(html, unsafe_allow_html=True)
