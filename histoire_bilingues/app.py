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
import time
from streamlit_lottie import st_lottie

st.set_page_config(page_title="FeedoDo - Histoire magique", layout="wide")

# --- Intro magique avec bouton ---
# --- Intro avec GIF magique et bouton ---
# --- Splash screen Fée Dodo (5 secondes, automatique) ---
GIF_PATH = "Intro3.gif"

if "splash_shown" not in st.session_state:
    st.session_state.splash_shown = False

if not st.session_state.splash_shown:
    with open(GIF_PATH, "rb") as f:
        gif_base64 = base64.b64encode(f.read()).decode()

    st.markdown(f"""
        <style>
        body {{
            background-color: #FFF8F0 !important;
        }}
        #splash {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: #FFF8F0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            opacity: 1;
            transition: opacity 2s ease;
        }}
        #splash.fade-out {{
            opacity: 0;
            pointer-events: none;
        }}
        #splash h1 {{
            font-family: 'Comic Sans MS', cursive;
            color: #D8652C;
            font-size: 2rem;
            margin-top: 1.5rem;
        }}
        #splash p {{
            font-family: 'Comic Sans MS', cursive;
            color: #444;
            font-size: 1rem;
            margin-top: 0.5rem;
        }}
        </style>

        <div id="splash">
            <img src="data:image/gif;base64,{gif_base64}" width="300"/>
            <h1>✨ Bienvenue dans Fée Dodo ✨</h1>
            <p>Préparation de votre monde magique...</p>
        </div>

        <script>
        setTimeout(function() {{
            document.getElementById('splash').classList.add('fade-out');
        }}, 5000);
        setTimeout(function() {{
            window.location.reload();
        }}, 7000);
        </script>
    """, unsafe_allow_html=True)
   

    # Attente réelle côté serveur (attention en production)
    time.sleep(3.92)
    st.session_state.splash_shown = True
    st.rerun()


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

st.title("📖 Bienvenue dans FeedoDo : l’usine à histoires magiques !")

# Choix de la langue et option de traduction
show_translation = st.checkbox("🧚‍♀️ Traduire dans une autre langue ?")

# Lorsqu’on décoche la traduction, on supprime les anciens états pour forcer régénération
if not show_translation:
    for key in ["story_translated", "audio_translated"]:
        if key in st.session_state:
            del st.session_state[key]
    for key in ["story", "audio_original", "images"]:
        if key in st.session_state:
            del st.session_state[key]

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

        # Calcul du nombre total d’étapes pour la barre
        total_steps = 1  # génération d’histoire
        if show_translation:
            total_steps += 1  # traduction
        total_steps += len(parts)  # nombre de scènes/images
        total_steps += 1  # audio original
        if show_translation:
            total_steps += 1  # audio traduit

        progress.progress(int(step * 100 / total_steps))

        # 3) Génération des images ET audios en parallèle
        images = []
        clipdrop_error = False

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Soumettre toutes les tâches images
            image_futures = {executor.submit(generate_image_from_prompt, generate_image_prompt(part)): part
                             for part in parts}

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

        # Stocker l’histoire dans la session
        st.session_state.story = story
        st.session_state.story_translated = story_translated

        # Finaliser à 100 %
        progress.progress(100)
        st.success("✅ Tout a été généré avec succès !")

# Affichage du résultat une fois que tout est en session_state
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

    # 3) Afficher audio complet traduit + texte traduit
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
