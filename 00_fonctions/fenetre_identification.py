# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre 1 — IDENTIFICATION : structure, opérateur, dossier de sortie
═══════════════════════════════════════════════════════════════════════════
Regroupe les 3 informations liées à « qui fait le traitement et où
sauvegarder ». Retourne un dict : DIR, NOM, OUTPUT_DIR, annule.

Ce module suit la convention des autres fenêtres du projet
(fenetre_donnees_indicateurs.py, fenetre_comprendre_donnees.py) :
une fenêtre = un fichier, chargé automatiquement par la boucle
importlib du script principal depuis 00_fonctions/.

Appel depuis le script principal :
    _res1 = fenetre_identification.fenetre_identification()
═══════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from pathlib import Path


def fenetre_identification():
    """
    Fenêtre 1 — Identification de la structure et choix du dossier de sortie.
    Retourne un dict avec les clés : DIR, NOM, OUTPUT_DIR.
    """

    resultats = {"DIR": None, "NOM": None, "OUTPUT_DIR": None, "annule": False}

    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    fenetre.title("SPRINGE — Étape 1/4 · Identification")
    fenetre.resizable(False, False)
    fenetre.geometry("500x370")

    # ── En-tête ──────────────────────────────────────────────────────────
    tk.Label(
        fenetre,
        text="Étape 1 / 4 — Identification",
        font=("Arial", 13, "bold"),
        pady=10
    ).pack()

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=5)

    # ── Cadre formulaire ─────────────────────────────────────────────────
    # on utilise un Frame pour aligner proprement les labels et les champs
    cadre = tk.Frame(fenetre, padx=30)
    cadre.pack(fill='x', pady=5)

    # Champ 1 : nom de la structure
    tk.Label(
        cadre,
        text="Nom de votre structure :",
        font=("Arial", 10),
        anchor="w"
    ).grid(row=0, column=0, sticky="w", pady=6)

    tk.Label(
        cadre,
        text="(ex : DIRCO, CD22, RNES…)",
        font=("Arial", 9),
        fg="gray",
        anchor="w"
    ).grid(row=1, column=0, sticky="w", pady=(0, 8))

    var_dir = tk.StringVar()
    tk.Entry(cadre, textvariable=var_dir, width=28, font=("Arial", 10)).grid(
        row=0, column=1, rowspan=2, padx=10, sticky="w"
    )

    # Champ 2 : nom opérateur
    tk.Label(
        cadre,
        text="Votre nom :",
        font=("Arial", 10),
        anchor="w"
    ).grid(row=2, column=0, sticky="w", pady=6)

    var_nom = tk.StringVar()
    tk.Entry(cadre, textvariable=var_nom, width=28, font=("Arial", 10)).grid(
        row=2, column=1, padx=10, sticky="w"
    )

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=10)

    # ── Sélection dossier de sortie ──────────────────────────────────────
    # L'utilisateur peut parcourir son arborescence ou laisser vide
    # (le fallback vers 02_outputs/ sera appliqué dans la logique ci-dessous).
    cadre_dossier = tk.Frame(fenetre, padx=30)
    cadre_dossier.pack(fill='x')

    tk.Label(
        cadre_dossier,
        text="Dossier de sauvegarde des résultats :",
        font=("Arial", 10, "bold"),
        anchor="w"
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

    # Texte qui affiche le chemin sélectionné (ou le message par défaut)
    var_dossier = tk.StringVar(
        value="(par défaut : dossier 02_outputs/ du programme)"
    )
    label_dossier = tk.Label(
        cadre_dossier,
        textvariable=var_dossier,
        font=("Arial", 9),
        fg="gray",
        wraplength=400,
        anchor="w",
        justify="left"
    )
    label_dossier.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))

    def choisir_dossier():
        """Ouvre un explorateur de fichiers pour choisir le dossier."""
        chemin = filedialog.askdirectory(
            title="Choisissez le dossier où sauvegarder les résultats SPRINGE"
        )
        if chemin:
            # Chemin valide → on l'affiche en noir
            var_dossier.set(chemin)
            label_dossier.config(fg="black")
        # Si annulé → on laisse le message par défaut (gris)

    tk.Button(
        cadre_dossier,
        text="📂  Parcourir…",
        font=("Arial", 10),
        command=choisir_dossier
    ).grid(row=2, column=0, sticky="w", pady=4)

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=10)

    # ── Boutons Annuler / Continuer ──────────────────────────────────────
    cadre_boutons = tk.Frame(fenetre)
    cadre_boutons.pack()

    def annuler():
        """Ferme tout et arrête SPRINGE proprement."""
        resultats["annule"] = True
        fenetre.destroy()

    def valider():
        """Récupère les valeurs et ferme la fenêtre."""
        resultats["DIR"]        = var_dir.get().strip() or "DIR"
        resultats["NOM"]        = var_nom.get().strip() or "utilisateur"

        # Gestion du dossier de sortie :
        # Si l'utilisateur a choisi un chemin valide → on l'utilise.
        # Sinon (valeur par défaut ou chemin inexistant) → fallback 02_outputs/.
        chemin_saisi = var_dossier.get()
        if (
            chemin_saisi == "(par défaut : dossier 02_outputs/ du programme)"
            or not Path(chemin_saisi).exists()
        ):
            # Fallback : dossier 02_outputs/ à côté du script lancer_SPRINGE
            resultats["OUTPUT_DIR"] = Path(__file__).parent / "02_outputs"
        else:
            resultats["OUTPUT_DIR"] = Path(chemin_saisi)

        fenetre.destroy()

    tk.Button(
        cadre_boutons,
        text="✖  Annuler",
        font=("Arial", 10),
        fg="gray",
        command=annuler,
        width=14
    ).grid(row=0, column=0, padx=10)

    tk.Button(
        cadre_boutons,
        text="Continuer  ▶",
        font=("Arial", 10, "bold"),
        bg="#1565c0",
        fg="white",
        relief="flat",
        command=valider,
        width=14
    ).grid(row=0, column=1, padx=10)

    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()
    return resultats
