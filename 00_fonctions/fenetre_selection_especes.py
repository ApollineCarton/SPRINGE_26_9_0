# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre ÉTAPE 4/4 — "Sélection des espèces EEE"
Version 26.9.0 (septembre 2026) : première fenêtre de l'étape 4
« Compréhension des données d'entrée ».
Objectif : laisser le gestionnaire choisir les espèces à prendre en compte
           dans l'analyse. Par défaut, les 4 espèces principales sont
           retenues ; il peut restreindre à celles qui l'intéressent.
═══════════════════════════════════════════════════════════════════════════

POURQUOI CETTE FENÊTRE
─────────────────────────────────────────────────────────────────
Le compte-rendu du 30/03/2026 (CD22, Frédéric Morin) demandait de pouvoir
prioriser un nombre restreint d'espèces. Plutôt que de figer une liste,
on laisse le gestionnaire cocher ce qui le concerne : une DIR peut vouloir
ne traiter que la Berce du Caucase, une autre les seules Renouées.

Le filtrage s'applique EN AMONT de tous les calculs : les points EEE des
espèces non cochées sont simplement retirés de gdf_EEE. Tous les
indicateurs (densité, MS1, N1, P…) travaillent alors sur le sous-ensemble
retenu, sans autre modification.

CONVENTION
─────────────────────────────────────────────────────────────────
Les clés retournées sont des codes COURTS et FIXES (Renouees, Ailante…),
indépendants de la couche EEE fournie. Le script principal les traduit en
species_name_sci via fenetre_mapping_especes.CODES_SELECTION_VERS_SCI,
puis filtre gdf_EEE sur la colonne 'species_name_sci' produite par le
mapping interactif (et non plus sur une colonne 'plante' codée en dur).

Ce que la fenêtre RENVOIE (dict) :
    {
      "annule"  : bool,        # True si l'utilisateur a cliqué Annuler
      "especes" : list[str],   # libellés courts retenus, ex. ['Renouees','Ailante']
    }
═══════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


# Catalogue des espèces proposées.
# (libellé_court, nom_affiché, cochée_par_défaut)
# Les 4 principales sont cochées ; « Autres EEE » ne l'est pas, car c'est
# une catégorie fourre-tout : la cocher revient à réintégrer tout point
# non identifié précisément. Le gestionnaire décide en connaissance de cause.
ESPECES_CATALOGUE = [
    ("Renouees",     "Renouées asiatiques (Reynoutria sp.)",   True),
    ("Ailante",      "Ailante (Ailanthus altissima)",          True),
    ("Ambroisie",    "Ambroisie (Ambrosia artemisiifolia)",    True),
    ("BerceCaucase", "Berce du Caucase (Heracleum mant.)",     True),
    ("Autre",        "Autres EEE (non listées ci-dessus)",     False),
]


def fenetre_selection_especes():

    # Dictionnaire de retour, pré-rempli avec les valeurs par défaut.
    resultats = {"annule": False, "especes": []}

    # ── Racine cachée + Toplevel (même patron que les autres fenêtres) ──
    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    # Barre de titre : numéro d'étape ajouté en 26.9.0.
    fenetre.title("SPRINGE — Étape 4/4 · Espèces à analyser")
    fenetre.resizable(False, False)

    def centrer_fenetre(fenetre, largeur=560, hauteur=None):
        # Hauteur déduite du contenu après mise en page (voir fenetre_accueil).
        fenetre.update_idletasks()
        if hauteur is None:
            hauteur = fenetre.winfo_reqheight() + 20
        le, he = fenetre.winfo_screenwidth(), fenetre.winfo_screenheight()
        x = (le // 2) - (largeur // 2)
        y = (he // 2) - (hauteur // 2)
        fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    # ── Titre + intro ───────────────────────────────────────────────────
    # Titre de l'étape (ajout 26.9.0), même format que les autres fenêtres.
    tk.Label(
        fenetre,
        text="Étape 4 / 4 — Compréhension des données d'entrée",
        font=("Arial", 13, "bold"),
        pady=8
    ).pack()

    # Ancien titre, conservé comme sous-titre : il dit précisément ce que
    # l'on demande sur CET écran de l'étape 4.
    tk.Label(
        fenetre,
        text="Espèces à prendre en compte",
        font=("Arial", 11, "bold"),
        pady=2
    ).pack()

    tk.Label(
        fenetre,
        text=(
            "Par défaut, SPRINGE analyse les 4 espèces principales. "
            "Vous pouvez restreindre l'analyse aux seules espèces qui vous "
            "concernent : les points des espèces décochées seront ignorés."
        ),
        font=("Arial", 10),
        wraplength=500,
        justify="center",
        fg="#444444"
    ).pack(pady=(0, 6))

    ttk.Separator(fenetre, orient="horizontal").pack(fill="x", padx=20, pady=6)

    # ── Cases à cocher ──────────────────────────────────────────────────
    # Une IntVar par espèce, mémorisant l'état coché (1) / décoché (0).
    cadre = tk.Frame(fenetre)
    cadre.pack(padx=40, anchor="w", pady=4)

    variables = {}   # {libellé_court : IntVar}
    for cle, libelle, par_defaut in ESPECES_CATALOGUE:
        var = tk.IntVar(value=1 if par_defaut else 0)
        variables[cle] = var
        tk.Checkbutton(
            cadre,
            text=libelle,
            variable=var,
            font=("Arial", 10),
            anchor="w",
            padx=4, pady=3,
            cursor="hand2"
        ).pack(anchor="w")

    ttk.Separator(fenetre, orient="horizontal").pack(fill="x", padx=20, pady=8)

    # ── Footer Annuler / Continuer ──────────────────────────────────────
    cadre_footer = tk.Frame(fenetre)
    cadre_footer.pack(pady=4)

    def annuler():
        resultats["annule"] = True
        fenetre.destroy()

    def valider():
        # Espèces réellement cochées.
        retenues = [cle for cle, var in variables.items() if var.get() == 1]

        # Garde-fou : au moins une espèce, sinon SPRINGE n'a rien à scorer.
        if not retenues:
            messagebox.showwarning(
                "Aucune espèce sélectionnée",
                "Veuillez cocher au moins une espèce à analyser."
            )
            return

        resultats["especes"] = retenues
        fenetre.destroy()

    tk.Button(
        cadre_footer, text="✖  Annuler", font=("Arial", 10),
        fg="gray", command=annuler, width=14
    ).grid(row=0, column=0, padx=10)

    tk.Button(
        cadre_footer, text="Continuer  ▶", font=("Arial", 10, "bold"),
        bg="#1565c0", fg="white", relief="flat", command=valider, width=14
    ).grid(row=0, column=1, padx=10)

    # Croix de fermeture = Annuler. Sans cette ligne, fermer par la croix
    # renvoyait especes=[] et annule=False : le filtrage aurait vidé
    # gdf_EEE et arrêté SPRINGE avec un message trompeur.
    fenetre.protocol("WM_DELETE_WINDOW", annuler)

    # ── Dimensionnement final + blocage ─────────────────────────────────
    centrer_fenetre(fenetre)
    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()

    return resultats


# Démonstration locale (ne s'exécute qu'en lançant directement ce fichier).
if __name__ == "__main__":
    print(fenetre_selection_especes())
