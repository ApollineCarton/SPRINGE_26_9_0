# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre 0 — ACCUEIL
═══════════════════════════════════════════════════════════════════════════
Première chose que voit l'utilisateur. Présente l'outil, annonce ce qui
va être demandé, et signale la nécessité d'une connexion internet.

Ce module suit la convention des autres fenêtres du projet
(fenetre_donnees_indicateurs.py, fenetre_comprendre_donnees.py) :
une fenêtre = un fichier, chargé automatiquement par la boucle
importlib du script principal depuis 00_fonctions/.

Appel depuis le script principal :
    fenetre_accueil.fenetre_accueil()
═══════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# CHARGEMENT DES LOGOS
# ═══════════════════════════════════════════════════════════════════════════
# Deux pièges classiques de Tkinter sont traités ici :
#
#   1. FORMATS D'IMAGE
#      tk.PhotoImage ne lit nativement que PNG (Tk ≥ 8.6) et GIF.
#      Il ne sait PAS lire le JPEG — or logo_ofb.jpg en est un.
#      On passe donc par Pillow (PIL) quand il est disponible, ce qui
#      permet en prime de redimensionner proprement les logos.
#      Sans Pillow, on se rabat sur PhotoImage : les PNG passeront,
#      le JPEG sera ignoré (avec un message, pas un crash).
#
#   2. RAMASSE-MIETTES
#      Tkinter ne garde qu'une référence FAIBLE vers les images.
#      Si l'objet PhotoImage n'est référencé que localement, Python le
#      détruit dès la sortie de la fonction et le logo disparaît de
#      l'écran (bug classique du « cadre vide »). On conserve donc
#      toutes les images dans une liste attachée à la fenêtre.
#
# Dans tous les cas, l'absence d'un logo ne doit JAMAIS empêcher SPRINGE
# de démarrer : chaque échec est silencieux côté utilisateur.

# Hauteur d'affichage des logos, en pixels. Les largeurs s'ajustent
# automatiquement pour préserver les proportions de chaque image.
HAUTEUR_LOGO = 46


def _dossier_images():
    """
    Localise le dossier contenant les logos.

    Ce module vit dans SPRINGE_utilisateur/00_fonctions/, les images dans
    SPRINGE_utilisateur/01_data/images/ : il faut donc remonter de deux
    crans (.parent.parent) depuis ce fichier.

    On teste malgré tout plusieurs emplacements, car le module peut être
    lancé isolément pendant le développement.
    """
    ici = Path(__file__).resolve().parent

    candidats = [
        ici.parent / "01_data" / "images",   # cas normal (module dans 00_fonctions)
        ici / "01_data" / "images",          # module à la racine du projet
        ici.parent.parent / "01_data" / "images",
    ]

    for dossier in candidats:
        if dossier.is_dir():
            return dossier

    return None


def _trouver_fichier(dossier, alias):
    """
    Retrouve un fichier image à partir d'une liste de noms possibles,
    SANS extension.

    Trois sources de variation sont absorbées ici :

      • L'EXTENSION — les logos peuvent être fournis en .png, .jpg, .jpeg…
        On ne compare donc que le nom de base (Path.stem).

      • L'ORDRE DES MOTS — le logo de l'OFB a été livré sous le nom
        « ofb_logo », alors qu'on attendait « logo_ofb ». D'où la liste
        d'alias : on accepte les deux, ainsi que les variantes probables.

      • LA CASSE — glob() est sensible à la casse sous Linux mais pas sous
        Windows. On compare nous-mêmes en minuscules pour obtenir un
        comportement identique sur les deux systèmes.

    Paramètres
    ----------
    dossier : Path ou None
    alias : list[str]
        Noms de base acceptés, du plus probable au moins probable.

    Retour : Path du fichier trouvé, ou None.
    """
    if dossier is None:
        return None

    # On indexe une fois le contenu du dossier : {nom_en_minuscules: Path}
    fichiers = {
        f.stem.lower(): f
        for f in dossier.iterdir()
        if f.is_file()
    }

    # On teste les alias dans l'ordre : le premier trouvé gagne.
    for nom in alias:
        if nom.lower() in fichiers:
            return fichiers[nom.lower()]

    return None


