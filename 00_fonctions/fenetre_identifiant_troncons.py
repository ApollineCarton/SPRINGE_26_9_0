# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre ÉTAPE 2/4 (suite) — IDENTIFIANT DES TRONÇONS
═══════════════════════════════════════════════════════════════════════════
Version 26.9.0 (septembre 2026)

Demande à l'utilisateur quelle variable (colonne) de son fichier « réseau
routier » identifie chaque point repère / tronçon.

CHANGEMENT STRUCTURANT DE LA VERSION 26.9.0
─────────────────────────────────────────────────────────────────
Avant : un champ texte libre pré-rempli avec 'nom_plo_fi'. L'utilisateur
devait connaître et taper le nom exact ; une faute de frappe ne se révélait
qu'au moment de la déduplication, après plusieurs minutes de chargement.

Maintenant : une LISTE DÉROULANTE des colonnes réellement présentes dans le
fichier, en lecture seule. Il est impossible de choisir une colonne qui
n'existe pas.

Conséquence sur l'ordre des fenêtres : pour connaître les colonnes, le
fichier réseau routier doit déjà être chargé. Cette fenêtre vient donc
APRÈS la fenêtre « Description de la zone d'étude » et après la lecture
du réseau par le script principal, qui lui transmet la liste des colonnes.

PRÉSÉLECTION
─────────────────────────────────────────────────────────────────
Si une colonne 'nom_plo_fi' existe (nom par défaut des couches SI ROUTE des
DIR), elle est présélectionnée. La comparaison ignore la casse : un export
shapefile peut l'avoir écrite 'NOM_PLO_FI'. L'utilisateur reste libre d'en
choisir une autre.

Ce choix diffère volontairement des fenêtres de mapping EEE, où rien n'est
présélectionné : ici le nom par défaut est une convention nationale connue
(SI ROUTE), pas une devinette sur la structure d'une couche quelconque.

CE QUE LA FENÊTRE NE FAIT PAS
─────────────────────────────────────────────────────────────────
Elle ne renomme rien. Le renommage interne de la colonne choisie en
'nom_plo_fi' (nécessaire car de nombreux modules de calcul utilisent ce nom
en dur) est fait par le script principal, juste après l'appel. Garder cette
fenêtre sans effet de bord la rend testable seule.

Retourne un dict : colonne_id (str ou None), annule (bool).

Appel depuis le script principal :
    _res_id = fenetre_identifiant_troncons.fenetre_identifiant_troncons(
        colonnes_disponibles = [liste des colonnes du réseau routier]
    )
═══════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk          # ttk.Combobox (liste déroulante) + Separator
from tkinter import messagebox   # avertissement si aucune colonne choisie


# Nom de colonne par défaut des couches SI ROUTE (DIR).
COLONNE_PAR_DEFAUT = "nom_plo_fi"


def _trouver_colonne_par_defaut(colonnes, nom_defaut):
    """
    Cherche nom_defaut parmi les colonnes, SANS tenir compte de la casse.

    Renvoie le nom EXACT tel qu'écrit dans le fichier (ex. 'NOM_PLO_FI'),
    ou None si absent. On renvoie la graphie du fichier et non nom_defaut,
    sinon la présélection afficherait un nom qui n'existe pas dans la liste.
    """
    for colonne in colonnes:
        if str(colonne).lower() == nom_defaut.lower():
            return colonne
    return None


