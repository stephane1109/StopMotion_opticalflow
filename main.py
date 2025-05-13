# pip install streamlit opencv-python yt-dlp

import streamlit as st
import cv2
import os
import tempfile
import subprocess

def telecharger_video_yt_dlp(url, chemin_sortie):
    commande = [
        "yt-dlp",
        "-f", "mp4",
        "-o", os.path.join(chemin_sortie, "video_originale.%(ext)s"),
        url
    ]
    subprocess.run(commande, check=True)
    for fichier in os.listdir(chemin_sortie):
        if fichier.endswith(".mp4"):
            return os.path.join(chemin_sortie, fichier)
    return None

def appliquer_optical_flow(images):
    """
    Applique la visualisation du flux optique sur une liste d’images successives.
    """
    images_avec_flow = []
    for i in range(len(images) - 1):
        img1 = cv2.cvtColor(images[i], cv2.COLOR_BGR2GRAY)
        img2 = cv2.cvtColor(images[i + 1], cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(img1, img2, None,
                                            0.5, 3, 15, 3, 5, 1.2, 0)
        vis = images[i].copy()
        h, w = img1.shape
        step = 16
        for y in range(0, h, step):
            for x in range(0, w, step):
                fx, fy = flow[y, x]
                cv2.arrowedLine(vis, (x, y), (int(x + fx), int(y + fy)),
                                (0, 255, 0), 1, tipLength=0.4)
        images_avec_flow.append(vis)
    # Ajouter dernière image sans flow
    images_avec_flow.append(images[-1])
    return images_avec_flow

def extraire_images_echantillonnées(chemin_video, dossier_sortie, fps_cible, avec_flow=False):
    cap = cv2.VideoCapture(chemin_video)
    fps_original = cap.get(cv2.CAP_PROP_FPS)
    ratio_saut = max(1, int(round(fps_original / fps_cible)))

    images_extraites = []
    compteur = 0
    index = 0

    while cap.isOpened():
        succès, image = cap.read()
        if not succès:
            break
        if index % ratio_saut == 0:
            images_extraites.append(image)
            compteur += 1
        index += 1
    cap.release()

    # Si l’utilisateur a activé le flux optique
    if avec_flow and len(images_extraites) > 1:
        images_extraites = appliquer_optical_flow(images_extraites)

    # Sauvegarde des images dans le dossier
    for i, img in enumerate(images_extraites):
        nom = os.path.join(dossier_sortie, f"image_{i:05d}.jpg")
        cv2.imwrite(nom, img)

    return int(fps_original), len(images_extraites)

def créer_vidéo_depuis_images(dossier_images, nom_fichier_sortie, fps=12, extension=".jpg"):
    fichiers_images = sorted([
        f for f in os.listdir(dossier_images)
        if f.endswith(extension)
    ])

    if not fichiers_images:
        st.error("Aucune image trouvée.")
        return None

    image_exemple = cv2.imread(os.path.join(dossier_images, fichiers_images[0]))
    hauteur, largeur, _ = image_exemple.shape

    codec = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(nom_fichier_sortie, codec, fps, (largeur, hauteur))

    for nom_fichier in fichiers_images:
        image = cv2.imread(os.path.join(dossier_images, nom_fichier))
        if image is None:
            continue
        image_redim = cv2.resize(image, (largeur, hauteur))
        video.write(image_redim)

    video.release()
    return nom_fichier_sortie

# Interface Streamlit
st.title("🎬 Création d'une vidéo Stop Motion avec option Optical Flow")

mode = st.radio("Source de la vidéo :", ["YouTube (yt-dlp)", "Fichier local (.mp4)"])

if mode == "YouTube (yt-dlp)":
    url_youtube = st.text_input("Entrez l'URL de la vidéo YouTube")
else:
    fichier_upload = st.file_uploader("Téléversez un fichier vidéo .mp4", type=["mp4"])

fps_cible = st.selectbox("Choisissez la fréquence Stop Motion", [4, 6, 8, 10, 12, 14, 16], index=2)

avec_optical_flow = st.checkbox("🔍 Activer la visualisation des mouvements (Optical Flow)", value=False)

if st.button("Créer la vidéo Stop Motion"):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            if mode == "YouTube (yt-dlp)":
                if not url_youtube:
                    st.error("Veuillez entrer une URL.")
                    st.stop()
                st.info("Téléchargement de la vidéo...")
                chemin_video = telecharger_video_yt_dlp(url_youtube, tmpdir)
                st.success("Vidéo téléchargée.")
            else:
                if not fichier_upload:
                    st.error("Veuillez téléverser une vidéo.")
                    st.stop()
                chemin_video = os.path.join(tmpdir, "video_originale.mp4")
                with open(chemin_video, "wb") as f:
                    f.write(fichier_upload.read())
                st.success("Vidéo téléversée.")

            st.info("Extraction et traitement des images...")
            dossier_images = os.path.join(tmpdir, "images")
            os.makedirs(dossier_images, exist_ok=True)

            fps_origine, nb_images = extraire_images_echantillonnées(
                chemin_video, dossier_images, fps_cible, avec_flow=avec_optical_flow)

            st.info(f"FPS d'origine : {fps_origine} | Images conservées : {nb_images}")

            st.info("Création de la vidéo finale...")
            chemin_sortie = os.path.join(tmpdir, "stopmotion.mp4")
            resultat = créer_vidéo_depuis_images(dossier_images, chemin_sortie, fps=fps_cible)

            if resultat:
                with open(resultat, "rb") as fichier_vidéo:
                    st.success("✅ Vidéo créée avec succès.")
                    st.video(fichier_vidéo.read())
                    st.download_button("📥 Télécharger la vidéo", data=fichier_vidéo, file_name="stopmotion.mp4")

        except subprocess.CalledProcessError:
            st.error("Erreur avec yt-dlp : assurez-vous qu’il est installé et dans le PATH.")
        except Exception as e:
            st.error(f"Erreur : {str(e)}")

