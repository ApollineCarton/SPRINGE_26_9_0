# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre ÉTAPE 2/4 — DESCRIPTION DE LA ZONE D'ÉTUDE ET FICHIERS SIG
═══════════════════════════════════════════════════════════════════════════
Version 26.9.0 (septembre 2026)

Demande le mode de définition de la zone d'étude (Option A ou B), puis
les fichiers SIG correspondants.

  Option A : l'utilisateur possède un fichier délimitant la zone d'étude,
             DISTINCT du fichier contenant ses points repères / tronçons
             → il fournit ce fichier de zone (polygone ou multipolygones)
               + son réseau routier.
  Option B : le réseau routier définit lui-même la zone d'étude
             → il ne fournit que son réseau routier.

IMPORTANT : cette fenêtre ne fait que RÉFÉRENCER les fichiers (chemins).
Le chargement effectif (gpd.read_file) est fait par le script principal,
juste après cette fenêtre : depuis la version 26.9.0, le réseau routier
est lu AVANT la fenêtre « Identifiant des tronçons », qui a besoin de la
liste de ses colonnes pour sa liste déroulante.

Historique :
  - 26.9.0 : passe de l'étape 3/4 à l'étape 2/4 (réorganisation des
             fenêtres) ; « zone de travail » devient « zone d'étude » ;
             textes des options A / B réécrits.

Retourne un dict : choix, fichier_emprise, fichier_troncons, annule.
  - choix : "yes" pour l'Option A, "no" pour l'Option B. Ces valeurs
            historiques sont conservées telles quelles : le script
            principal et le rapport d'exécution les testent déjà.

Le nom du fichier (fenetre_zone_travail.py) est volontairement conservé :
le renommer obligerait à modifier l'appel dans le script principal sans
aucun bénéfice pour l'utilisateur, qui ne voit jamais ce nom.

Appel depuis le script principal :
    _res_zone = fenetre_zone_travail.fenetre_zone_travail()
═══════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk          # ttk.Separator : ligne horizontale de séparation
from tkinter import filedialog   # explorateur de fichiers (askopenfilename)
from tkinter import messagebox   # boîtes d'avertissement « fichier manquant »


# Types de fichiers proposés dans l'explorateur. Défini une seule fois ici
# pour que les trois appels à askopenfilename restent strictement cohérents.
TYPES_FICHIERS_SIG = [("Fichiers SIG", "*.shp *.gpkg")]