def _charger_logo(chemin, hauteur=HAUTEUR_LOGO):
    """
    Charge une image et la redimensionne à la hauteur voulue.

    Retour : objet image utilisable par Tkinter, ou None en cas d'échec.
    """
    if chemin is None or not chemin.exists():
        return None

    # ── Voie privilégiée : Pillow ────────────────────────────────────
    # Import local (et non en tête de module) : ainsi, si Pillow n'est
    # pas installé, seul le chargement des logos est affecté — le reste
    # de SPRINGE démarre normalement.
    try:
        from PIL import Image, ImageTk

        image = Image.open(chemin)

        # Calcul de la largeur proportionnelle à la hauteur cible,
        # pour ne pas déformer le logo.
        ratio = hauteur / image.height
        largeur = max(1, int(image.width * ratio))

        # LANCZOS donne le meilleur rendu en réduction. Le nom de la
        # constante a changé avec Pillow 10, d'où le getattr de repli.
        filtre = getattr(Image, "Resampling", Image).LANCZOS
        image = image.resize((largeur, hauteur), filtre)

        return ImageTk.PhotoImage(image)

    except ImportError:
        # Pillow absent : repli sur Tkinter seul, qui ne gère que
        # PNG et GIF, et ne sait pas redimensionner finement.
        if chemin.suffix.lower() in (".png", ".gif"):
            try:
                return tk.PhotoImage(file=str(chemin))
            except Exception:
                return None

        # JPEG sans Pillow : impossible, on abandonne proprement.
        return None

    except Exception:
        # Fichier corrompu, format exotique… : on ignore ce logo.
        return None


def _bandeau_logos(parent):
    """
    Construit le bandeau de logos en haut de la fenêtre.

    Disposition :
        « Conçu par »          à gauche  → logos OFB et CBN de Brest
        « Avec le soutien de » à droite  → logo DGITM

    Si aucun logo n'est chargeable, la fonction ne dessine rien du tout :
    mieux vaut pas de bandeau qu'un bandeau vide avec des intitulés
    orphelins.

    Retour : liste des objets image à conserver en référence.
    """
    dossier = _dossier_images()

    # Groupes : (intitulé, alignement, [liste d'alias par logo])
    groupes = [
        ("Outil conçu par", "left", [
            ["logo_ofb", "ofb_logo", "ofb"],
            ["logo_cbn_brest", "cbn_brest_logo", "logo_cbn", "cbn_brest", "cbn"],
        ]),
        ("Avec le soutien de la DGITM", "right", [
            ["logo_DGITM", "dgitm_logo", "dgitm"],
        ]),
    ]

    # On charge d'abord tout, pour savoir s'il y a matière à afficher.
    images_par_groupe = []

    for intitule, cote, logos in groupes:
        images = []

        for alias in logos:
            img = _charger_logo(_trouver_fichier(dossier, alias))

            if img is not None:
                images.append(img)

        images_par_groupe.append((intitule, cote, images))

    # Aucun logo trouvé → on n'affiche aucun bandeau.
    if not any(images for _, _, images in images_par_groupe):
        return []

    bandeau = tk.Frame(parent)
    bandeau.pack(fill="x", padx=18, pady=(10, 0))

    references = []

    for intitule, cote, images in images_par_groupe:
        if not images:
            continue

        # Un bloc par groupe : l'intitulé au-dessus, les logos en dessous.
        bloc = tk.Frame(bandeau)
        bloc.pack(side=cote, anchor="n")

        tk.Label(
            bloc,
            text=intitule,
            font=("Arial", 8),
            fg="#666666",
            anchor="w" if cote == "left" else "e"
        ).pack(
            anchor="w" if cote == "left" else "e",
            pady=(0, 3)
        )

        ligne = tk.Frame(bloc)
        ligne.pack(anchor="w" if cote == "left" else "e")

        for img in images:
            tk.Label(
                ligne,
                image=img
            ).pack(
                side="left",
                padx=(0, 8)
            )

            # Indispensable : sans cette référence conservée, Python
            # détruit l'image et Tkinter affiche un cadre vide.
            references.append(img)

    return references


