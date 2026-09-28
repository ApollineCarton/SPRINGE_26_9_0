# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "traitement_en_cours"
Date : 2026-04-13
Objectif : Fenêtre de suivi d'avancée du code SPRINGE
═══════════════════════════════════════════════════════════════════

DEUX MODES disponibles selon le paramètre `total` :

────────────────────────────────────────────────────────────────
MODE 1 — Message simple (comportement d'origine, inchangé)
    Appel  : fenetre = traitement_en_cours("Mon message")
    Usage  : fenetre.destroy() pour fermer à la fin
────────────────────────────────────────────────────────────────
MODE 2 — Barre de progression (nouveau)
    Appel  : fenetre = traitement_en_cours("Titre bloc", total=N)
    Usage dans la boucle :
        fenetre.avancer(label_couche)   ← incrémente + met à jour le texte
    Fin    : fenetre.destroy()
────────────────────────────────────────────────────────────────
FONCTION SÉPARÉE — Message à fermeture automatique (ajout 26.9.0)
    Appel  : message_temporaire("Titre", "Message", duree_ms=3000)
    Usage  : rien à fermer, la fenêtre disparaît seule et le script
             reprend. Remplace un messagebox à bouton OK quand on ne
             veut PAS que l'utilisateur ait à cliquer pour continuer.
────────────────────────────────────────────────────────────────

Parameters
----------
message : str
    Titre / description du bloc de traitement affiché en haut.
total : int, optionnel (défaut = None)
    Nombre total d'étapes. Si fourni → active la barre de progression.

Returns
-------
fenetre : tk.Tk
    L'objet fenêtre. Appeler fenetre.destroy() à la fin du bloc.
    En mode progression, l'objet a aussi la méthode fenetre.avancer(label).
"""

import tkinter as tk
from tkinter import ttk  # ttk contient le widget Progressbar


# ════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ════════════════════════════════════════════════════════════════

def traitement_en_cours(message: str, total: int = None):
    """
    Crée et affiche une fenêtre de suivi.

    Si `total` est fourni → mode barre de progression.
    Sinon               → mode message simple (comportement d'origine).
    """

    # ── Création de la fenêtre racine Tkinter ──────────────────
    # tk.Tk() crée UNE SEULE fenêtre principale.
    # C'est important : on ne rappelle jamais tk.Tk() ailleurs
    # pendant que cette fenêtre est ouverte, sinon on multiplie les fenêtres.
    fenetre = tk.Tk()
    fenetre.title("SPRINGE - Traitement")
    fenetre.resizable(False, False)  # taille fixe, pas redimensionnable

    # ── Label titre en haut (commun aux 2 modes) ───────────────
    label_titre = tk.Label(
        fenetre,
        text=f"⚙️ Traitement en cours... {message}",
        padx=20, pady=10
    )
    label_titre.pack()

    # ════════════════════════════════════════════════════════════
    # MODE 2 — Barre de progression
    # ════════════════════════════════════════════════════════════

    if total is not None:

        # Barre de progression horizontale
        # mode="determinate" = barre qui avance d'un % précis (≠ "indeterminate" = animation infinie)
        # length = largeur en pixels
        barre = ttk.Progressbar(fenetre, length=400, mode="determinate", maximum=total)
        barre.pack(padx=20, pady=5)

        # Label affichant le % numérique sous la barre
        label_pct = tk.Label(fenetre, text="0%", pady=5)
        label_pct.pack()

        # Label affichant le nom de la couche en cours de chargement
        label_couche = tk.Label(fenetre, text="Initialisation...", padx=20, pady=5)
        label_couche.pack()

        # Compteur interne stocké dans un dict mutable pour pouvoir
        # le modifier depuis la fonction imbriquée `avancer` ci-dessous.
        # (Un simple int ne serait pas modifiable par référence en Python.)
        etat = {"compteur": 0}

        # ── Méthode avancer() ───────────────────────────────────
        # Appelée UNE FOIS par couche chargée dans la boucle principale.
        # Elle met à jour la barre, le %, et le texte de la couche.
        def avancer(nom_couche: str):
            """
            Incrémente la barre d'une étape et met à jour les labels.

            Parameters
            ----------
            nom_couche : str
                Texte à afficher (ex: "SIC (ZSC/SIC)") — correspond
                au 3e élément de chaque tuple dans la liste `couches`.
            """
            # On incrémente le compteur interne
            etat["compteur"] += 1

            # On met à jour la valeur de la barre (de 0 à `total`)
            barre["value"] = etat["compteur"]

            # Calcul du pourcentage arrondi à l'entier
            pct = int((etat["compteur"] / total) * 100)
            label_pct.config(text=f"{pct}%")

            # Mise à jour du texte : quelle couche vient d'être chargée
            label_couche.config(text=f"Chargement : {nom_couche}")

            # root.update() force Tkinter à redessiner la fenêtre immédiatement.
            # Sans ça, l'interface ne se rafraîchit pas pendant que Python
            # est occupé dans la boucle de chargement.
            fenetre.update()

        # On attache la méthode directement à l'objet fenetre
        # pour pouvoir écrire fenetre.avancer(...) depuis l'extérieur
        fenetre.avancer = avancer

    # ════════════════════════════════════════════════════════════
    # MODE 1 — Message simple (comportement d'origine)
    # ════════════════════════════════════════════════════════════

    else:
        # Pas de barre, juste redimensionnement automatique selon le texte
        fenetre.update_idletasks()
        fenetre.geometry(
            f"{label_titre.winfo_reqwidth() + 40}x{label_titre.winfo_reqheight() + 40}"
        )

    # Premier affichage de la fenêtre dans les deux cas
    fenetre.update()

    return fenetre


# ════════════════════════════════════════════════════════════════
# MESSAGE À FERMETURE AUTOMATIQUE (ajout 26.9.0)
# ════════════════════════════════════════════════════════════════
# POURQUOI CETTE FONCTION
# ─────────────────────────────────────────────────────────────────
# Après le chargement des API, SPRINGE affichait un messagebox
# « Chargement terminé ! » avec un bouton OK. Tant que l'utilisateur ne
# cliquait pas, les calculs NE DÉMARRAIENT PAS : un gestionnaire parti
# prendre un café pouvait revenir vingt minutes plus tard devant un
# traitement qui n'avait pas commencé.
#
# Cette fenêtre informe puis se ferme TOUTE SEULE après quelques secondes.
#
# POURQUOI mainloop() ET PAS time.sleep()
# ─────────────────────────────────────────────────────────────────
# Avec time.sleep(), Python dort : Tkinter ne redessine plus la fenêtre,
# et Windows peut l'afficher « (Ne répond pas) ». Avec after() +
# mainloop(), Tkinter reste actif pendant toute l'attente (la fenêtre se
# dessine, peut être déplacée), puis after() déclenche sa destruction,
# ce qui termine mainloop() et rend la main au script.

def message_temporaire(titre: str, message: str, duree_ms: int = 3000):
    """
    Affiche un message d'information qui se ferme automatiquement.

    Bloque le script PENDANT duree_ms millisecondes seulement, sans
    aucune action requise de l'utilisateur.

    Parameters
    ----------
    titre : str
        Texte de la barre de titre.
    message : str
        Message principal (les retours à la ligne sont respectés).
    duree_ms : int, optionnel (défaut = 3000)
        Durée d'affichage en millisecondes.
    """

    # Une seule racine Tk, détruite à la fin : même règle que
    # traitement_en_cours() ci-dessus (jamais deux tk.Tk() ouverts).
    fenetre = tk.Tk()
    fenetre.title(titre)
    fenetre.resizable(False, False)

    # Premier plan : la fenêtre s'ouvre après plusieurs minutes de
    # chargement des API, l'utilisateur est peut-être sur une autre
    # application. "-topmost" la place au-dessus de tout.
    fenetre.attributes("-topmost", True)

    # ── Message principal ───────────────────────────────────────
    tk.Label(
        fenetre,
        text=message,
        font=("Arial", 10),
        justify="center",
        wraplength=500,      # retour à la ligne automatique (pixels) ; 500 évite
                             # qu'un mot isolé (« patienter ») tombe seul en fin de message
        padx=25, pady=15
    ).pack()

    # ── Mention de fermeture automatique ────────────────────────
    # Sans elle, l'utilisateur chercherait un bouton, puis croirait à
    # un bug en voyant la fenêtre disparaître.
    tk.Label(
        fenetre,
        text="Cette fenêtre se ferme automatiquement, "
             "les calculs démarrent sans action de votre part.",
        font=("Arial", 8, "italic"),
        fg="gray40",
        wraplength=500,
        padx=25
    ).pack(pady=(0, 12))

    # ── Centrage à l'écran ──────────────────────────────────────
    # update_idletasks() calcule la taille réelle du contenu sans
    # afficher ; on centre ensuite avec cette taille.
    fenetre.update_idletasks()
    largeur = fenetre.winfo_reqwidth()
    hauteur = fenetre.winfo_reqheight()
    x = (fenetre.winfo_screenwidth() // 2) - (largeur // 2)
    y = (fenetre.winfo_screenheight() // 2) - (hauteur // 2)
    fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    # ── Fermeture programmée ────────────────────────────────────
    # after(délai, fonction) : Tkinter appellera fenetre.destroy au
    # bout de duree_ms. La destruction de la racine termine mainloop().
    # Si l'utilisateur ferme lui-même la fenêtre par la croix avant la
    # fin du délai, mainloop() se termine aussi : le script continue.
    fenetre.after(duree_ms, fenetre.destroy)
    fenetre.mainloop()