def _centrer_fenetre(fenetre, largeur=600):
    """
    Dimensionne la fenêtre sur la hauteur RÉELLEMENT nécessaire à son
    contenu, puis la centre à l'écran.

    Pourquoi une hauteur calculée plutôt que fixe : les nouveaux textes des
    options A / B sont plus longs qu'avant. Une hauteur figée (l'ancien
    "560x340") couperait le bas de la fenêtre, donc les boutons.

    update_idletasks() force Tkinter à calculer la mise en page SANS
    afficher la fenêtre ; winfo_reqheight() renvoie alors la hauteur
    demandée par l'ensemble des widgets.
    """
    fenetre.update_idletasks()
    hauteur = fenetre.winfo_reqheight() + 20          # +20 px de marge basse
    x = (fenetre.winfo_screenwidth() // 2) - (largeur // 2)
    y = (fenetre.winfo_screenheight() // 2) - (hauteur // 2)
    fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")


def _demander_fichier(root, titre_dialogue, message_si_absent, resultats):
    """
    Ouvre l'explorateur de fichiers et renvoie le chemin choisi.

    Si l'utilisateur ferme l'explorateur sans rien choisir, on l'avertit,
    on marque l'annulation dans `resultats` et on renvoie None : l'appelant
    n'a plus qu'à sortir.

    Cette fonction factorise un bloc qui était auparavant copié trois fois
    (fichier de zone en Option A, réseau en Option A, réseau en Option B).
    """
    chemin = filedialog.askopenfilename(
        parent=root,                  # rattache l'explorateur à notre racine Tk
        title=titre_dialogue,
        filetypes=TYPES_FICHIERS_SIG
    )
    if not chemin:
        # askopenfilename renvoie une chaîne vide si l'utilisateur annule.
        messagebox.showwarning(
            "Fichier manquant",
            f"{message_si_absent}\nSPRINGE va s'arrêter.",
            parent=root
        )
        resultats["annule"] = True
        return None
    return chemin


def fenetre_zone_travail():
    """
    Étape 2/4 — Choix du mode de définition de la zone d'étude, puis
    sélection des fichiers SIG correspondants.

    Retourne un dict : choix, fichier_emprise, fichier_troncons, annule.
    """

    # Dictionnaire de retour, pré-rempli. fichier_emprise reste à None en
    # Option B : c'est ce None que le script principal teste ensuite.
    resultats = {
        "choix"           : None,
        "fichier_emprise" : None,
        "fichier_troncons": None,
        "annule"          : False
    }

    # Racine Tk cachée : Tkinter exige une fenêtre racine, mais seule la
    # Toplevel ci-dessous doit être visible (même patron que les autres
    # fenêtres de SPRINGE).
    root = tk.Tk()
    root.withdraw()

    # ── Fenêtre de choix du mode ─────────────────────────────────────────
    fenetre_mode = tk.Toplevel(root)
    fenetre_mode.title("SPRINGE — Étape 2/4 · Description de la zone d'étude")
    fenetre_mode.resizable(False, False)

    # Titre de l'étape
    tk.Label(
        fenetre_mode,
        text="Étape 2 / 4 — Description de la zone d'étude",
        font=("Arial", 13, "bold"),
        pady=10
    ).pack()

    ttk.Separator(fenetre_mode, orient='horizontal').pack(fill='x', padx=20, pady=5)

    # Consigne générale. wraplength (en pixels) laisse Tkinter couper les
    # lignes lui-même : pas de "\n" manuels au milieu des phrases.
    tk.Label(
        fenetre_mode,
        text=(
            "Définissez votre zone d'étude.\n"
            "(ex : votre CEI, votre commune, votre département…)"
        ),
        font=("Arial", 10),
        justify="center",
        wraplength=540
    ).pack(pady=6)

    ttk.Separator(fenetre_mode, orient='horizontal').pack(fill='x', padx=20, pady=5)

    # ── Description de l'Option A ────────────────────────────────────────
    # Deux labels séparés (situation / ce qu'il faut fournir) plutôt qu'un
    # seul bloc indenté à coups d'espaces : l'alignement ne dépend plus de la
    # largeur des caractères de la police.
    tk.Label(
        fenetre_mode,
        text=(
            "●  Option A  —  Vous avez un fichier délimitant la zone d'étude, "
            "distinct du fichier contenant vos points repères / tronçons routiers."
        ),
        font=("Arial", 10, "bold"),
        wraplength=530,
        justify="left",
        anchor="w"
    ).pack(padx=30, anchor="w", pady=(6, 0))

    tk.Label(
        fenetre_mode,
        text=(
            "→ Vous devez fournir ce fichier (format polygone ou multipolygones) "
            "+ votre réseau routier (contenant les points repères / tronçons)."
        ),
        font=("Arial", 10),
        wraplength=510,
        justify="left",
        anchor="w"
    ).pack(padx=(50, 30), anchor="w", pady=(2, 8))

    # ── Description de l'Option B ────────────────────────────────────────
    tk.Label(
        fenetre_mode,
        text=(
            "●  Option B  —  Votre réseau routier (contenant les points repères / "
            "tronçons) définit lui-même la zone d'étude."
        ),
        font=("Arial", 10, "bold"),
        wraplength=530,
        justify="left",
        anchor="w"
    ).pack(padx=30, anchor="w", pady=(6, 0))

    tk.Label(
        fenetre_mode,
        text="→ Vous devez fournir uniquement ce fichier.",
        font=("Arial", 10),
        wraplength=510,
        justify="left",
        anchor="w"
    ).pack(padx=(50, 30), anchor="w", pady=(2, 8))

    ttk.Separator(fenetre_mode, orient='horizontal').pack(fill='x', padx=20, pady=8)

    # ── Boutons Annuler / Option A / Option B ────────────────────────────
    cadre_mode = tk.Frame(fenetre_mode)
    cadre_mode.pack(pady=(0, 10))

    def choisir(val):
        """Mémorise le mode choisi ("yes" = A, "no" = B) et ferme la fenêtre."""
        resultats["choix"] = val
        fenetre_mode.destroy()

    def annuler_mode():
        """Signale l'annulation : le script principal s'arrêtera proprement."""
        resultats["annule"] = True
        fenetre_mode.destroy()

    tk.Button(
        cadre_mode, text="✖  Annuler", font=("Arial", 10), fg="gray",
        command=annuler_mode, width=14
    ).grid(row=0, column=0, padx=8)

    # lambda : on doit passer un ARGUMENT à choisir() ; command= attend une
    # fonction sans argument, d'où l'emballage dans une lambda.
    tk.Button(
        cadre_mode, text="Option A  →", font=("Arial", 10, "bold"),
        bg="#1565c0", fg="white", relief="flat",
        command=lambda: choisir("yes"), width=16
    ).grid(row=0, column=1, padx=8)

    tk.Button(
        cadre_mode, text="Option B  →", font=("Arial", 10, "bold"),
        bg="#1565c0", fg="white", relief="flat",
        command=lambda: choisir("no"), width=16
    ).grid(row=0, column=2, padx=8)

    # La croix de fermeture vaut « Annuler ». Sans cette ligne, fermer la
    # fenêtre par la croix laissait choix=None et annule=False : le script
    # principal aurait poursuivi avec un mode indéfini.
    fenetre_mode.protocol("WM_DELETE_WINDOW", annuler_mode)

    # Dimensionnement une fois TOUS les widgets créés (sinon la hauteur
    # calculée ne tiendrait pas compte des boutons).
    _centrer_fenetre(fenetre_mode)

    # grab_set : fenêtre modale ; wait_window : le script attend sa fermeture.
    fenetre_mode.grab_set()
    root.wait_window(fenetre_mode)

    # Annulation au choix du mode → sortie immédiate.
    if resultats["annule"]:
        root.destroy()
        return resultats

    # ── Sélection des fichiers selon le mode choisi ──────────────────────
    if resultats["choix"] == "yes":
        # Option A : d'abord le fichier de zone d'emprise…
        fichier_emprise = _demander_fichier(
            root,
            "Option A — Sélectionnez votre fichier de zone d'étude "
            "(polygone ou multipolygones, .shp ou .gpkg)",
            "Aucun fichier de zone d'étude sélectionné.",
            resultats
        )
        if fichier_emprise is None:
            root.destroy()
            return resultats
        resultats["fichier_emprise"] = fichier_emprise

        # … puis le réseau routier.
        fichier_troncons = _demander_fichier(
            root,
            "Option A — Sélectionnez votre fichier de réseau routier "
            "(points repères / tronçons, .shp ou .gpkg)",
            "Aucun fichier de réseau routier sélectionné.",
            resultats
        )
        if fichier_troncons is None:
            root.destroy()
            return resultats
        resultats["fichier_troncons"] = fichier_troncons

    else:
        # Option B : le réseau routier seul.
        fichier_troncons = _demander_fichier(
            root,
            "Option B — Sélectionnez votre fichier de réseau routier "
            "(points repères / tronçons, .shp ou .gpkg)",
            "Aucun fichier de réseau routier sélectionné.",
            resultats
        )
        if fichier_troncons is None:
            root.destroy()
            return resultats
        resultats["fichier_troncons"] = fichier_troncons

    root.destroy()
    return resultats


# Démonstration locale : ne s'exécute qu'en lançant ce fichier directement.
if __name__ == "__main__":
    print(fenetre_zone_travail())