def fenetre_accueil():
    """
    Affiche la fenêtre d'accueil SPRINGE.
    Bloque jusqu'à ce que l'utilisateur clique sur "Démarrer".
    """

    # tk.Tk() crée la fenêtre racine Tkinter.
    # withdraw() la cache immédiatement : on va créer une Toplevel propre
    # à la place, ce qui donne plus de contrôle sur la mise en forme.
    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    fenetre.title("SPRINGE — Bienvenue")
    fenetre.resizable(False, False)

    # ═══════════════════════════════════════════════════════════════════════
    # CENTRAGE ET DIMENSIONNEMENT AUTOMATIQUE
    # ═══════════════════════════════════════════════════════════════════════

    def centrer_fenetre(fenetre, largeur=580):
        """
        Dimensionne et centre la fenêtre.

        La hauteur est calculée automatiquement à partir de la taille
        réelle de tous les widgets présents dans la fenêtre.

        Ainsi, si la hauteur du bouton augmente, la fenêtre augmente
        automatiquement elle aussi.
        """

        # Force Tkinter à calculer la taille réelle de tous les widgets.
        fenetre.update_idletasks()

        # Hauteur nécessaire au contenu + marge de confort.
        hauteur = fenetre.winfo_reqheight() + 30

        # Garde-fou : la fenêtre ne doit jamais dépasser 90 % de la
        # hauteur de l'écran.
        hauteur_max = int(fenetre.winfo_screenheight() * 0.90)
        hauteur = min(hauteur, hauteur_max)

        largeur_ecran = fenetre.winfo_screenwidth()
        hauteur_ecran = fenetre.winfo_screenheight()

        # Calcul de la position pour centrer la fenêtre.
        x = (largeur_ecran - largeur) // 2
        y = (hauteur_ecran - hauteur) // 2

        # Application de la taille et de la position.
        fenetre.geometry(
            f"{largeur}x{hauteur}+{x}+{y}"
        )

    # ── Bandeau institutionnel (logos) ──────────────────────────────────
    fenetre._logos = _bandeau_logos(fenetre)

    # ── Titre principal : « SPRING » + « eee » en exposant ───────────────
    # Un Label Tkinter n'affiche qu'UNE seule police : impossible d'y mettre
    # une partie du texte en exposant. On place donc DEUX Labels côte à côte
    # dans un même cadre :
    #   - « SPRING » en grande taille (22) ;
    #   - « eee » en petite taille (12), collé en haut du cadre.
    #
    # POURQUOI PAS DES CARACTÈRES UNICODE EXPOSANTS (ᵉᵉᵉ) : ils n'existent
    # pas dans la police Arial. Windows les emprunterait à une autre police,
    # avec un rendu imprévisible selon le poste (voire des carrés vides).
    # Deux Labels donnent le même rendu partout.
    cadre_titre = tk.Frame(fenetre)
    cadre_titre.pack(pady=6)          # le pady du titre passe sur le cadre

    tk.Label(
        cadre_titre,
        text="SPRING",
        font=("Arial", 22, "bold"),
        padx=0                        # aucun espace : « eee » doit être collé
    ).pack(side="left")               # side="left" : les deux Labels s'alignent en ligne

    tk.Label(
        cadre_titre,
        text="eee",
        font=("Arial", 12, "bold"),
        padx=0,
        pady=2                        # petit décalage vers le bas : aligne le haut
                                      # des « e » sur le haut des majuscules
    ).pack(side="left", anchor="n")   # anchor="n" : collé en HAUT du cadre = exposant

    tk.Label(
        fenetre,
        text="Soutien à la PRiorisation des INterventions de Gestion des EEE",
        font=("Arial", 10, "italic"),
        wraplength=500
    ).pack()

    tk.Label(
        fenetre,
        text="Version_26.9.0",
        font=("Arial", 9),
        fg="gray"
    ).pack(pady=(0, 5))

    # ── Séparateur visuel ───────────────────────────────────────────────
    ttk.Separator(
        fenetre,
        orient="horizontal"
    ).pack(
        fill="x",
        padx=20,
        pady=8
    )

    # ── Texte de présentation ──────────────────────────────────────────
    tk.Label(
        fenetre,
        text=(
            "Outil d'aide à la décision (OAD) développé au sein de "
            "l'Office français de la biodiversité (OFB) et du "
            "Conservatoire botanique national de Brest (CBN de Brest), "
            "avec le soutien de la Direction générale des infrastructures, "
            "des transports et des mobilités (DGITM).\n\n"
            "OAD à destination des directions interdépartementales des "
            "routes (DIR) et des gestionnaires d'infrastructures linéaires "
            "routières, pour les aider dans la priorisation de leurs "
            "interventions de gestion relatives à la problématique des "
            "Plantes Exotiques Envahissantes (EEE)."
        ),
        font=("Arial", 10),
        wraplength=500,
        justify="center"
    ).pack(pady=5)

    # ── Séparateur visuel ───────────────────────────────────────────────
    ttk.Separator(
        fenetre,
        orient="horizontal"
    ).pack(
        fill="x",
        padx=20,
        pady=8
    )

    # ── Annonce des étapes ──────────────────────────────────────────────
    tk.Label(
        fenetre,
        text="Avant de lancer le calcul, vous allez devoir renseigner :",
        font=("Arial", 10, "bold"),
        anchor="w"
    ).pack(
        padx=30,
        anchor="w",
        pady=(5, 2)
    )

    etapes = [
        "1.  Le nom de votre structure et votre nom",

        "2.  Le dossier où sauvegarder les fichiers de sortie de SPRINGE\n"
        "      (par défaut, sauvegarde dans SPRINGE_utilisateur > 02_outputs)",

        "3.  Votre zone d'étude\n"
        "      (ex : votre CEI, votre commune, votre département…)",

        "4.  Les données cartographiques disponibles et nécessaires\n"
        "      à l'exécution de SPRINGE",
    ]

    for etape in etapes:
        tk.Label(
            fenetre,
            text=etape,
            font=("Arial", 10),
            wraplength=500,
            justify="left",
            anchor="w"
        ).pack(
            padx=40,
            anchor="w",
            pady=1
        )

    # ── Séparateur visuel ───────────────────────────────────────────────
    ttk.Separator(
        fenetre,
        orient="horizontal"
    ).pack(
        fill="x",
        padx=20,
        pady=8
    )

    # ── Avertissement connexion internet ────────────────────────────────
    tk.Label(
        fenetre,
        text="⚠️  Une connexion internet est indispensable.",
        font=("Arial", 11, "bold"),
        fg="red"
    ).pack(pady=3)

    tk.Label(
        fenetre,
        text=(
            "SPRINGE télécharge automatiquement des données en flux, via "
            "des API (interfaces de programmation d'applications) telles que "
            "la BD TOPO, l'IGN, l'INPN, la SNCF.\n"
            "Merci de vérifier la stabilité de votre connexion internet "
            "avant de continuer."
        ),
        font=("Arial", 9),
        fg="red",
        wraplength=500,
        justify="center"
    ).pack(pady=(0, 8))

    # ── Bouton Démarrer ─────────────────────────────────────────────────
    # Le pady=15 augmente la hauteur interne du bouton.
    #
    # IMPORTANT :
    # Le bouton est créé AVANT l'appel à centrer_fenetre().
    # Ainsi winfo_reqheight() tient bien compte de sa nouvelle hauteur.

    tk.Button(
        fenetre,
        text="▶   Démarrer SPRINGE",
        font=("Arial", 11, "bold"),
        bg="#2e7d32",
        fg="white",
        padx=20,
        pady=15,
        relief="flat",
        command=fenetre.destroy
    ).pack(pady=20)

    # ── Dimensionnement final ───────────────────────────────────────────
    # Tous les widgets existent maintenant.
    # Tkinter peut donc calculer la hauteur réellement nécessaire.
    centrer_fenetre(fenetre)

    # ── Blocage de l'interaction ────────────────────────────────────────
    # grab_set() est placé APRÈS le dimensionnement.
    fenetre.grab_set()

    # Attend que l'utilisateur clique sur "Démarrer".
    root.wait_window(fenetre)

    # Ferme proprement la fenêtre racine cachée.
    root.destroy()
