# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fenêtre ÉTAPE 3/4 — "Renseignement des données SIG d'entrée"
Date : 2026-07-09 — Version 26.9.0 (septembre 2026)
(anciennement « Données de calcul des indicateurs » : seuls le titre de
 la barre de fenêtre et le titre interne ont changé en 26.9.0)
═══════════════════════════════════════════════════════════════════════════

Objectif : recueillir les chemins d'accès aux couches SIG nécessaires au
calcul des indicateurs SPRINGE. Remplace le chargement en bloc depuis
01_data/ par une saisie explicite par l'utilisateur, ce qui rend l'outil
distribuable sans embarquer les couches.

Deux modes d'affichage pilotés par « Êtes-vous gestionnaire d'une DIR ? » :
  • DIR  → liste nominative des couches SI ROUTE (noms officiels Isidor3)
  • non-DIR → blocs thématiques regroupés + bouton « Ajouter une couche »

Chaque couche est vérifiée au clic Parcourir par un gpd.read_file(rows=1)
(prouve la lisibilité, pas juste l'existence). Si ça échoue → message ami.

RETOURNE un dict :
    {
      "annule"      : bool,
      "est_dir"     : bool,
      "couches"     : { var_name: filepath_or_None, ... },
      "supplementaires_MS2" : [filepath, ...],   # couches ajoutées (MS2)
      "supplementaires_MS3" : [filepath, ...],   # couches ajoutées (MS3)
      "supplementaires_MS1" : [filepath, ...],   # couches ajoutées (MS1)
    }
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────
# Essai d'import geopandas pour la vérification de lisibilité.
# S'il n'est pas dispo (cas rare), on se rabat sur pathlib.exists().
# ─────────────────────────────────────────────────────────────────────────
try:
    import geopandas as _gpd
    _VERIF_LECTURE = True
except ImportError:
    _VERIF_LECTURE = False


# ═════════════════════════════════════════════════════════════════════════
# REGISTRE DES COUCHES — toutes les métadonnées au même endroit.
# ═════════════════════════════════════════════════════════════════════════
# Chaque entrée :
#   var          : nom de la variable Python (clé de retour dans le dict)
#   label_dir    : texte affiché en mode DIR
#   label_nondir : texte affiché en mode non-DIR (None → couche non demandée
#                  individuellement en mode non-DIR, couverte par le bloc groupé)
#   info_dir     : détail SI ROUTE (nom, domaine, page catalogue)
#   info_nondir  : détail pour non-DIR
#   bloc         : thème métier (pour le regroupement)
#   obligatoire  : True → bloque le Continuer si absent
# ─────────────────────────────────────────────────────────────────────────

# -- OBLIGATOIRE --------------------------------------------------------
COUCHE_EEE = {
    "var": "gdf_EEE",
    "label_dir":    "Points de présence EEE",
    "label_nondir": "Points de présence EEE",
    "info_dir": (
        "Domaine Environnement · Nom « PEE » · Libellé « Plantes exotiques "
        "envahissantes » · Type ponctuelle\n"
        "Voir page 118 du Catalogue Isidor3_2023-03-06.odt (dossier 02_docs)"
    ),
    "info_nondir": (
        "Couche de points de présence d'espèces exotiques envahissantes (EEE) "
        "sur votre réseau. Type ponctuelle. Formats acceptés : .shp, .gpkg"
    ),
    "bloc": "obligatoire",
    "obligatoire": True,
}

# -- VISIBILITÉ / SÉCURITÉ ROUTIÈRE (MS1, P2) --------------------------
COUCHES_MS1 = [
    {
        "var": "gdf_carrefours",
        "label_dir":    "Carrefours (RRNnc)",
        "label_nondir": None,  # couvert par le bloc groupé
        "info_dir": (
            "Domaine Aménagement · Nom « Carrefour » · Libellé « Carrefours (RRNnc) » "
            "· Type ponctuelle\n"
            "Voir page 43 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour les indicateurs MS1 (visibilité) et P2 (propagation)"
        ),
        "info_nondir": "",
        "bloc": "MS1",
        "obligatoire": False,
    },
    {
        "var": "gdf_echangeurs",
        "label_dir":    "Échangeurs (RRNc)",
        "label_nondir": None,
        "info_dir": (
            "Domaine Aménagement · Nom « Echangeurs » · Libellé « Échangeurs (RRNc) » "
            "· Type ponctuelle\n"
            "Voir page 45 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour les indicateurs MS1 (visibilité) et P2 (propagation)"
        ),
        "info_nondir": "",
        "bloc": "MS1",
        "obligatoire": False,
    },
    {
        "var": "gdf_pn",
        "label_dir":    "Passages à niveau",
        "label_nondir": None,
        "info_dir": (
            "Domaine Aménagement · Nom « PN » · Libellé « Passages à niveau » "
            "· Type ponctuelle\n"
            "Voir page 48 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour l'indicateur MS1 (visibilité)"
        ),
        "info_nondir": "",
        "bloc": "MS1",
        "obligatoire": False,
    },
]

# -- PATRIMOINE ROUTIER / OUVRAGES D'ART (MS3) -------------------------
COUCHES_MS3 = [
    {
        "var": "gdf_ecransAcoustiques",
        "label_dir":    "Écrans acoustiques",
        "label_nondir": None,
        "info_dir": (
            "Domaine Ouvrages d'art · Nom « EcransAcoustiques » · Type linéaire\n"
            "Voir page 66 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour l'indicateur MS3 (patrimoine routier)"
        ),
        "info_nondir": "",
        "bloc": "MS3",
        "obligatoire": False,
    },
    {
        "var": "gdf_mursConsedes",
        "label_dir":    "Murs concédés (RRNc)",
        "label_nondir": None,
        "info_dir": (
            "Domaine Ouvrages d'art · Nom « MursConcedes » · Libellé « Murs (RRNc) » "
            "· Type linéaire\n"
            "Voir page 71 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour l'indicateur MS3 (patrimoine routier)"
        ),
        "info_nondir": "",
        "bloc": "MS3",
        "obligatoire": False,
    },
    {
        "var": "gdf_murs",
        "label_dir":    "Murs (RRNnc)",
        "label_nondir": None,
        "info_dir": (
            "Domaine Ouvrages d'art · Nom « Murs » · Libellé « Murs (RRNnc) » "
            "· Type linéaire\n"
            "Voir page 68 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour l'indicateur MS3 (patrimoine routier)"
        ),
        "info_nondir": "",
        "bloc": "MS3",
        "obligatoire": False,
    },
    {
        "var": "gdf_pontsConsedes",
        "label_dir":    "Ponts concédés (RRNc)",
        "label_nondir": None,
        "info_dir": (
            "Domaine Ouvrages d'art · Nom « PontsConcedes » · Libellé « Ponts (RRNc) » "
            "· Type linéaire\n"
            "Voir page 77 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour l'indicateur MS3 (patrimoine routier)"
        ),
        "info_nondir": "",
        "bloc": "MS3",
        "obligatoire": False,
    },
    {
        "var": "gdf_ponts",
        "label_dir":    "Ponts (RRNnc)",
        "label_nondir": None,
        "info_dir": (
            "Domaine Ouvrages d'art · Nom « Ponts » · Libellé « Ponts (RRNnc) » "
            "· Type linéaire\n"
            "Voir page 73 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour l'indicateur MS3 (patrimoine routier)"
        ),
        "info_nondir": "",
        "bloc": "MS3",
        "obligatoire": False,
    },
    {
        # Passages à faune — demandé en fichier EN ATTENDANT l'intégration
        # de l'API passagesfaune.fr (TODO API).
        "var": "gdf_paf",
        "label_dir":    "Passages à faune",
        "label_nondir": None,
        "info_dir": (
            "Source Geonature / dossiers internes · Type ponctuelle\n"
            "Pas dans le SI ROUTE. TODO : intégration API passagesfaune.fr\n"
            "Utilisée pour l'indicateur MS3 (patrimoine routier)"
        ),
        "info_nondir": "",
        "bloc": "MS3",
        "obligatoire": False,
    },
]

# -- ZONES FRÉQUENTÉES / RISQUE SANITAIRE (MS2) ------------------------
COUCHES_MS2 = [
    {
        "var": "gdf_airesderepos",
        "label_dir":    "Aires de repos ou de services",
        "label_nondir": None,
        "info_dir": (
            "Domaine Aménagement · Nom « Aires » · Libellé « Aires de repos "
            "ou de services » · Type ponctuelle\n"
            "Voir page 40 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour l'indicateur MS2 (risque sanitaire)"
        ),
        "info_nondir": "",
        "bloc": "MS2",
        "obligatoire": False,
    },
]

# -- TRAFIC (MS1b, P2) --------------------------------------------------
COUCHES_TRAFIC = [
    {
        "var": "gdf_tmja",
        "label_dir":    "Trafic routier (TMJA)",
        "label_nondir": "Données de trafic routier",
        "info_dir": (
            "Domaine Gestion du trafic · Nom « TraficRoutier » · Libellé "
            "« Trafic » · Type ponctuelle\n"
            "Voir page 111 du Catalogue Isidor3 (02_docs)\n"
            "Utilisée pour les indicateurs MS1b (exposition trafic) et P2 (propagation)"
        ),
        "info_nondir": (
            "Couche de points renseignant le trafic moyen journalier annuel (TMJA) "
            "sur votre réseau. Type ponctuelle. Formats acceptés : .shp, .gpkg"
        ),
        "bloc": "trafic",
        "obligatoire": False,
    },
]


# ═════════════════════════════════════════════════════════════════════════
# TEXTES DES BLOCS THÉMATIQUES (mode non-DIR)
# ═════════════════════════════════════════════════════════════════════════
BLOCS_NONDIR = {
    "MS1": {
        "titre": "Visibilité / Sécurité routière",
        "sous_titre": "Indicateurs MS1, P2",
        "description": (
            "Zones de croisement ou d'intersection de votre réseau "
            "(carrefours, échangeurs, passages à niveau…).\n"
            "Couches ponctuelles ou linéaires acceptées."
        ),
    },
    "MS3": {
        "titre": "Patrimoine routier / Ouvrages d'art",
        "sous_titre": "Indicateur MS3",
        "description": (
            "Ouvrages d'art, murs de soutènement, écrans acoustiques, "
            "ponts, passages à faune…\n"
            "Couches ponctuelles ou linéaires acceptées."
        ),
    },
    "MS2": {
        "titre": "Zones fréquentées / Risque sanitaire",
        "sous_titre": "Indicateur MS2",
        "description": (
            "Zones d'arrêt du public ou du personnel : aires de repos, "
            "postes d'appel d'urgence, bâtiments…\n"
            "Couches ponctuelles ou linéaires acceptées."
        ),
    },
}


# ═════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═════════════════════════════════════════════════════════════════════════

def _verifier_couche(chemin):
    """
    Vérifie qu'une couche SIG est LISIBLE (pas juste « le fichier existe »).

    Tente un gpd.read_file(rows=1) — lecture d'une seule ligne, quasi
    instantanée, mais prouve que le fichier est un SIG valide et accessible.

    Retourne (True, message_ok) ou (False, message_erreur_ami).
    """
    p = Path(chemin)
    if not p.exists():
        return False, (
            f"Fichier introuvable : {chemin}\n\n"
            "Raisons possibles :\n"
            "  • Chemin trop long (>260 caractères sous Windows)\n"
            "  • Fichier stocké sur un lecteur réseau inaccessible\n"
            "  • Faute de frappe dans le chemin\n\n"
            "Essayez de copier le fichier dans un dossier local plus court."
        )
    if _VERIF_LECTURE:
        try:
            _gpd.read_file(chemin, rows=1)
        except Exception as e:
            return False, (
                f"Le fichier existe mais n'a pas pu être lu :\n{chemin}\n\n"
                f"Erreur : {str(e)[:200]}\n\n"
                "Raisons possibles :\n"
                "  • Fichier corrompu ou format non reconnu\n"
                "  • Fichier .shp incomplet (il faut les .dbf, .shx, .prj associés)\n"
                "  • Droits d'accès insuffisants"
            )
    return True, f"✔  {p.name}"


def _ouvrir_explorateur(titre="Sélectionnez une couche SIG"):
    """
    Ouvre un explorateur de fichiers filtré sur les formats SIG acceptés.
    Retourne le chemin choisi (str) ou None si annulé.
    """
    chemin = filedialog.askopenfilename(
        title=titre,
        filetypes=[
            ("Couches SIG", "*.shp *.gpkg *.geojson"),
            ("Shapefile", "*.shp"),
            ("GeoPackage", "*.gpkg"),
            ("GeoJSON", "*.geojson"),
            ("Tous fichiers", "*.*"),
        ]
    )
    return chemin if chemin else None


# ═════════════════════════════════════════════════════════════════════════
# WIDGET RÉUTILISABLE : une ligne de saisie de couche
# ═════════════════════════════════════════════════════════════════════════

def _creer_ligne_couche(parent, label_texte, info_texte, resultats_dict,
                        cle_resultat, row_start, on_change=None,
                        registre=None, sans_donnee=None, essentielle=False):
    """
    Crée une ligne de saisie pour UNE couche SIG dans un conteneur grid.

    ─────────────────────────────────────────────────────────────────
    PRINCIPE DES TROIS ÉTATS
    ─────────────────────────────────────────────────────────────────
    Chaque couche se trouve dans l'un de ces trois états :

      "non_decide"  → l'utilisateur n'a rien fait. C'est l'état initial.
                      Il BLOQUE le bouton Continuer.
      "renseignee"  → un chemin valide a été fourni.
      "absente"     → l'utilisateur a explicitement déclaré ne pas
                      disposer de cette couche. SPRINGE tournera sans,
                      et l'indicateur concerné l'ignorera.

    Pourquoi trois états et pas deux ? Parce que « champ vide » est
    ambigu : on ne sait pas si l'utilisateur n'a pas la couche ou s'il
    a simplement oublié de la renseigner. Cette ambiguïté est exactement
    ce qui provoquait des crashs tardifs (« NoneType ») après 20 minutes
    de calcul. En forçant une décision explicite, l'oubli devient
    impossible.
    ─────────────────────────────────────────────────────────────────

    Paramètres :
      parent        : conteneur Tk (Frame ou LabelFrame)
      label_texte   : texte principal affiché (ex. "Carrefours (RRNnc)")
      info_texte    : texte détaillé SI ROUTE / catalogue
      resultats_dict: dict dans lequel stocker le chemin validé
      cle_resultat  : clé du dict pour cette couche
      row_start     : ligne de départ dans le grid du parent
      on_change     : callback optionnel appelé après chaque changement
      registre      : liste où enregistrer l'état de la ligne, pour que
                      la validation globale puisse l'interroger
      sans_donnee   : set() des couches déclarées absentes (partagé)
      essentielle   : True → couche indispensable (EEE). Pas de bouton
                      « Je ne l'ai pas », et astérisque rouge affiché.

    Retourne le numéro de la prochaine ligne libre (row_start + 2).
    """
    row = row_start

    # État courant de cette ligne. On utilise un dict mutable pour que
    # les closures (parcourir, declarer_absente) puissent le modifier.
    etat = {"valeur": "non_decide", "cle": cle_resultat, "label": label_texte}

    # ── Label de la couche ──────────────────────────────────────────────
    # L'astérisque rouge signale une couche indispensable au calcul.
    cadre_label = tk.Frame(parent)
    cadre_label.grid(row=row, column=0, sticky="w", padx=(10, 0), pady=(4, 0))

    tk.Label(
        cadre_label,
        text=f"  {label_texte}",
        font=("Arial", 10),
        anchor="w"
    ).pack(side="left")

    if essentielle:
        tk.Label(
            cadre_label,
            text=" *",
            font=("Arial", 12, "bold"),
            fg="#c62828"
        ).pack(side="left")

    # ── Bouton ℹ (toggle info détaillée) ────────────────────────────────
    # Le label_detail est créé caché ; le bouton ℹ le montre/cache.
    label_detail = tk.Label(
        parent,
        text=info_texte,
        font=("Arial", 8),
        fg="#666666",
        wraplength=480,
        justify="left",
        anchor="w"
    )
    # État d'affichage du détail (mutable via liste pour contourner la closure).
    detail_visible = [False]

    def toggle_info():
        if detail_visible[0]:
            label_detail.grid_remove()
            detail_visible[0] = False
        else:
            label_detail.grid(row=row + 1, column=0, columnspan=3,
                              sticky="w", padx=(30, 10), pady=(0, 2))
            detail_visible[0] = True

    btn_info = tk.Button(
        parent,
        text="ℹ",
        font=("Arial", 8),
        fg="#1565c0",
        relief="flat",
        command=toggle_info,
        cursor="hand2"
    )
    btn_info.grid(row=row, column=1, padx=(2, 2), pady=(4, 0))

    # ── Label de statut (chemin sélectionné ou message) ─────────────────
    # Orange au départ : ce n'est pas une erreur, mais une décision
    # encore à prendre. Le rouge est réservé aux vraies erreurs.
    var_statut = tk.StringVar(value="⚠  À renseigner")
    label_statut = tk.Label(
        parent,
        textvariable=var_statut,
        font=("Arial", 9),
        fg="#e65100",
        anchor="w",
        wraplength=260
    )
    label_statut.grid(row=row, column=4, sticky="w", padx=(4, 10), pady=(4, 0))

    # Référence au bouton « Je ne l'ai pas », créé plus bas.
    # On la stocke dans une liste pour la rendre accessible aux closures
    # définies avant sa création.
    ref_btn_absente = [None]

    def _rafraichir_bouton_absente():
        """Met en évidence le bouton « Je ne l'ai pas » s'il est actif."""
        if ref_btn_absente[0] is None:
            return
        if etat["valeur"] == "absente":
            ref_btn_absente[0].config(bg="#616161", fg="white")
        else:
            ref_btn_absente[0].config(bg="#f5f5f5", fg="#616161")

    # ── Bouton Parcourir ────────────────────────────────────────────────
    def parcourir():
        chemin = _ouvrir_explorateur(
            titre=f"Sélectionnez la couche : {label_texte}"
        )
        if not chemin:
            return  # l'utilisateur a annulé l'explorateur

        ok, msg = _verifier_couche(chemin)
        if ok:
            resultats_dict[cle_resultat] = chemin
            etat["valeur"] = "renseignee"
            # Fournir un chemin annule une éventuelle déclaration d'absence.
            if sans_donnee is not None:
                sans_donnee.discard(cle_resultat)
            var_statut.set(f"✔  {Path(chemin).name}")
            label_statut.config(fg="#2e7d32")
        else:
            resultats_dict[cle_resultat] = None
            etat["valeur"] = "non_decide"
            var_statut.set("✖  Erreur de lecture")
            label_statut.config(fg="#c62828")
            messagebox.showwarning("Couche inaccessible", msg)

        _rafraichir_bouton_absente()
        if on_change:
            on_change()

    tk.Button(
        parent,
        text="Parcourir",
        font=("Arial", 9),
        relief="flat",
        bg="#e0e0e0",
        command=parcourir,
        cursor="hand2"
    ).grid(row=row, column=2, padx=(2, 4), pady=(4, 0))

    # ── Bouton « Je ne l'ai pas » ───────────────────────────────────────
    # Absent pour la couche EEE, qui est indispensable au calcul :
    # sans points de présence, SPRINGE n'a tout simplement rien à scorer.
    if not essentielle:

        def declarer_absente():
            """Bascule entre « absente » et « non décidé »."""
            if etat["valeur"] == "absente":
                # Deuxième clic : on annule la déclaration.
                etat["valeur"] = "non_decide"
                if sans_donnee is not None:
                    sans_donnee.discard(cle_resultat)
                var_statut.set("⚠  À renseigner")
                label_statut.config(fg="#e65100")
            else:
                # On déclare la couche indisponible : le calcul tournera
                # sans elle, l'indicateur concerné l'ignorera simplement.
                resultats_dict[cle_resultat] = None
                etat["valeur"] = "absente"
                if sans_donnee is not None:
                    sans_donnee.add(cle_resultat)
                var_statut.set("—  Non disponible")
                label_statut.config(fg="#9e9e9e")

            _rafraichir_bouton_absente()
            if on_change:
                on_change()

        ref_btn_absente[0] = tk.Button(
            parent,
            text="Je ne l'ai pas",
            font=("Arial", 8),
            relief="flat",
            bg="#f5f5f5",
            fg="#616161",
            command=declarer_absente,
            cursor="hand2"
        )
        ref_btn_absente[0].grid(row=row, column=3, padx=(2, 4), pady=(4, 0))

    # ── Enregistrement dans le registre de validation ───────────────────
    # La fonction valider() parcourra ce registre pour vérifier qu'aucune
    # ligne n'est restée en "non_decide".
    if registre is not None:
        registre.append(etat)

    # La ligne de détail (row+1) est créée mais cachée par défaut.
    # La prochaine ligne disponible est row+2.
    return row + 2


# ═════════════════════════════════════════════════════════════════════════
# WIDGET RÉUTILISABLE : bloc thématique non-DIR avec bouton Ajouter
# ═════════════════════════════════════════════════════════════════════════

def _creer_bloc_nondir(parent, bloc_id, info_bloc, resultats_supp, row_start):
    """
    Crée un bloc thématique pour le mode non-DIR : un texte explicatif +
    un premier emplacement de couche + un bouton « + Ajouter une couche ».

    Les couches ajoutées dynamiquement sont stockées dans la liste
    resultats_supp (ex. resultats["supplementaires_MS3"]).

    Retourne (le LabelFrame créé, la prochaine ligne libre dans parent).
    """
    cadre = tk.LabelFrame(
        parent,
        text=f"  {info_bloc['titre']}  ({info_bloc['sous_titre']})  ",
        font=("Arial", 10, "bold"),
        padx=10, pady=6
    )
    cadre.grid(row=row_start, column=0, sticky="ew", padx=15, pady=(6, 2))

    # Description du bloc.
    tk.Label(
        cadre,
        text=info_bloc["description"],
        font=("Arial", 9),
        fg="#444444",
        wraplength=520,
        justify="left",
        anchor="w"
    ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

    # Compteur de lignes internes au cadre (mutable pour les ajouts dynamiques).
    row_interne = [1]
    # Compteur de couches ajoutées (pour les clés du dict).
    compteur = [0]

    def ajouter_couche():
        """Ajoute dynamiquement une nouvelle ligne de saisie dans le bloc."""
        idx = compteur[0]
        compteur[0] += 1
        # On crée un mini-dict temporaire pour récupérer le chemin.
        # Quand l'utilisateur valide, on l'ajoute à la liste.
        temp = {"chemin": None}

        def on_change():
            # Synchronise le chemin validé dans la liste de résultats.
            # On utilise l'index pour mettre à jour ou ajouter.
            while len(resultats_supp) <= idx:
                resultats_supp.append(None)
            resultats_supp[idx] = temp.get("chemin")

        row_interne[0] = _creer_ligne_couche(
            cadre,
            label_texte=f"Couche {idx + 1}",
            info_texte=info_bloc["description"],
            resultats_dict=temp,
            cle_resultat="chemin",
            row_start=row_interne[0],
            on_change=on_change
        )

    # Premier emplacement (toujours présent).
    ajouter_couche()

    # Bouton « + Ajouter une couche ».
    btn_ajouter = tk.Button(
        cadre,
        text="+ Ajouter une couche",
        font=("Arial", 9),
        fg="#1565c0",
        relief="flat",
        cursor="hand2",
        command=ajouter_couche
    )
    # On le place en bas du cadre ; il faudrait le repositionner après chaque
    # ajout, mais grid le fait automatiquement si on utilise row=999 (astuce).
    btn_ajouter.grid(row=999, column=0, columnspan=4, sticky="w",
                     padx=10, pady=(4, 4))

    return cadre, row_start + 1


# ═════════════════════════════════════════════════════════════════════════
# FENÊTRE PRINCIPALE
# ═════════════════════════════════════════════════════════════════════════

def fenetre_donnees_indicateurs():
    """
    Fenêtre de saisie des chemins de couches SIG pour les indicateurs.

    Retourne un dict :
      {
        "annule": bool,
        "est_dir": bool,
        "couches": { var_name: filepath_or_None, ... },
        "supplementaires_MS1": [filepath, ...],
        "supplementaires_MS2": [filepath, ...],
        "supplementaires_MS3": [filepath, ...],
      }
    """

    # ── Résultat initialisé ─────────────────────────────────────────────
    resultats = {
        "annule": False,
        "est_dir": True,
        "couches": {},
        # Couches que l'utilisateur a explicitement declarees indisponibles.
        # Distinct de "chemin None" : ici la decision est CONSCIENTE, donc
        # le calcul peut demarrer sans risque de crash tardif.
        "sans_donnee": set(),
        "supplementaires_MS1": [],
        "supplementaires_MS2": [],
        "supplementaires_MS3": [],
    }

    # Registre des lignes affichees, alimente par _creer_ligne_couche().
    # Il est vide et reconstruit a chaque bascule DIR / non-DIR, puisque
    # les widgets sont detruits et recrees.
    registre_lignes = []
    # Initialiser toutes les clés de couches à None.
    for spec in [COUCHE_EEE] + COUCHES_MS1 + COUCHES_MS3 + COUCHES_MS2 + COUCHES_TRAFIC:
        resultats["couches"][spec["var"]] = None

    # ── Fenêtre ─────────────────────────────────────────────────────────
    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    # Barre de titre (en haut à gauche). Version 26.9.0 : ancien intitulé
    # « Données de calcul des indicateurs » remplacé, et numéro d'étape
    # ajouté pour que l'utilisateur sache où il en est dans le parcours.
    fenetre.title("SPRINGE — Étape 3/4 · Renseignement des données SIG d'entrée")
    fenetre.resizable(True, True)

    # Centrage.
    def centrer(f, w=700, h=700):
        f.update_idletasks()
        x = (f.winfo_screenwidth() // 2) - (w // 2)
        y = (f.winfo_screenheight() // 2) - (h // 2)
        f.geometry(f"{w}x{h}+{x}+{y}")
    centrer(fenetre)

    # ── Zone scrollable (Canvas + Frame) ────────────────────────────────
    # Nécessaire car la fenêtre peut devenir longue avec les ajouts.
    canvas = tk.Canvas(fenetre, highlightthickness=0)
    scrollbar = ttk.Scrollbar(fenetre, orient="vertical", command=canvas.yview)
    frame_scroll = tk.Frame(canvas)

    frame_scroll.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=frame_scroll, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Scroll à la molette.
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # ── Titre ───────────────────────────────────────────────────────────
    tk.Label(
        frame_scroll,
        # Version 26.9.0 : même format « Étape N / 4 — … » que les autres
        # fenêtres du parcours.
        text="Étape 3 / 4 — Renseignement des données d'entrée",
        font=("Arial", 13, "bold")
    ).grid(row=0, column=0, pady=(10, 2))

    tk.Label(
        frame_scroll,
        text=(
            "Renseignez les chemins d'accès aux couches SIG utilisées par "
            "SPRINGE. Cliquez sur ℹ pour le détail de chaque couche."
        ),
        font=("Arial", 10),
        fg="#444444",
        wraplength=620,
        justify="center"
    ).grid(row=1, column=0, pady=(0, 6))

    # ── Légende des états ───────────────────────────────────────────────
    # Explicite d'emblée les deux règles du jeu : l'astérisque rouge et
    # l'obligation de statuer sur chaque couche. Sans cette légende, le
    # blocage du bouton Continuer paraîtrait arbitraire à l'utilisateur.
    cadre_legende = tk.Frame(frame_scroll, bg="#fff8e1",
                             highlightbackground="#ffb300",
                             highlightthickness=1)
    cadre_legende.grid(row=2, column=0, sticky="ew", padx=25, pady=(2, 6))

    tk.Label(
        cadre_legende,
        text=(
            "*  Couche indispensable — SPRINGE ne peut pas tourner sans.\n"
            "Pour toutes les autres : indiquez le fichier avec « Parcourir », "
            "ou cliquez sur « Je ne l'ai pas ».\n"
            "Une couche déclarée non disponible est simplement ignorée par "
            "les indicateurs qui l'utilisent.\n"
            "Le bouton « Continuer » reste inactif tant qu'une couche n'a pas "
            "été traitée : cela évite un arrêt du calcul en cours de route."
        ),
        font=("Arial", 9),
        bg="#fff8e1",
        fg="#5d4037",
        wraplength=600,
        justify="left"
    ).pack(padx=10, pady=6)

    # (pas de separateur ici : le cadre encadre de la legende suffit)

    # ── Question DIR / non-DIR ──────────────────────────────────────────
    cadre_dir = tk.Frame(frame_scroll)
    cadre_dir.grid(row=3, column=0, pady=(4, 4))

    tk.Label(
        cadre_dir,
        text="Êtes-vous gestionnaire d'une DIR ?",
        font=("Arial", 11, "bold")
    ).grid(row=0, column=0, columnspan=3, pady=(0, 4))

    tk.Label(
        cadre_dir,
        text=(
            "Si oui, SPRINGE affiche les noms officiels des couches du SI ROUTE.\n"
            "Si non, SPRINGE regroupe les données par thème avec des descriptions génériques."
        ),
        font=("Arial", 9),
        fg="#666666",
        wraplength=500,
        justify="center"
    ).grid(row=1, column=0, columnspan=3, pady=(0, 6))

    var_dir = tk.BooleanVar(value=True)

    # Conteneur qui changera selon DIR/non-DIR.
    # On le détruit et recrée à chaque bascule.
    conteneur_couches = [None]  # mutable pour la closure

    # ── Fonctions de construction des deux modes ────────────────────────

    def construire_mode_dir(parent):
        """Construit le contenu en mode DIR (liste nominative SI ROUTE)."""
        f = tk.Frame(parent)
        row = 0

        # OBLIGATOIRE : EEE
        cadre_oblig = tk.LabelFrame(
            f, text="  Obligatoire  ", font=("Arial", 10, "bold"),
            fg="#c62828", padx=10, pady=6
        )
        cadre_oblig.grid(row=row, column=0, sticky="ew", padx=15, pady=(6, 2))
        _creer_ligne_couche(
            cadre_oblig, COUCHE_EEE["label_dir"], COUCHE_EEE["info_dir"],
            resultats["couches"], "gdf_EEE", 0,
            registre=registre_lignes, sans_donnee=resultats["sans_donnee"],
            essentielle=True
        )
        row += 1

        # MS1 : Visibilité / Sécurité routière
        cadre_ms1 = tk.LabelFrame(
            f, text="  Visibilité / Sécurité routière  (MS1, P2)  ",
            font=("Arial", 10, "bold"), padx=10, pady=6
        )
        cadre_ms1.grid(row=row, column=0, sticky="ew", padx=15, pady=(6, 2))
        r = 0
        for spec in COUCHES_MS1:
            r = _creer_ligne_couche(
                cadre_ms1, spec["label_dir"], spec["info_dir"],
                resultats["couches"], spec["var"], r,
                registre=registre_lignes, sans_donnee=resultats["sans_donnee"]
            )
        row += 1

        # MS3 : Patrimoine routier
        cadre_ms3 = tk.LabelFrame(
            f, text="  Patrimoine routier / Ouvrages d'art  (MS3)  ",
            font=("Arial", 10, "bold"), padx=10, pady=6
        )
        cadre_ms3.grid(row=row, column=0, sticky="ew", padx=15, pady=(6, 2))
        r = 0
        for spec in COUCHES_MS3:
            r = _creer_ligne_couche(
                cadre_ms3, spec["label_dir"], spec["info_dir"],
                resultats["couches"], spec["var"], r,
                registre=registre_lignes, sans_donnee=resultats["sans_donnee"]
            )
        # Bouton ajouter pour les DIR aussi (couches OA supplémentaires).
        def _ajouter_ms3_dir():
            nonlocal r
            idx = len(resultats["supplementaires_MS3"])
            resultats["supplementaires_MS3"].append(None)
            temp = {"chemin": None}
            def on_change():
                resultats["supplementaires_MS3"][idx] = temp.get("chemin")
            _creer_ligne_couche(
                cadre_ms3, f"Couche supplémentaire {idx + 1}",
                "Couche de patrimoine routier supplémentaire (ponctuelle ou linéaire)",
                temp, "chemin", r, on_change
            )
            r += 2  # avance pour le prochain ajout
        tk.Button(
            cadre_ms3, text="+ Ajouter une couche d'ouvrage d'art",
            font=("Arial", 9), fg="#1565c0", relief="flat", cursor="hand2",
            command=_ajouter_ms3_dir
        ).grid(row=999, column=0, columnspan=4, sticky="w", padx=10, pady=(4, 4))
        row += 1

        # MS2 : Zones fréquentées
        cadre_ms2 = tk.LabelFrame(
            f, text="  Zones fréquentées / Risque sanitaire  (MS2)  ",
            font=("Arial", 10, "bold"), padx=10, pady=6
        )
        cadre_ms2.grid(row=row, column=0, sticky="ew", padx=15, pady=(6, 2))
        r = 0
        for spec in COUCHES_MS2:
            r = _creer_ligne_couche(
                cadre_ms2, spec["label_dir"], spec["info_dir"],
                resultats["couches"], spec["var"], r,
                registre=registre_lignes, sans_donnee=resultats["sans_donnee"]
            )
        # Bouton ajouter (zones fréquentées supplémentaires).
        def _ajouter_ms2_dir():
            idx = len(resultats["supplementaires_MS2"])
            resultats["supplementaires_MS2"].append(None)
            temp = {"chemin": None}
            def on_change():
                resultats["supplementaires_MS2"][idx] = temp.get("chemin")
            _creer_ligne_couche(
                cadre_ms2, f"Couche supplémentaire {idx + 1}",
                "Couche de zones fréquentées supplémentaire (ponctuelle ou linéaire)",
                temp, "chemin", r, on_change
            )
        tk.Button(
            cadre_ms2, text="+ Ajouter une couche de zone fréquentée",
            font=("Arial", 9), fg="#1565c0", relief="flat", cursor="hand2",
            command=_ajouter_ms2_dir
        ).grid(row=999, column=0, columnspan=4, sticky="w", padx=10, pady=(4, 4))
        row += 1

        # Trafic
        cadre_trafic = tk.LabelFrame(
            f, text="  Trafic  (MS1b, P2)  ",
            font=("Arial", 10, "bold"), padx=10, pady=6
        )
        cadre_trafic.grid(row=row, column=0, sticky="ew", padx=15, pady=(6, 2))
        r = 0
        for spec in COUCHES_TRAFIC:
            r = _creer_ligne_couche(
                cadre_trafic, spec["label_dir"], spec["info_dir"],
                resultats["couches"], spec["var"], r,
                registre=registre_lignes, sans_donnee=resultats["sans_donnee"]
            )
        row += 1

        return f

    def construire_mode_nondir(parent):
        """Construit le contenu en mode non-DIR (blocs thématiques groupés)."""
        f = tk.Frame(parent)
        row = 0

        # OBLIGATOIRE : EEE (identique au mode DIR)
        cadre_oblig = tk.LabelFrame(
            f, text="  Obligatoire  ", font=("Arial", 10, "bold"),
            fg="#c62828", padx=10, pady=6
        )
        cadre_oblig.grid(row=row, column=0, sticky="ew", padx=15, pady=(6, 2))
        _creer_ligne_couche(
            cadre_oblig, COUCHE_EEE["label_nondir"], COUCHE_EEE["info_nondir"],
            resultats["couches"], "gdf_EEE", 0,
            registre=registre_lignes, sans_donnee=resultats["sans_donnee"],
            essentielle=True
        )
        row += 1

        # Blocs thématiques avec bouton Ajouter.
        for bloc_id, info_bloc in BLOCS_NONDIR.items():
            liste_supp = resultats[f"supplementaires_{bloc_id}"]
            _, row = _creer_bloc_nondir(f, bloc_id, info_bloc, liste_supp, row)

        # Trafic (affiché tel quel même en non-DIR)
        cadre_trafic = tk.LabelFrame(
            f, text="  Trafic  (MS1b, P2)  ",
            font=("Arial", 10, "bold"), padx=10, pady=6
        )
        cadre_trafic.grid(row=row, column=0, sticky="ew", padx=15, pady=(6, 2))
        r = 0
        for spec in COUCHES_TRAFIC:
            r = _creer_ligne_couche(
                cadre_trafic, spec["label_nondir"], spec["info_nondir"],
                resultats["couches"], spec["var"], r,
                registre=registre_lignes, sans_donnee=resultats["sans_donnee"]
            )
        row += 1

        return f

    # ── Bascule DIR / non-DIR ───────────────────────────────────────────
    def basculer():
        """Détruit et reconstruit le contenu selon le mode choisi."""
        if conteneur_couches[0] is not None:
            conteneur_couches[0].destroy()

        # Réinitialiser les listes de supplémentaires à chaque bascule
        # (le contenu précédent est détruit visuellement de toute façon).
        resultats["supplementaires_MS1"] = []
        resultats["supplementaires_MS2"] = []
        resultats["supplementaires_MS3"] = []
        # Réinitialiser les couches individuelles.
        for cle in resultats["couches"]:
            resultats["couches"][cle] = None
        # Les widgets sont detruits : leurs etats enregistres n'ont plus
        # de sens. On vide le registre EN PLACE (.clear() et non
        # "registre_lignes = []") pour que les closures deja creees
        # continuent de pointer sur la meme liste.
        registre_lignes.clear()
        resultats["sans_donnee"].clear()

        if var_dir.get():
            conteneur_couches[0] = construire_mode_dir(frame_scroll)
        else:
            conteneur_couches[0] = construire_mode_nondir(frame_scroll)

        conteneur_couches[0].grid(row=5, column=0, sticky="ew")
        resultats["est_dir"] = var_dir.get()

    # Boutons DIR Oui / Non.
    btn_dir_oui = tk.Button(
        cadre_dir, text="Oui, je suis d'une DIR",
        font=("Arial", 10), relief="flat", padx=10, pady=6, width=20,
        command=lambda: [var_dir.set(True), _refresh_dir_btns(), basculer()]
    )
    btn_dir_oui.grid(row=2, column=0, padx=(0, 5))

    btn_dir_non = tk.Button(
        cadre_dir, text="Non / Autre gestionnaire",
        font=("Arial", 10), relief="flat", padx=10, pady=6, width=20,
        command=lambda: [var_dir.set(False), _refresh_dir_btns(), basculer()]
    )
    btn_dir_non.grid(row=2, column=1, padx=(5, 0))

    def _refresh_dir_btns():
        """Met à jour l'apparence des boutons DIR/non-DIR."""
        if var_dir.get():
            btn_dir_oui.configure(bg="#2e7d32", fg="white")
            btn_dir_non.configure(bg="#e0e0e0", fg="black")
        else:
            btn_dir_oui.configure(bg="#e0e0e0", fg="black")
            btn_dir_non.configure(bg="#2e7d32", fg="white")

    ttk.Separator(frame_scroll, orient="horizontal").grid(
        row=4, column=0, sticky="ew", padx=20, pady=4
    )

    # Construction initiale (mode DIR par défaut).
    _refresh_dir_btns()
    basculer()

    # ── Footer Annuler / Continuer ──────────────────────────────────────
    cadre_footer = tk.Frame(fenetre)
    cadre_footer.pack(side="bottom", pady=8)

    def annuler():
        resultats["annule"] = True
        canvas.unbind_all("<MouseWheel>")
        fenetre.destroy()

    def valider():
        # ── 1. Couche EEE : strictement indispensable ────────────────
        if not resultats["couches"].get("gdf_EEE"):
            messagebox.showwarning(
                "Donnée obligatoire manquante",
                "La couche de points de présence EEE est obligatoire (*).\n"
                "Sans elle, SPRINGE n'a aucune donnée a scorer.\n\n"
                "Veuillez la renseigner avant de continuer."
            )
            return

        # ── 2. Toutes les autres couches doivent avoir ete DECIDEES ──
        # C'est le verrou qui empeche l'oubli silencieux : on refuse de
        # lancer un calcul de 20 minutes qui planterait sur une couche
        # que l'utilisateur croyait avoir renseignee.
        non_decidees = [e["label"] for e in registre_lignes
                        if e["valeur"] == "non_decide"]

        if non_decidees:
            apercu = "\n".join(f"   • {lab}" for lab in non_decidees[:12])
            if len(non_decidees) > 12:
                apercu += f"\n   … et {len(non_decidees) - 12} autre(s)"
            messagebox.showwarning(
                "Couches non renseignées",
                f"{len(non_decidees)} couche(s) attendent encore une décision :\n\n"
                f"{apercu}\n\n"
                "Pour chacune, deux possibilités :\n"
                "   • « Parcourir » pour indiquer le fichier\n"
                "   • « Je ne l'ai pas » si vous n'en disposez pas\n\n"
                "Les couches déclarées indisponibles sont simplement "
                "ignorées par les indicateurs concernés."
            )
            return

        resultats["est_dir"] = var_dir.get()
        canvas.unbind_all("<MouseWheel>")
        fenetre.destroy()

    tk.Button(
        cadre_footer, text="✖  Annuler", font=("Arial", 10),
        fg="gray", command=annuler, width=14
    ).grid(row=0, column=0, padx=10)

    tk.Button(
        cadre_footer, text="Continuer  ▶", font=("Arial", 10, "bold"),
        bg="#1565c0", fg="white", relief="flat", command=valider, width=14
    ).grid(row=0, column=1, padx=10)

    # ── Blocage + attente ───────────────────────────────────────────────
    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()

    # Nettoyage des supplémentaires : retirer les None (couches non remplies).
    for cle in ["supplementaires_MS1", "supplementaires_MS2", "supplementaires_MS3"]:
        resultats[cle] = [c for c in resultats[cle] if c is not None]

    # Le set est converti en liste triee : plus lisible dans le rapport
    # d'execution et serialisable en JSON.
    resultats["sans_donnee"] = sorted(resultats["sans_donnee"])

    return resultats


# ── Démonstration locale ────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    res = fenetre_donnees_indicateurs()
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