def fenetre_identifiant_troncons(colonnes_disponibles,
                                 colonne_par_defaut=COLONNE_PAR_DEFAUT):
    """
    Étape 2/4 (suite) — Choix de la colonne identifiant des tronçons.

    Paramètres
    ----------
    colonnes_disponibles : list[str]
        Colonnes du fichier réseau routier, géométrie exclue (le script
        principal s'en charge : la géométrie ne peut pas être un identifiant).
    colonne_par_defaut : str
        Nom à présélectionner s'il existe (défaut : 'nom_plo_fi').

    Retour
    ------
    dict : {"colonne_id": str ou None, "annule": bool}
    """

    resultats = {"colonne_id": None, "annule": False}

    # Conversion en str : un nom de colonne peut, rarement, être un entier
    # (fichier mal exporté). La Combobox et les comparaisons attendent du texte.
    colonnes = [str(c) for c in colonnes_disponibles]

    root = tk.Tk()
    root.withdraw()

    # ── Garde-fou : fichier sans aucune colonne attributaire ────────────
    # Cas très improbable, mais une Combobox vide bloquerait l'utilisateur
    # sans explication. On l'informe et on annule proprement.
    if not colonnes:
        messagebox.showerror(
            "Aucune variable trouvée",
            "Le fichier réseau routier ne contient aucune variable attributaire.\n"
            "SPRINGE ne peut pas identifier les tronçons et va s'arrêter.",
            parent=root
        )
        root.destroy()
        resultats["annule"] = True
        return resultats

    fenetre = tk.Toplevel(root)
    fenetre.title("SPRINGE — Étape 2/4 · Identifiant des tronçons")
    fenetre.resizable(False, False)

    # ── En-tête ──────────────────────────────────────────────────────────
    tk.Label(
        fenetre,
        text="Étape 2 / 4 — Description de la zone d'étude (suite)",
        font=("Arial", 13, "bold"),
        pady=10
    ).pack(padx=20)

    # Sous-titre : rappelle l'objet précis de cet écran.
    tk.Label(
        fenetre,
        text="Identifiant des tronçons",
        font=("Arial", 11, "bold")
    ).pack()

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=8)

    # ── Explication ──────────────────────────────────────────────────────
    # Trois paragraphes distincts plutôt qu'un seul bloc avec des "\n" :
    # chacun a son rôle (principe / aide DIR / consigne) et wraplength gère
    # les retours à la ligne proprement.
    tk.Label(
        fenetre,
        text=(
            "SPRINGE procède à l'identification des points repères / tronçons "
            "routiers grâce à une variable « identifiant » de votre fichier SIG "
            "« réseau routier » fourni ci-avant."
        ),
        font=("Arial", 10),
        justify="center",
        wraplength=480
    ).pack(padx=20, pady=(2, 6))

    tk.Label(
        fenetre,
        text=(
            f"Aide : pour les DIR, le nom de variable par défaut à rechercher "
            f"est  {colonne_par_defaut}"
        ),
        font=("Arial", 9, "italic"),
        fg="gray30",
        justify="center",
        wraplength=480
    ).pack(padx=20, pady=(0, 6))

    tk.Label(
        fenetre,
        text=(
            "Merci de rechercher dans la liste déroulante la variable "
            "« identifiant » de votre fichier."
        ),
        font=("Arial", 10),
        justify="center",
        wraplength=480
    ).pack(padx=20, pady=(0, 8))

    # ── Liste déroulante ─────────────────────────────────────────────────
    cadre = tk.Frame(fenetre)
    cadre.pack(pady=5)

    tk.Label(
        cadre,
        text="Variable identifiant :",
        font=("Arial", 10)
    ).grid(row=0, column=0, padx=10)

    # Présélection : graphie exacte de 'nom_plo_fi' dans le fichier, ou ""
    # (liste vide à l'ouverture, l'utilisateur doit alors choisir).
    preselection = _trouver_colonne_par_defaut(colonnes, colonne_par_defaut) or ""
    var_colonne = tk.StringVar(value=preselection)

    # state="readonly" : l'utilisateur ne peut que CHOISIR dans la liste, pas
    # taper. C'est ce qui supprime le risque de faute de frappe.
    # height : nombre de lignes visibles quand la liste est dépliée (au-delà,
    # une barre de défilement apparaît automatiquement).
    combo = ttk.Combobox(
        cadre,
        textvariable=var_colonne,
        values=colonnes,
        state="readonly",
        width=30,
        height=15,
        font=("Arial", 10)
    )
    combo.grid(row=0, column=1, padx=10)

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=10)

    # ── Boutons ──────────────────────────────────────────────────────────
    cadre_boutons = tk.Frame(fenetre)
    cadre_boutons.pack(pady=(0, 12))

    def annuler():
        """Signale l'annulation : le script principal s'arrêtera proprement."""
        resultats["annule"] = True
        fenetre.destroy()

    def valider():
        """Vérifie qu'une variable est choisie, puis ferme la fenêtre."""
        valeur = var_colonne.get()
        if not valeur:
            # On bloque la fermeture : mieux vaut un choix explicite qu'un
            # identifiant vide qui ferait planter la déduplication plus loin.
            messagebox.showwarning(
                "Sélection requise",
                "Veuillez choisir la variable identifiant dans la liste déroulante.",
                parent=fenetre
            )
            return
        resultats["colonne_id"] = valeur
        fenetre.destroy()

    tk.Button(
        cadre_boutons, text="✖  Annuler", font=("Arial", 10), fg="gray",
        command=annuler, width=14
    ).grid(row=0, column=0, padx=10)

    tk.Button(
        cadre_boutons, text="Continuer  ▶", font=("Arial", 10, "bold"),
        bg="#1565c0", fg="white", relief="flat", command=valider, width=14
    ).grid(row=0, column=1, padx=10)

    # Croix de fermeture = Annuler (sinon colonne_id=None et annule=False).
    fenetre.protocol("WM_DELETE_WINDOW", annuler)

    # ── Dimensionnement et centrage ──────────────────────────────────────
    # Hauteur calculée d'après le contenu réel (voir fenetre_zone_travail).
    fenetre.update_idletasks()
    largeur, hauteur = 540, fenetre.winfo_reqheight() + 10
    x = (fenetre.winfo_screenwidth() // 2) - (largeur // 2)
    y = (fenetre.winfo_screenheight() // 2) - (hauteur // 2)
    fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()
    return resultats


# Démonstration locale avec des colonnes fictives.
if __name__ == "__main__":
    print(fenetre_identifiant_troncons(
        ["id_objet", "route", "NOM_PLO_FI", "dist_deb", "dist_fin"]
    ))
