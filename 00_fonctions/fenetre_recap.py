# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre — RÉCAPITULATIF AVANT DÉMARRAGE
═══════════════════════════════════════════════════════════════════════════
Version 26.9.0 (septembre 2026)

Dernière vérification avant le calcul long. Affiche un résumé de tout ce
que l'utilisateur a renseigné pendant les 4 étapes.

Retourne True si l'utilisateur lance le traitement, False sinon.

CHANGEMENTS DE LA VERSION 26.9.0
─────────────────────────────────────────────────────────────────
  - Titre : « Récapitulatif avant démarrage ».
  - « Zone de travail » devient « Zone d'étude » ; libellés « Fichier zone
    d'emprise » et « Fichier réseau routier ».
  - Ligne « Données TMJA » supprimée (le paramètre fichier_tmja disparaît).
  - AJOUT des informations issues de l'étape 4 : espèces EEE traitées,
    conformité déclarée au protocole de recensement, caractérisation des
    populations prévue ou non.
    Ces informations sont désormais connues AVANT le récapitulatif, puisque
    les fenêtres de mapping EEE ont été avancées dans le parcours.
  - Nouveaux textes d'avertissement (rouge : vérification ; noir : durée).

POURQUOI « CONFORMITÉ » ET « CARACTÉRISATION PRÉVUE » SONT DEUX LIGNES
─────────────────────────────────────────────────────────────────
Elles peuvent différer : un gestionnaire peut déclarer ses données conformes
au protocole, puis abandonner le paramétrage (fenêtre des colonnes fermée,
ou refus de poursuivre après l'alerte « modalités inattendues »). Afficher
les deux permet de comprendre POURQUOI la caractérisation n'aura pas lieu.

Ce module ne calcule rien : le script principal lui passe des valeurs déjà
mises en forme (libellés d'espèces, booléens). Une fenêtre = un affichage.

Appel depuis le script principal :
    _lancer = fenetre_recap.fenetre_recap(DIR=..., NOM=..., ...)
═══════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk          # ttk.Separator
from pathlib import Path         # Path(...).name : nom du fichier sans son dossier


def _oui_non(valeur):
    """
    Traduit un booléen en texte lisible pour l'utilisateur.

    None est traité à part : il signifie « question restée sans réponse »
    (fenêtre de conformité fermée par la croix), ce qui n'est ni oui ni non.
    """
    if valeur is True:
        return "oui"
    if valeur is False:
        return "non"
    return "non renseigné"


def fenetre_recap(DIR, NOM, OUTPUT_DIR, colonne_id, choix,
                  fichier_troncons, fichier_emprise,
                  especes_retenues=None,
                  conforme_protocole=None,
                  caracterisation_prevue=False):
    """
    Récapitulatif complet avant démarrage.

    Paramètres
    ----------
    DIR, NOM : str
        Structure et opérateur (étape 1).
    OUTPUT_DIR : Path ou str
        Dossier de sortie des résultats (étape 1).
    colonne_id : str
        Variable identifiant des tronçons TELLE QUE CHOISIE par l'utilisateur
        (nom d'origine, avant le renommage interne en 'nom_plo_fi').
    choix : str
        "yes" = Option A, "no" = Option B (étape 2).
    fichier_troncons, fichier_emprise : str ou None
        Chemins des fichiers SIG (étape 2). fichier_emprise vaut None en Option B.
    especes_retenues : list[str] ou None
        Libellés LISIBLES des espèces cochées (étape 4), ex.
        ["Renouées asiatiques (Reynoutria sp.)", "Ailante (Ailanthus altissima)"].
    conforme_protocole : bool ou None
        Réponse à « vos données suivent-elles le protocole ? » (étape 4).
    caracterisation_prevue : bool
        True si la caractérisation des populations sera calculée.

    Retour
    ------
    bool : True si l'utilisateur clique « Lancer SPRINGE », False sinon.
    """

    # Boîte aux lettres : une fonction imbriquée ne peut pas réassigner une
    # variable de la fonction englobante avec « = », mais elle peut modifier
    # le contenu d'un dict.
    confirme = {"valeur": False}

    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    fenetre.title("SPRINGE — Récapitulatif avant démarrage")
    fenetre.resizable(False, False)

    # ── En-tête ──────────────────────────────────────────────────────────
    tk.Label(
        fenetre,
        text="Récapitulatif avant démarrage",
        font=("Arial", 13, "bold"),
        pady=10
    ).pack()

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=5)

    # ── Tableau récapitulatif ────────────────────────────────────────────
    # Grille à deux colonnes : libellé (gras, aligné à droite) / valeur.
    cadre_recap = tk.Frame(fenetre, padx=20)
    cadre_recap.pack(fill='x', pady=5)

    # Compteur de ligne mutable, pour ne plus numéroter les lignes à la main
    # (avant : row=0, 1, 2… écrits en dur, avec des trous quand une ligne
    # était conditionnelle). Chaque appel à ligne() ou separateur() l'avance.
    position = {"row": 0}

    def ligne(label, valeur, couleur_valeur="black"):
        """Ajoute une ligne « libellé : valeur » à la grille."""
        r = position["row"]
        tk.Label(
            cadre_recap,
            text=label,
            font=("Arial", 10, "bold"),
            anchor="e",
            justify="right",
            width=34          # largeur en caractères, pour les libellés longs
        ).grid(row=r, column=0, sticky="ne", pady=2)
        tk.Label(
            cadre_recap,
            text=valeur,
            font=("Arial", 10),
            fg=couleur_valeur,
            anchor="w",
            justify="left",   # alignement des lignes quand la valeur est coupée
            wraplength=320
        ).grid(row=r, column=1, sticky="w", padx=10, pady=2)
        position["row"] += 1

    def separateur():
        """Ajoute un trait horizontal sur toute la largeur de la grille."""
        ttk.Separator(cadre_recap, orient='horizontal').grid(
            row=position["row"], column=0, columnspan=2, sticky="ew", pady=6
        )
        position["row"] += 1

    # -- Bloc 1 : identification (étape 1) --
    ligne("Structure :",                       DIR)
    ligne("Opérateur :",                       NOM)
    ligne("Dossier de sortie des résultats :", str(OUTPUT_DIR))

    separateur()

    # -- Bloc 2 : zone d'étude et réseau routier (étape 2) --
    mode_label = (
        "Option A (fichier zone d'emprise + réseau routier)"
        if choix == "yes"
        else "Option B (réseau routier = zone d'étude)"
    )
    ligne("Zone d'étude :",  mode_label)

    # La ligne n'apparaît qu'en Option A : en Option B, il n'y a pas de
    # fichier d'emprise distinct à afficher.
    if fichier_emprise:
        ligne("Fichier zone d'emprise :", Path(fichier_emprise).name)

    ligne("Fichier réseau routier :", Path(fichier_troncons).name)
    ligne("Identifiant tronçons :",   colonne_id)

    separateur()

    # -- Bloc 3 : compréhension des données d'entrée (étape 4) --
    # Une espèce par ligne ("\n".join) : plus lisible qu'une énumération
    # coupée n'importe où par wraplength.
    if especes_retenues:
        texte_especes = "\n".join(especes_retenues)
    else:
        texte_especes = "aucune"
    ligne("Espèces EEE traitées :", texte_especes)

    ligne("Données d'occurrence conformes au\nprotocole de recensement (Albert 2017) :",
          _oui_non(conforme_protocole))

    # En gris si « non » : l'information est normale, pas une erreur, mais
    # elle doit se distinguer d'un « oui ».
    ligne("Caractérisation des populations\nEEE prévue :",
          _oui_non(caracterisation_prevue),
          couleur_valeur="black" if caracterisation_prevue else "gray40")

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=8)

    # ── Consigne de vérification (rouge) ─────────────────────────────────
    tk.Label(
        fenetre,
        text=(
            "Merci de vérifier la véracité des informations récapitulées "
            "ci-dessus, puis de cliquer sur le bouton vert « Lancer SPRINGE »."
        ),
        font=("Arial", 10, "bold"),
        fg="#b71c1c",
        wraplength=540,
        justify="center"
    ).pack(padx=20, pady=(2, 6))

    # ── Information sur le déroulement (noir) ────────────────────────────
    tk.Label(
        fenetre,
        text=(
            "Une fois les calculs en cours, le traitement s'exécute sans "
            "interruption, avec l'apparition de fenêtres de suivi. La durée de "
            "traitement est variable selon la dimension de la zone d'étude, la "
            "qualité de la connexion internet et la rapidité de l'ordinateur utilisé."
        ),
        font=("Arial", 9),
        fg="black",
        wraplength=540,
        justify="center"
    ).pack(padx=20, pady=(0, 4))

    ttk.Separator(fenetre, orient='horizontal').pack(fill='x', padx=20, pady=6)

    # ── Boutons ──────────────────────────────────────────────────────────
    cadre_boutons = tk.Frame(fenetre)
    cadre_boutons.pack(pady=(4, 14))

    def annuler():
        confirme["valeur"] = False
        fenetre.destroy()

    def lancer():
        confirme["valeur"] = True
        fenetre.destroy()

    tk.Button(
        cadre_boutons, text="✖  Annuler SPRINGE", font=("Arial", 10), fg="gray",
        command=annuler, width=18
    ).grid(row=0, column=0, padx=12)

    tk.Button(
        cadre_boutons, text="▶   Lancer SPRINGE", font=("Arial", 11, "bold"),
        bg="#2e7d32", fg="white", relief="flat",
        command=lancer, width=18
    ).grid(row=0, column=1, padx=12)

    # Croix de fermeture = Annuler (comportement explicite, identique au défaut).
    fenetre.protocol("WM_DELETE_WINDOW", annuler)

    # ── Dimensionnement et centrage ──────────────────────────────────────
    # Hauteur calculée d'après le contenu : le nombre de lignes varie selon
    # l'Option A/B et le nombre d'espèces cochées, une taille fixe (l'ancien
    # "540x480") aurait coupé les boutons.
    fenetre.update_idletasks()
    largeur = max(620, fenetre.winfo_reqwidth() + 20)
    hauteur = fenetre.winfo_reqheight() + 10
    x = (fenetre.winfo_screenwidth() // 2) - (largeur // 2)
    y = max(0, (fenetre.winfo_screenheight() // 2) - (hauteur // 2))
    fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()
    return confirme["valeur"]


# Démonstration locale avec des valeurs fictives.
if __name__ == "__main__":
    print(fenetre_recap(
        DIR="DIRCO", NOM="utilisateur", OUTPUT_DIR="C:/SPRINGE/02_outputs",
        colonne_id="nom_plo_fi", choix="yes",
        fichier_troncons="C:/data/Troncons_DIR.shp",
        fichier_emprise="C:/data/zone.gpkg",
        especes_retenues=["Renouées asiatiques (Reynoutria sp.)",
                          "Ailante (Ailanthus altissima)"],
        conforme_protocole=True, caracterisation_prevue=True,
    ))
