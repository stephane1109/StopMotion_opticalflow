# pip install streamlit opencv-python yt-dlp

import streamlit as st
import cv2
import os
import tempfile
import subprocess

def telecharger_video_yt_dlp(url, dossier_temporaire):
    """
    Télécharge une vidéo YouTube avec yt-dlp.
    """
    commande = [
        "yt-dlp",
        "-f", "mp4",
        "-o", os.path.join(dossier_temporaire, "video_originale.%(ext)s"),
        url
    ]
    subprocess.run(commande, check=True)
    for fichier in os.listdir(dossier_temporaire):
        if fichier.endswith(".mp4"):
            return os.path.join(dossier_temporaire, fichier)
    return None

def appliquer_optical_flow(images):
    """
    Applique la visualisation du flux optique sur les images successives.
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
    images_avec_flow.append(images[-1])  # Dernière image sans flow
    return images_avec_flow

def extraire_images_echantillonnées(chemin_video, dossier_sortie, fps_cible, avec_flow=False):
    """
    Extrait les images à intervalle régulier (effet stop motion), avec option Optical Flow.
    """
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

    if avec_flow and len(images_extraites) > 1:
        images_extraites = appliquer_optical_flow(images_extraites)

    for i, img in enumerate(images_extraites):
        nom = os.path.join(dossier_sortie, f"image_{i:05d}.jpg")
        cv2.imwrite(nom, img)

    return int(fps_original), len(images_extraites)

def créer_vidéo_depuis_images(dossier_images, chemin_sortie, fps=12):
    """
    Construit une vidéo à partir d’images extraites.
    """
    fichiers = sorted([f for f in os.listdir(dossier_images) if f.endswith(".jpg")])
    if not fichiers:
        return None

    image_exemple = cv2.imread(os.path.join(dossier_images, fichiers[0]))
    h, w, _ = image_exemple.shape
    codec = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(chemin_sortie, codec, fps, (w, h))

    for f in fichiers:
        img = cv2.imread(os.path.join(dossier_images, f))
        img = cv2.resize(img, (w, h))
        video.write(img)

    video.release()
    return chemin_sortie

def reencoder_video_h264(chemin_entrée, chemin_sortie):
    """
    Réencode une vidéo en H.264 pour compatibilité Streamlit.
    """
    commande = [
        "ffmpeg",
        "-y",
        "-i", chemin_entrée,
        "-vcodec", "libx264",
        "-preset", "fast",
        "-crf", "23",
        chemin_sortie
    ]
    subprocess.run(commande, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Interface Streamlit
st.title("Générateur de Stop Motion avec Optical Flow (optionnel)")

mode = st.radio("Source de la vidéo :", ["YouTube (yt-dlp)", "Fichier local (.mp4)"])

if mode == "YouTube (yt-dlp)":
    url = st.text_input("Entrez l'URL de la vidéo YouTube")
else:
    fichier = st.file_uploader("Téléverser une vidéo .mp4", type=["mp4"])

fps_cible = st.selectbox("FPS cible (effet Stop Motion)", [4, 6, 8, 10, 12, 14, 16], index=2)
avec_optical_flow = st.checkbox("Ajouter le flux optique (mouvement entre images)")

if st.button("Créer la vidéo Stop Motion"):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Charger la vidéo
            if mode == "YouTube (yt-dlp)":
                if not url:
                    st.error("Veuillez fournir une URL YouTube.")
                    st.stop()
                st.info("Téléchargement de la vidéo...")
                chemin_video = telecharger_video_yt_dlp(url, tmpdir)
                st.success("Téléchargement terminé.")
            else:
                if not fichier:
                    st.error("Veuillez téléverser une vidéo.")
                    st.stop()
                chemin_video = os.path.join(tmpdir, "video_originale.mp4")
                with open(chemin_video, "wb") as f:
                    f.write(fichier.read())
                st.success("Vidéo téléversée.")

            # Extraction images
            dossier_images = os.path.join(tmpdir, "images")
            os.makedirs(dossier_images, exist_ok=True)

            st.info("Extraction des images en cours...")
            fps_origine, nb = extraire_images_echantillonnées(
                chemin_video, dossier_images, fps_cible, avec_flow=avec_optical_flow)
            st.success(f"{nb} images extraites (FPS origine : {fps_origine})")

            # Création de la vidéo temporaire
            chemin_brut = os.path.join(tmpdir, "video_brute.mp4")
            créer_vidéo_depuis_images(dossier_images, chemin_brut, fps=fps_cible)

            # Réencodage final
            chemin_final = os.path.join(tmpdir, "video_finale.mp4")
            st.info("Réencodage final (H.264)...")
            reencoder_video_h264(chemin_brut, chemin_final)

            with open(chemin_final, "rb") as f:
                st.success("Vidéo générée avec succès.")
                st.video(f.read())
                st.download_button("Télécharger la vidéo", data=f, file_name="stopmotion.mp4", mime="video/mp4")

        except subprocess.CalledProcessError:
            st.error("Erreur lors de l'utilisation de yt-dlp ou ffmpeg. Vérifiez leur installation.")
        except Exception as e:
            st.error(f"Erreur : {str(e)}")


