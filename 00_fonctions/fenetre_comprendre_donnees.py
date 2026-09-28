# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre "Comprendre vos données"
Date : 2026-07-07
Objectif : recueillir, en langage gestionnaire, les 2 informations qui
           conditionnent le calcul de l'axe densité EEE :
             1. la SOURCE des points de présence EEE   -> paramètre source_points
             2. la NATURE de la couche de tronçons (PR) -> paramètre source_pr
═══════════════════════════════════════════════════════════════════════════

PLACEMENT dans la séquence : après la fenêtre "données optionnelles",
juste avant le récapitulatif (elle caractérise des couches déjà déclarées).

Style : calqué sur les fenêtres existantes (fenetre_accueil,
fenetre_identification…) — même patron Tk()/Toplevel, mêmes polices Arial,
mêmes boutons plats verts/bleus, même footer Annuler/Continuer, même
mécanique de retour via un dictionnaire 'resultats'.

Ce que la fenêtre RENVOIE (dict) :
    {
      "annule"        : bool,   # True si l'utilisateur a cliqué Annuler
      "source_points" : str,    # 'camalien'  ou 'autre'
      "source_pr"     : str,    # 'si_route'  ou 'autre'
    }
Ces deux chaînes se branchent directement dans calculer_densite_EEE(...).
"""

import tkinter as tk
from tkinter import ttk


def fenetre_comprendre_donnees():

    # ── Dictionnaire de retour, pré-rempli avec les valeurs PAR DÉFAUT ───────
    #    (le cas le plus courant : points CamAlien + couche SI ROUTE).
    #    Si l'utilisateur ne touche à rien, ce sont ces valeurs qui repartent.
    resultats = {"annule": False, "source_points": "camalien", "source_pr": "si_route"}

    # ── Fenêtre racine cachée + Toplevel propre (même patron que le reste) ──
    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    fenetre.title("SPRINGE — Comprendre vos données")
    fenetre.resizable(False, False)

    # ── Centrage à l'écran (fonction identique aux autres fenêtres) ─────────
    def centrer_fenetre(fenetre, largeur=620, hauteur=600):
        fenetre.update_idletasks()
        largeur_ecran = fenetre.winfo_screenwidth()
        hauteur_ecran = fenetre.winfo_screenheight()
        x = (largeur_ecran // 2) - (largeur // 2)
        y = (hauteur_ecran // 2) - (hauteur // 2)
        fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    centrer_fenetre(fenetre)

    # ── Titre + intro (on explique POURQUOI on pose ces questions) ──────────
    tk.Label(
        fenetre,
        text="Comprendre vos données",
        font=("Arial", 13, "bold"),
        pady=8
    ).pack()

    tk.Label(
        fenetre,
        text=(
            "Ces deux informations permettent à SPRINGE d'adapter le calcul de la "
            "densité des EEE à vos données. Choisissez, pour chaque question, "
            "l'option qui correspond à votre situation."
        ),
        font=("Arial", 10),
        wraplength=560,
        justify="center"
    ).pack(pady=(0, 4))

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=6)

    # ── Variables Tkinter qui mémorisent le choix de chaque question ────────
    #    On leur donne la valeur par défaut ; elles seront relues à la validation.
    var_points = tk.StringVar(value="camalien")
    var_pr = tk.StringVar(value="si_route")

    # ── Fabrique réutilisable d'un "bloc question" ──────────────────────────
    #    Chaque bloc = un titre + deux boutons d'option (façon Oui/Non) + une
    #    ligne d'EXPLICATION qui se met à jour selon l'option sélectionnée.
    #    C'est ce qui rend la fenêtre "compréhensible" : l'utilisateur voit en
    #    direct l'effet de son choix, sans avoir à connaître les rouages.
    #
    #    Paramètres :
    #      parent  : conteneur Tk où dessiner le bloc
    #      titre   : question posée (texte)
    #      options : liste de tuples (libellé_bouton, valeur_interne, explication)
    #      var     : la StringVar qui stocke la valeur choisie
    def bloc_question(parent, titre, options, var):

        # Titre de la question, aligné à gauche.
        tk.Label(
            parent,
            text=titre,
            font=("Arial", 11, "bold"),
            wraplength=560,
            justify="left",
            anchor="w"
        ).pack(padx=30, anchor="w", pady=(8, 4))

        # Rangée horizontale des boutons d'option.
        cadre_boutons = tk.Frame(parent)
        cadre_boutons.pack(padx=30, anchor="w")

        # Ligne d'explication (dynamique) sous les boutons.
        label_explication = tk.Label(
            parent,
            text="",
            font=("Arial", 9),
            fg="#444444",
            wraplength=560,
            justify="left",
            anchor="w"
        )
        label_explication.pack(padx=30, anchor="w", pady=(4, 2))

        # Dictionnaires de travail : accès rapide aux boutons et aux explications.
        boutons = {}
        explication_par_valeur = {valeur: expl for (_, valeur, expl) in options}

        # Rafraîchit l'apparence : le bouton choisi passe en vert (comme le style
        # "Démarrer"), l'autre en gris neutre ; l'explication affichée suit.
        def rafraichir():
            for valeur, bouton in boutons.items():
                if var.get() == valeur:
                    bouton.configure(bg="#2e7d32", fg="white")   # sélectionné
                else:
                    bouton.configure(bg="#e0e0e0", fg="black")   # non sélectionné
            label_explication.configure(text=explication_par_valeur.get(var.get(), ""))

        # Création des boutons. Chaque clic mémorise la valeur puis rafraîchit.
        for i, (libelle, valeur, _expl) in enumerate(options):
            # v=valeur : on "fige" la valeur dans le paramètre par défaut, sinon
            # toutes les fonctions partageraient la dernière valeur de la boucle.
            def choisir(v=valeur):
                var.set(v)
                rafraichir()

            bouton = tk.Button(
                cadre_boutons,
                text=libelle,
                font=("Arial", 10),
                relief="flat",
                padx=10, pady=6,
                width=32,
                wraplength=230,
                command=choisir
            )
            bouton.grid(row=0, column=i, padx=(0, 10), pady=2)
            boutons[valeur] = bouton

        # Affichage initial (met en avant la valeur par défaut + son explication).
        rafraichir()

    # ── QUESTION 1 : source des points EEE -> pilote source_points ──────────
    bloc_question(
        fenetre,
        titre="1.  D'où proviennent vos points de présence EEE ?",
        options=[
            ("Uniquement de la caméra CamAlien",
             "camalien",
             "→ SPRINGE utilise la taille des taches (largeur × longueur) relevée "
             "par la caméra pour pondérer la densité."),
            ("D'autres sources, ou plusieurs\nsources mélangées",
             "autre",
             "→ SPRINGE compte le nombre de points (méthode robuste quelle que soit "
             "l'origine des données : INPN, inventaires, etc.)."),
        ],
        var=var_points
    )

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=8)

    # ── QUESTION 2 : nature de la couche de tronçons -> pilote source_pr ────
    bloc_question(
        fenetre,
        titre="2.  Votre couche de tronçons (PR) provient-elle du SI ROUTE ?",
        options=[
            ("Oui, couche SI ROUTE\n(avec dist_deb / dist_fin)",
             "si_route",
             "→ SPRINGE calcule la densité par kilomètre, comparable d'un tronçon "
             "à l'autre."),
            ("Non, ou je ne sais pas",
             "autre",
             "→ SPRINGE utilise la valeur brute (non ramenée au km). La longueur "
             "pourra être intégrée plus tard."),
        ],
        var=var_pr
    )

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=8)

    # ── Footer Annuler / Continuer (identique à fenetre_identification) ─────
    cadre_footer = tk.Frame(fenetre)
    cadre_footer.pack(pady=4)

    def annuler():
        """Ferme tout et signale l'annulation (le script s'arrêtera proprement)."""
        resultats["annule"] = True
        fenetre.destroy()

    def valider():
        """Relit les StringVar, remplit le dict de retour et ferme la fenêtre."""
        resultats["source_points"] = var_points.get()
        resultats["source_pr"] = var_pr.get()
        fenetre.destroy()

    tk.Button(
        cadre_footer,
        text="✖  Annuler",
        font=("Arial", 10),
        fg="gray",
        command=annuler,
        width=14
    ).grid(row=0, column=0, padx=10)

    tk.Button(
        cadre_footer,
        text="Continuer  ▶",
        font=("Arial", 10, "bold"),
        bg="#1565c0",
        fg="white",
        relief="flat",
        command=valider,
        width=14
    ).grid(row=0, column=1, padx=10)

    # ── Blocage jusqu'à fermeture (même mécanique que les autres fenêtres) ──
    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()

    return resultats


# ── Démonstration locale (ne s'exécute PAS à l'import, seulement si on lance
#    directement ce fichier ; pratique pour tester la fenêtre isolément). ─────
if __name__ == "__main__":
    print(fenetre_comprendre_donnees())
