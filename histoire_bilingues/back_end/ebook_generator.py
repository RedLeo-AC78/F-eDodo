# back_end/ebook_generator.py

import PIL
from ebooklib import epub
from io import BytesIO

def build_epub_from_story(story_text: str, images: list[tuple[str, "PIL.Image.Image"]], metadata: dict) -> BytesIO:
    """
    Construit un fichier EPUB à partir du texte complet de l’histoire et de la liste d’images.
    - story_text : le texte intégral (ex. st.session_state.story)
    - images : liste de tuples (partie_de_texte, PIL.Image) dans l’ordre des scènes
    - metadata : dictionnaire contenant au moins 'title' et 'author'
    """
    book = epub.EpubBook()

    # 1) Métadonnées de base
    book.set_identifier("id123456")
    book.set_title(metadata.get("title", "Mon Histoire Magique"))
    book.set_language(metadata.get("language", "fr"))
    book.add_author(metadata.get("author", "Auteur Inconnu"))

    # 2) Chapitre d’introduction (facultatif)
    intro = epub.EpubHtml(
        uid="introduction",        # 'uid' sert à initialiser, mais l’attribut réel est intro.id
        file_name="intro.xhtml",
        title="Introduction"
    )
    intro.content = f"<h1>{metadata.get('title', '')}</h1><p>{metadata.get('description', '')}</p>"
    book.add_item(intro)

    # 3) Préparer la spine et la table des matières
    spine = ['nav', intro]
    toc = [epub.Link(intro.file_name, "Introduction", intro.id)]  # on utilise intro.id ici

    # 4) Pour chaque "scène", créer un chapitre EpubHtml + image
    for idx, (texte_part, img_pil) in enumerate(images, start=1):
        chap_id = f"chap_{idx}"
        chap = epub.EpubHtml(
            uid=chap_id,                 # chap.id prendra la valeur chap_id
            file_name=f"{chap_id}.xhtml",
            title=f"Scène {idx}"
        )

        # 4.a) Convertir l’image PIL en bytes PNG et l’ajouter au livre
        img_buffer = BytesIO()
        img_pil.save(img_buffer, format="PNG")
        img_data = img_buffer.getvalue()
        image_name = f"image_{idx}.png"
        epub_image = epub.EpubItem(
            uid=f"img_{idx}",
            file_name=f"images/{image_name}",
            media_type="image/png",
            content=img_data
        )
        book.add_item(epub_image)

        # 4.b) Générer le HTML du chapitre, incluant l’image + le texte
        chap.content = f"""
            <h2>Scène {idx}</h2>
            <div style="text-align:center; margin-bottom:1em;">
              <img src="images/{image_name}" alt="Illustration Scène {idx}" style="max-width:100%;height:auto;"/>
            </div>
            <div style="font-size:1.1em; line-height:1.5;">
              {texte_part.replace('\n', '<br/>')}
            </div>
        """
        book.add_item(chap)

        # 4.c) Insérer le chapitre dans la spine et la TOC
        spine.append(chap)
        toc.append(epub.Link(chap.file_name, f"Scène {idx}", chap.id))  # chap.id ici

    # 5) Facultatif : ajouter une feuille de style CSS basique
    style = '''
    body { font-family: serif; margin: 1em; }
    h1, h2, h3 { color: #5D3FD3; text-align: center; }
    img { display: block; margin-left: auto; margin-right: auto; }
    '''
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="styles/nav.css",
        media_type="text/css",
        content=style.encode('utf-8')
    )
    book.add_item(nav_css)

    # 6) Finaliser le livre : spine, toc, et ajouter NCX/Nav
    book.toc = tuple(toc)
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 7) Écrire l’EPUB dans un buffer mémoire et le retourner
    epub_buffer = BytesIO()
    epub.write_epub(epub_buffer, book, {})
    epub_buffer.seek(0)
    return epub_buffer
