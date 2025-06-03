# app.py

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

import concurrent.futures

from back_end.ebook_generator import build_epub_from_story

# ────────────────────────────────────────────────────────────────────
# 0. CONFIGURATION DE LA PAGE : DOIT ÊTRE LA PREMIÈRE COMMANDE STREAMLIT
# ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="FeedoDo - Histoire magique", layout="wide")

# ────────────────────────────────────────────────────────────────────
# 1. LECTURE ET CONVERSION DE L'IMAGE DE FOND EN BASE64
# ────────────────────────────────────────────────────────────────────
BACKGROUND_IMAGE_PATH = "background.png"
background_base64 = ""
if os.path.exists(BACKGROUND_IMAGE_PATH):
    with open(BACKGROUND_IMAGE_PATH, "rb") as img_file:
        background_bytes = img_file.read()
        background_base64 = base64.b64encode(background_bytes).decode()

# ────────────────────────────────────────────────────────────────────
# 2. INJECTION DU CSS AVEC LE BACKGROUND
# ────────────────────────────────────────────────────────────────────
st.markdown(f"""
    <style>
    /* ---------- STYLE GÉNÉRAL DU BACKGROUND ---------- */
    body {{
        background-color: #FFF8F0;  /* beige très clair si pas d'image */
        background-image: url("data:image/png;base64,{background_base64}") !important;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}

    /* ---------- CONTENEUR PRINCIPAL ---------- */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        max-width: 900px;
        margin: auto;
    }}

    /* ---------- TITRES : police Comic Sans MS, couleur violette ---------- */
    h1, h2, h3 {{
        font-family: 'Comic Sans MS', cursive, sans-serif;
        color: #5D3FD3;
        text-align: center;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }}

    /* ---------- PARCHEMIN (CONTE) ---------- */
    .parchment-container {{
        display: flex;
        justify-content: center;
        width: 100%;
        margin-bottom: 2rem;
    }}
    .parchment {{
        background-color: #FDF0D5;          /* beige doux */
        color: #2B2B2B;                     /* texte anthracite */
        border: 8px solid #D2A679;         /* bord brun clair */
        border-radius: 20px;
        padding: 20px 30px;
        max-width: 800px;
        box-shadow: 0 6px 14px rgba(0,0,0,0.1);
        font-size: 18px;
        line-height: 1.6;
    }}
    .parchment img {{
        max-width: 100%;
        height: auto;
        display: block;
        margin: 1rem auto;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }}
    .parchment h3 {{
        margin-bottom: 0.8rem;
        color: #5D3FD3;
        font-family: 'Comic Sans MS', cursive, sans-serif;
    }}
    .parchment p {{
        text-align: center;
        margin-top: 1rem;
    }}

    /* ---------- BOUTONS (stButton) ---------- */
    .stButton > button {{
        font-family: 'Comic Sans MS', cursive, sans-serif;
        background: linear-gradient(135deg, #FFD966 0%, #FFB6C1 100%); /* dégradé jaune → rose */
        color: #FFFFFF;
        font-size: 20px;
        padding: 0.8em 1.8em;
        border-radius: 20px;
        border: 2px solid #FF8C00;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        transition: transform 0.2s, box-shadow 0.2s;
        display: block;
        margin: 1rem auto;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0,0,0,0.2);
        background: linear-gradient(135deg, #FFB347 0%, #FF69B4 100%);
    }}

    /* ---------- CHAMP DE SAISIE (stTextInput) ---------- */
    .stTextInput > div > input {{
        font-size: 20px;
        background-color: #FFFFFF;    /* fond blanc pour mieux voir le texte */
        border: 1px solid #FFD966;    /* bordure pastel légère */
        border-radius: 8px;
        padding: 0.6em 1em;
        color: #333333;
    }}
    .stTextInput > label {{
        font-family: 'Comic Sans MS', cursive, sans-serif;
        font-size: 18px;
        color: #5D3FD3;
    }}

    /* ---------- SELECTBOX (menu déroulant) ---------- */
    .stSelectbox > div > div > div {{
        font-size: 18px;
        background-color: #FFFFFF;    /* fond blanc */
        border: 1px solid #FFD966;    /* bordure pastel légère */
        border-radius: 8px;
        padding: 0.5em 0.8em;
        color: #333333;
        height: 2.5em;                /* hauteur fixe pour centrer verticalement */
        display: flex;
        align-items: center;          /* aligne le texte verticalement */
    }}
    .stSelectbox > label {{
        font-family: 'Comic Sans MS', cursive, sans-serif;
        font-size: 18px;
        color: #5D3FD3;
        margin-bottom: 0.3em;
    }}
    .stSelectbox > div > div > div svg {{
        fill: #5D3FD3 !important;     /* couleur du petit chevron */
    }}

    /* ---------- CHECKBOX ---------- */
    .stCheckbox > label {{
        font-family: 'Comic Sans MS', cursive, sans-serif;
        font-size: 18px;
        color: #5D3FD3;
        margin-top: 0.4em;            /* décale un peu vers le bas pour aligner avec select */
    }}

    /* ---------- BOUTON DE TÉLÉCHARGEMENT AUDIO ---------- */
    .stDownloadButton > button {{
        font-family: 'Comic Sans MS', cursive, sans-serif;
        background: linear-gradient(135deg, #87CEFA 0%, #98FB98 100%); /* bleu ciel → vert */
        color: #FFFFFF;
        font-size: 18px;
        padding: 0.6em 1.2em;
        border-radius: 16px;
        border: 2px solid #00BFFF;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
        margin-top: 0.5em;
    }}
    .stDownloadButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        background: linear-gradient(135deg, #1E90FF 0%, #00FA9A 100%);
    }}

    /* ---------- LECTEUR AUDIO ---------- */
    .stAudio {{
        margin-top: 0.5em;
        margin-bottom: 1.5em;
        border: 2px solid #FFD966;
        border-radius: 12px;
        background-color: #FFF8DC;
    }}

    /* ---------- IMAGES GÉNÉRÉES ---------- */
    img {{
        border-radius: 16px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }}

    /* ---------- RÉPONSIVE ---------- */
    @media (max-width: 768px) {{
        .block-container {{
            padding: 1rem;
        }}
        .parchment {{
            padding: 15px 20px;
            font-size: 16px;
        }}
        .stButton > button,
        .stDownloadButton > button {{
            font-size: 18px;
            padding: 0.7em 1.4em;
        }}
        .stTextInput > div > input {{
            font-size: 18px;
        }}
        .stSelectbox > div > div > div {{
            font-size: 16px;
            height: 2.2em;
            padding: 0.4em 0.6em;
        }}
    }}
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────
# 3. CHARGEMENT DES VARIABLES D’ENVIRONNEMENT ET INITIALISATION CLIENT
# ────────────────────────────────────────────────────────────────────
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

LANGUAGES = {
    "🇫🇷 Français": "fr",
    "🇬🇧 English": "en",
    "🇪🇸 Español": "es"
}

# Texte des boutons de téléchargement audio
download_labels = {
    "fr": "⬇️ Télécharger l'audio",
    "en": "⬇️ Download audio",
    "es": "⬇️ Descargar audio"
}

# ────────────────────────────────────────────────────────────────────
# 4. FONCTION DE TRADUCTION VIA API GOOGLE
# ────────────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────────────
# 5. FONCTION DE GÉNÉRATION D’HISTOIRE VIA MISTRAL
# ────────────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────────────
# 6. AFFICHAGE DE L’INTERFACE STREAMLIT
# ────────────────────────────────────────────────────────────────────
st.title("📖 Bienvenue dans FeedoDo : l’usine à histoires magiques !")

# Choix de la langue et option de traduction
show_translation = st.checkbox("🧚‍♀️ Traduire dans une autre langue ?")

if show_translation:
    col1, col2 = st.columns(2)
    with col1:
        lang_input_label = st.selectbox("🗣️ Langue de l’histoire :", list(LANGUAGES.keys()))
        lang_input_code = LANGUAGES[lang_input_label]
    with col2:
        lang_output_label = st.selectbox(
            "🌍 Langue de traduction :",
            [lbl for lbl in LANGUAGES if LANGUAGES[lbl] != lang_input_code]
        )
        lang_output_code = LANGUAGES[lang_output_label]
else:
    lang_input_label = st.selectbox("🗣️ Langue de l’histoire :", list(LANGUAGES.keys()))
    lang_input_code = LANGUAGES[lang_input_label]
    lang_output_label = None
    lang_output_code = None

# Saisie des mots-clés
keywords_input = st.text_input(f"📝 Mots-clés ({lang_input_label}) :")

# Bouton pour générer l’histoire et barre de chargement asynchrone
if st.button("🚀 Générer l’histoire magique"):
    # ───────────────────────────────────────────────────────────────
    # ==> On supprime d’abord tout ce qui pourrait rester d’une ancienne histoire
    # ───────────────────────────────────────────────────────────────
    for key in ["story", "story_translated", "audio_original", "audio_translated", "images"]:
        if key in st.session_state:
            del st.session_state[key]

    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        st.error("⚠️ Veuillez entrer au moins un mot-clé.")
    else:
        # Barre de progression
        progress = st.progress(0)
        step = 0

        # 1) Génération de l’histoire
        with st.spinner("🧠 Génération de l’histoire..."):
            story = generate_story(keywords, lang_input_code)
        step += 1

        # 2) Traduction complète si demandée
        if show_translation:
            with st.spinner("🌍 Traduction de l’histoire..."):
                story_translated = translate_text(story, lang_input_code, lang_output_code)
            step += 1
        else:
            story_translated = None

        # Découper l’histoire en scènes
        parts = split_story_to_chunks(story, n=2)

        # Calcul du nombre total d’étapes pour la barre de progression
        total_steps = 1  # génération d’histoire
        if show_translation:
            total_steps += 1  # traduction
        total_steps += len(parts)  # nombre de scènes/images
        total_steps += 1  # audio original
        if show_translation:
            total_steps += 1  # audio traduit

        progress.progress(int(step * 100 / total_steps))

        # 3) Génération des images ET des audios en parallèle
        images = []
        clipdrop_error = False

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Soumettre toutes les tâches de génération d’images
            image_futures = {
                executor.submit(generate_image_from_prompt, generate_image_prompt(part)): part
                for part in parts
            }

            # Soumettre génération audio original
            audio_original_future = executor.submit(generate_tts_audio, story, lang_input_code)

            # Soumettre audio traduit si nécessaire
            if show_translation and story_translated:
                audio_translated_future = executor.submit(generate_tts_audio, story_translated, lang_output_code)
            else:
                audio_translated_future = None

            # Traiter résultats d’images dès qu’elles tombent
            for future in concurrent.futures.as_completed(image_futures):
                part = image_futures[future]
                try:
                    image = future.result()
                    images.append((part, image))
                except RuntimeError as e:
                    if "402" in str(e):
                        st.error("❌ Crédits ClipDrop épuisés, impossible de générer d’autres images.")
                    else:
                        st.warning(f"⚠️ {e}")
                    clipdrop_error = True
                    break
                step += 1
                progress.progress(int(step * 100 / total_steps))

            st.session_state.images = images

            # 4) Récupérer l’audio original
            if audio_original_future:
                audio_original = audio_original_future.result()
                st.session_state.audio_original = audio_original
                step += 1
                progress.progress(int(step * 100 / total_steps))

            # 5) Récupérer l’audio traduit
            if audio_translated_future:
                audio_translated = audio_translated_future.result()
                st.session_state.audio_translated = audio_translated
                step += 1
                progress.progress(int(step * 100 / total_steps))

        # Stocker l’histoire et la version traduite dans la session
        st.session_state.story = story
        st.session_state.story_translated = story_translated

        # Finaliser à 100 %
        progress.progress(100)
        st.success("✅ Tout a été généré avec succès !")

# ────────────────────────────────────────────────────────────────────
# 7. AFFICHAGE DU RÉSULTAT UNE FOIS GÉNÉRÉ
# ────────────────────────────────────────────────────────────────────
if "story" in st.session_state and st.session_state.story:
    # 1) Afficher les scènes illustrées
    st.header("🎨 Illustrations magiques de l’histoire")
    if st.session_state.images:
        for idx, (part, image) in enumerate(st.session_state.images):
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            st.markdown(f"""
                <div class="parchment-container">
                    <div class="parchment">
                        <h3>Scène {idx+1}</h3>
                        <img src="data:image/png;base64,{img_str}" />
                        <p>{part}</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucune illustration disponible (crédits ClipDrop épuisés ou erreur).")

    # 2) Afficher audio complet d’origine
    st.header("🔊 Audio complet (Langue originale)")
    if st.session_state.audio_original:
        st.audio(st.session_state.audio_original, format="audio/mp3")
        st.download_button(
            label=download_labels.get(lang_input_code, "⬇️ Télécharger l'audio"),
            data=st.session_state.audio_original,
            file_name=f"histoire_complet_{lang_input_code}.mp3",
            mime="audio/mp3",
            use_container_width=True
        )

    # 3) Afficher audio complet traduit + texte traduit (si demandé)
    if show_translation and "story_translated" in st.session_state and st.session_state.story_translated:
        st.header("🔊 Audio complet (Version traduite)")
        if st.session_state.audio_translated:
            st.audio(st.session_state.audio_translated, format="audio/mp3")
            st.download_button(
                label=download_labels.get(lang_output_code, "⬇️ Télécharger l'audio traduit"),
                data=st.session_state.audio_translated,
                file_name=f"histoire_complet_{lang_output_code}.mp3",
                mime="audio/mp3",
                use_container_width=True
            )
        st.markdown(f"""
            <div class="parchment-container">
                <div class="parchment">
                    <h3>Histoire complète traduite ({lang_output_label})</h3>
                    <p>{st.session_state.story_translated.replace('\n', '<br>')}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────
# 8. BOUTON “TÉLÉCHARGER L’HISTOIRE” EN EPUB UNIQUEMENT
# ────────────────────────────────────────────────────────────────────
if "story" in st.session_state and st.session_state.story:
    st.header("📚 Télécharger l’histoire complète (EPUB uniquement)")

    if st.button("⬇️ Télécharger en EPUB"):
        # Préparer les métadonnées de l’ePub
        metadata = {
            "title": "Histoire Magique Générée",
            "language": lang_input_code,
            "author": "FeedoDo",
            "description": f"Histoire générée via FeedoDo le {__import__('datetime').datetime.now().date()}"
        }

        # Générer l’EPUB en mémoire
        images = st.session_state.images
        epub_buffer = build_epub_from_story(st.session_state.story, images, metadata)

        # Proposer le téléchargement direct du .epub
        st.download_button(
            label="Télécharger l’ePub",
            data=epub_buffer.getvalue(),
            file_name="histoire_magique.epub",
            mime="application/epub+zip",
            use_container_width=True
        )
