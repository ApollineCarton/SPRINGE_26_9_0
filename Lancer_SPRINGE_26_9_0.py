# -*- coding: utf-8 -*-
"""
=======================================================================
SPRINGE — Système de PRiorisation des INterventions de Gestion des EEE
=======================================================================
*** VERSION BETA ***

Version 26.9.0 (septembre 2026)
Auteur : Apolline CARTON

Objectif : outil d'aide à la décision pour caractériser et comparer les
           tronçons routiers colonisés par des plantes exotiques
           envahissantes (EEE), à destination des DIR.

SPRINGE est DESCRIPTIF et COMPARATIF, jamais prescriptif : il caractérise
et score les tronçons selon trois enjeux (MS = Maintenance Sécurité,
N = Nature, P = Propagation), mais le gestionnaire conserve l'entière
maîtrise de ses arbitrages.

─────────────────────────────────────────────────────────────────
ORGANISATION DU SCRIPT
─────────────────────────────────────────────────────────────────
  PARTIE 1  Initialisation, gestion de crash, saisies utilisateur
            (parcours en 4 étapes, avec lecture anticipée du réseau
             routier et des points EEE, mapping des espèces)
  PARTIE 2  Chargement des données (autres couches locales, Excel, API)
  PARTIE 3  Préparation des calculs (déduplication, jointure, scoring)
  PARTIE 4  Calcul des indicateurs MS / N / P
  PARTIE 5  Score final, densité, export GeoPackage, rapport

Toute la logique métier vit dans 00_fonctions/ : ce script est un
CHEF D'ORCHESTRE. Il enchaîne les appels, il ne calcule rien lui-même.
Les fenêtres de saisie suivent la même règle — une fenêtre = un module.

VERSION 26.9.0 — PRINCIPAUX CHANGEMENTS
  - Fenêtres réordonnées en 4 étapes numérotées (voir BLOC INPUTS).
  - Identifiant des tronçons choisi dans une liste déroulante, puis
    renommé en interne en 'nom_plo_fi'.
  - Fenêtre « Comprendre vos données » supprimée.
  - Mapping des espèces et paramétrage de la caractérisation avancés
    AVANT le récapitulatif (anciennes sections 3.0 / 3.1 / 3.1bis).
  - Récapitulatif enrichi (espèces, conformité, caractérisation).
─────────────────────────────────────────────────────────────────
"""

# ==========================================================
# 🔵 PARTIE 1 - INITIALISATION
# ==========================================================

# ----------------------------------------------------------
# 1.1 - Bibliothèques
# ----------------------------------------------------------
# Regroupées par famille plutôt qu'une par ligne : plus court à lire,
# et on repère immédiatement ce dont le script dépend réellement.

# -- Standard Python --
import datetime as datetime          # horodatage des exports et du rapport
import importlib.util                # chargement dynamique de 00_fonctions/
import os                            # ouverture du dossier de sortie (fin de script)
import sys                           # excepthook + sys.path vers 00_fonctions/
from pathlib import Path

import plotly.graph_objects as go    # pour graphiques intéractifs


# -- Calcul scientifique et données --
import pandas as pd                  # df_scoring
import geopandas as gpd              # manipulation des données SIG

# -- Interface utilisateur --
import tkinter as tk                 # messages de fin de traitement
from tkinter import messagebox       # rend tk.messagebox utilisable

# ──────────────────────────────────────────────────────────────────────
# POURQUOI SI PEU D'IMPORTS ICI
# ──────────────────────────────────────────────────────────────────────
# Ce script est un CHEF D'ORCHESTRE : il enchaîne des appels, il ne
# calcule rien lui-même. Les bibliothèques lourdes (numpy, matplotlib,
# scipy, requests…) sont importées par les modules de 00_fonctions/ qui
# en ont réellement besoin.
#
# C'est possible parce que la boucle de chargement ci-dessous utilise
# importlib.util.spec_from_file_location + exec_module : chaque module
# obtient son PROPRE espace de noms et importe ses propres dépendances.
# Il n'hérite de rien de ce script. Exemples vérifiés :
#     deduplication_troncons.py  → import string, geopandas
#     generer_graphiques.py      → import matplotlib.pyplot, numpy
#     appel_api.py               → import requests, geopandas
#
# Imports retirés car jamais utilisés ici (ils provoquaient des
# ModuleNotFoundError pour des paquets dont SPRINGE n'a pas besoin) :
#     geojson, numpy, scipy.cKDTree, shapely.Point, pyproj.CRS,
#     contextily, matplotlib, requests, string, warnings, traceback,
#     tkinter.filedialog, tkinter.simpledialog, tkinter.ttk
#
# Deux autres avaient déjà disparu aux versions précédentes :
#     owslib.wfs.WebFeatureService → remplacé par appel_api.py (requests)
#     shapely.ops.unary_union      → déprécié, remplacé par union_all()
# ──────────────────────────────────────────────────────────────────────

print("Bibliothèques chargées\n")


# ----------------------------------------------------------
# 1.2 - Initiatilisation du rapport d'execution
# ----------------------------------------------------------
_DATE_DEBUT_SPRINGE = datetime.datetime.now()
_ETAPE_COURANTE = "Initialisation"          # ← mis à jour tout au long du code pour savoir où le crash a eu lieu
_WARNINGS_SPRINGE = []                      # avertissements non bloquants collectés (API partielle etc.)
_API_STATUTS = {}                           # statuts de chargement des APIs
_OUTPUT_DIR_RAPPORT = None                  # défini après la saisie utilisateur

print(f"▶ SPRINGE démarré le {_DATE_DEBUT_SPRINGE.strftime('%d/%m/%Y à %H:%M:%S')}")
# ----------------------------------------------------------
# 1.3 - GESTIONNAIRE GLOBAL DE CRASH (rapport d'incident)
# ----------------------------------------------------------
# sys.excepthook est appelé automatiquement par Python pour toute exception
# non catchée. On l'utilise pour générer le rapport d'incident AVANT que
# le programme ne s'arrête, sans avoir à ré-indenter tout le code.


def _springe_excepthook(exc_type, exc_value, exc_tb):
    """Intercepte tout crash non géré et génère un rapport d'incident."""
    import traceback as _tb
    # Reconstituer le traceback complet en chaîne
    tb_lines = _tb.format_exception(exc_type, exc_value, exc_tb)
    tb_str   = "".join(tb_lines)

    print("\n" + "=" * 72)
    print("🚨  SPRINGE - ERREUR NON GÉRÉE DÉTECTÉE")
    print("=" * 72)
    print(tb_str)

    # Dossier de sortie : OUTPUT_DIR si déjà défini, sinon répertoire courant
    _dossier = globals().get("OUTPUT_DIR") or globals().get("_OUTPUT_DIR_RAPPORT") or Path(__file__).parent / "02_outputs"

    # Contexte disponible au moment du crash
    _ctx = {
        "Étape en cours"        : globals().get("_ETAPE_COURANTE", "inconnue"),
        # 26.9.0 : "fichier_troncons" (la variable réelle ; "_fichier_troncons_path"
        # n'existait pas, d'où un "non défini" systématique dans les rapports).
        "Fichier tronçons"      : globals().get("fichier_troncons", "non défini"),
        # 26.9.0 : nom CHOISI par l'utilisateur, plus parlant que le nom interne.
        "Colonne identifiant"   : globals().get("colonne_id_origine", globals().get("colonne_id", "non défini")),
        "DIR"                   : globals().get("DIR", "non défini"),
        "Nb tronçons bruts"     : len(globals()["gdf_troncons"]) if "gdf_troncons" in globals() else "non chargé",
        "Nb tronçons dédupés"   : len(globals()["gdf_troncons_copy"]) if "gdf_troncons_copy" in globals() else "non chargé",
        "Nb points EEE"         : len(globals()["gdf_EEE"]) if "gdf_EEE" in globals() else "non chargé",
        "Avertissements accumulés" : "; ".join(globals().get("_WARNINGS_SPRINGE", [])) or "aucun",
    }

    # Appel uniquement si le module est déjà chargé (il l'est dès la fin de la section 1)
    _gr = globals().get("generer_rapport")
    if _gr is not None:
        try:
            _gr.generer_rapport_incident(
                output_dir  = _dossier,
                exc         = exc_value,
                etape       = globals().get("_ETAPE_COURANTE", "inconnue"),
                date_debut  = _DATE_DEBUT_SPRINGE,
                DIR         = globals().get("DIR", "DIR"),
                NOM         = globals().get("NOM", "utilisateur"),
                name        = globals().get("name", "SPRINGE"),
                contexte    = _ctx,
            )
        except Exception as _e_rapport:
            print(f"⚠️  Impossible de générer le rapport d'incident : {_e_rapport}")
    else:
        # Module pas encore chargé → rapport minimal en .txt
        #
        # SEUL nommage encore fabriqué à la main dans SPRINGE, et c'est
        # volontaire : on arrive ici quand le crash est survenu AVANT le
        # chargement de 00_fonctions/, donc nommer_fichiers_sortie n'existe pas
        # non plus. Ce filet de dernier recours ne doit dépendre d'aucun
        # module, sinon il échouerait précisément dans le cas où il sert.
        # L'horodatage à la seconde est conservé ici : plusieurs crashs
        # précoces peuvent s'enchaîner en quelques secondes.
        _ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        _f  = Path(_dossier) / f"INCIDENT_SPRINGE_MINIMAL_{_ts}.txt"
        try:
            Path(_dossier).mkdir(parents=True, exist_ok=True)
            with open(_f, "w", encoding="utf-8") as _fh:
                _fh.write("SPRINGE — RAPPORT D'INCIDENT MINIMAL\n")
                _fh.write(f"Date : {datetime.datetime.now()}\n")
                _fh.write(f"Étape : {globals().get('_ETAPE_COURANTE', 'inconnue')}\n\n")
                _fh.write(tb_str)
            print(f"📄 Rapport d'incident minimal : {_f}")
        except Exception:
            pass

    # Comportement Python par défaut (affiche le traceback dans la console)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _springe_excepthook

""" NOTE — La solution la plus robuste est d'utiliser sys.excepthook — 
    un hook Python qui intercepte toute exception non catchée, 
    déclenche le rapport d'incident, et n'oblige pas à ré-indenter le code.
    # installé dès le démarrage : intercepte toute exception non catchée, 
    # génère automatiquement le rapport d'incident — sans toucher à l'indentation du code existant
"""

# ----------------------------------------------------------
# 1.2 - Import des fonctions depuis le fichier fonctions
# ----------------------------------------------------------

# Chemin du dossier
fonctions = Path(__file__).parent / "00_fonctions"

# Ajouter le dossier au sys.path pour pouvoir importer
sys.path.append(str(fonctions))

# Boucle sur tous les fichiers .py
for fichier in fonctions.glob("*.py"):
    if fichier.name == "__init__.py":
        continue  # ignorer __init__.py si présent
    module_name = fichier.stem  # nom sans .py
    spec = importlib.util.spec_from_file_location(module_name, fichier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # On ajoute le module globalement pour y accéder directement
    globals()[module_name] = module
    #print pour le suivi du chargement
    print(f"✔️ {fichier.name} chargé")

print("Les fonctions sont chargées\n")

# Import du module de rapport (chargé de la même façon que les autres fonctions)
_spec_r = importlib.util.spec_from_file_location("generer_rapport", fonctions / "generer_rapport.py")
_mod_r  = importlib.util.module_from_spec(_spec_r)
_spec_r.loader.exec_module(_mod_r)
generer_rapport = _mod_r
print("✔️ generer_rapport.py chargé\n")




"""
════════════════════════════════════════════════════════════════════════
BLOC INPUTS UTILISATEUR — PARCOURS EN 4 ÉTAPES (version 26.9.0)
════════════════════════════════════════════════════════════════════════
PRINCIPE :
    L'utilisateur répond à TOUT avant que le moindre calcul long ne
    commence. Ensuite le programme tourne jusqu'au bout sans interruption.

Chaque fenêtre vit dans son propre module de 00_fonctions/, chargé
automatiquement par la boucle importlib ci-dessus. Ce script ne fait
que les APPELER dans l'ordre et récupérer leurs résultats.

ORDRE DES FENÊTRES (réorganisé en 26.9.0) :

    Accueil                                     fenetre_accueil.py
    Étape 1    Identification                   fenetre_identification.py
    Étape 2    Description de la zone d'étude   fenetre_zone_travail.py
                 ↳ lecture de l'emprise et du réseau routier
    Étape 2    (suite) Identifiant des tronçons fenetre_identifiant_troncons.py
                 ↳ renommage interne de la variable choisie en 'nom_plo_fi'
    Étape 3    Données SIG d'entrée             fenetre_donnees_indicateurs.py
                 ↳ lecture de la couche de points EEE
    Étape 4    Compréhension des données d'entrée :
                 espèces à analyser             fenetre_selection_especes.py
                 colonne + correspondance       fenetre_mapping_especes.py
                 ↳ filtrage des espèces retenues
                 conformité + colonnes          fenetre_mapping_colonnes_EEE.py
    Récapitulatif avant démarrage               fenetre_recap.py

    SUPPRIMÉE : fenetre_comprendre_donnees.py (motif détaillé plus bas).

POURQUOI DES LECTURES DE FICHIERS AU MILIEU DES FENÊTRES :
    - la liste déroulante de l'identifiant a besoin des colonnes du réseau
      routier → le réseau est lu juste après l'étape 2 ;
    - les fenêtres de l'étape 4 travaillent sur le CONTENU de la couche EEE
      (colonnes, valeurs distinctes, effectifs) → elle est lue juste après
      l'étape 3, filtrée sur l'emprise, pour que les effectifs affichés
      soient ceux des points réellement traités.
    Ces deux lectures portent sur des fichiers locaux et sont rapides.
    Les chargements LONGS (autres couches SIG, API) restent APRÈS le
    récapitulatif, en Partie 2.

VARIABLES PRODUITES (utilisées dans la suite du script) :
    DIR, NOM            → structure et opérateur
    name                → intitulé de projet (nommer_fichiers_sortie)
    OUTPUT_DIR          → dossier de sortie (Path)
    choix               → "yes" (Option A) ou "no" (Option B)
    fichier_emprise     → chemin du fichier de zone d'emprise (Option A seulement)
    fichier_troncons    → chemin du fichier réseau routier
    emprise             → emprise de travail (GeoDataFrame, tampon 2 km)
    gdf_troncons        → réseau routier lu dans l'emprise, en Lambert 93
    colonne_id_origine  → variable identifiant CHOISIE par l'utilisateur
    colonne_id          → toujours 'nom_plo_fi' (renommage interne)
    _est_dir, _chemins  → profil DIR et chemins des couches SIG
    _supp_MS1/MS2/MS3   → couches ajoutées manuellement
    _gdf_EEE_charge     → couche EEE telle que lue (pour le rapport)
    gdf_EEE             → points EEE mappés (species_name_sci) ET filtrés
    especes_retenues    → codes des espèces cochées ('Renouees'…)
    especes_retenues_sci→ mêmes espèces en species_name_sci
    _colonne_espece_source, _mapping_especes_valeurs → traçabilité mapping
    _caracterisation_active, _mapping_colonnes_EEE,
    _rapport_conformite_EEE → paramétrage de la caractérisation EEE
════════════════════════════════════════════════════════════════════════
"""

_ETAPE_COURANTE = "Saisies utilisateur"


# ----------------------------------------------------------
# Outil : arrêt propre avec message à l'écran
# ----------------------------------------------------------
# Jusqu'ici, les arrêts « métier » (aucun point EEE, etc.) se faisaient par
# un simple raise SystemExit : le message n'apparaissait que dans la
# console, que l'utilisateur ne regarde pas forcément. Depuis 26.9.0, ces
# arrêts peuvent survenir PENDANT le questionnaire (lectures anticipées) :
# l'utilisateur doit comprendre pourquoi SPRINGE s'arrête.
#
# On garde raise SystemExit (et non une exception ordinaire) : il s'agit
# d'un arrêt voulu, pas d'un plantage. SystemExit ne passe pas par
# sys.excepthook, donc aucun rapport d'incident n'est généré à tort.
#
# Les annulations par l'utilisateur (bouton Annuler) gardent, elles, un
# SystemExit silencieux : il sait déjà pourquoi le programme s'arrête.

def _arret_springe(titre, message):
    """Affiche une boîte d'erreur, écrit en console, puis arrête SPRINGE."""
    print(f"\n⛔ {titre} — {message}")
    _racine = tk.Tk()          # racine Tk temporaire, cachée…
    _racine.withdraw()         # … car seule la boîte de message doit apparaître
    messagebox.showerror(titre, message, parent=_racine)
    _racine.destroy()
    raise SystemExit(f"{titre} : {message}")


# ── ACCUEIL ─────────────────────────────────────────────────────────────
fenetre_accueil.fenetre_accueil()


# ════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 — IDENTIFICATION
# ════════════════════════════════════════════════════════════════════════
_res1 = fenetre_identification.fenetre_identification()

# Si l'utilisateur a cliqué Annuler → arrêt propre du programme
if _res1["annule"]:
    raise SystemExit("SPRINGE annulé par l'utilisateur à l'étape 1.")

# Variables globales utilisées dans tout le reste du script
DIR        = _res1["DIR"]
NOM        = _res1["NOM"]
OUTPUT_DIR = _res1["OUTPUT_DIR"]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)   # crée le dossier si inexistant
# `name` est désormais un simple INTITULÉ DE PROJET, affiché en tête des
# rapports. Il n'entre PLUS dans le nom des fichiers produits.
#
# Ancienne valeur : f"SPRINGE_modele_Version2026_{DIR}_{NOM}". Elle contenait
# déjà la structure et l'opérateur, que les fonctions d'export rajoutaient
# ensuite, d'où le doublon constaté le 08/09/2026 :
#     projet_SPRINGE_SPRINGE_modele_Version2026_cbn_apo_cbn_20260724
# Le nommage est maintenant centralisé dans nommer_fichiers_sortie.py.
name       = nommer_fichiers_sortie.SOCLE_VERSION
_OUTPUT_DIR_RAPPORT = OUTPUT_DIR                # pour le gestionnaire de crash

print(f"✔️  Structure    : {DIR}")
print(f"✔️  Opérateur   : {NOM}")
print(f"✔️  Sortie       : {OUTPUT_DIR}")


# ════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 — DESCRIPTION DE LA ZONE D'ÉTUDE
# ════════════════════════════════════════════════════════════════════════
# Demande le mode de définition de la zone d'étude (Option A ou B) puis
# les fichiers SIG correspondants. La fenêtre ne fait que stocker des
# chemins ; la lecture est faite juste en dessous.

_res_zone = fenetre_zone_travail.fenetre_zone_travail()

if _res_zone["annule"]:
    raise SystemExit("SPRINGE annulé par l'utilisateur à l'étape 2 (zone d'étude).")

choix             = _res_zone["choix"]            # "yes" (A) ou "no" (B) — valeurs historiques conservées
fichier_troncons  = _res_zone["fichier_troncons"]
fichier_emprise   = _res_zone.get("fichier_emprise")  # None si Option B

# Libellé lisible du mode de zone. Calculé UNE fois ici et réutilisé plus
# bas par le rapport d'exécution, pour que console, récapitulatif et rapport
# disent exactement la même chose.
_mode_emprise_libelle = (
    "Option A (fichier zone d'emprise + réseau routier)" if choix == "yes"
    else "Option B (réseau routier = zone d'étude)"
)
print(f"✔️  Zone d'étude  : {_mode_emprise_libelle}")
print(f"✔️  Réseau routier: {Path(fichier_troncons).name}")
if fichier_emprise:
    print(f"✔️  Zone d'emprise: {Path(fichier_emprise).name}")


# ----------------------------------------------------------
# Lecture de l'emprise et du réseau routier
# ----------------------------------------------------------
# DÉPLACÉ EN 26.9.0 depuis la section 2.1 (Partie 2). Motif : la fenêtre
# suivante (identifiant des tronçons) propose une liste déroulante des
# variables du réseau routier ; il faut donc l'avoir lu avant.
#
# Le code de lecture lui-même est inchangé.
#
# try / finally : quoi qu'il arrive pendant la lecture (fichier corrompu,
# CRS illisible…), la petite fenêtre « Traitement en cours » est refermée.
# L'erreur éventuelle continue ensuite vers le gestionnaire de crash, qui
# produit le rapport d'incident comme avant.

_ETAPE_COURANTE = "Lecture de la zone d'étude et du réseau routier"
_fen = traitement_en_cours.traitement_en_cours("Lecture de la zone d'étude et du réseau routier")

try:
    if choix == "yes":
        # ── Option A : l'utilisateur a fourni une emprise séparée ──

        # Lecture brute du fichier d'emprise (polygone de zone d'étude).
        emprise_brute = gpd.read_file(fichier_emprise)

        # Construction de l'emprise de travail : reprojection L93, nettoyage
        # des géométries vides, tampon de 2 km, validation.
        # enveloppe_convexe=False : on RESPECTE la forme fournie par
        # l'utilisateur. La passer en enveloppe convexe élargirait à tort
        # une emprise concave (département, vallée, linéaire coudé…).
        emprise = construire_emprise.construire_emprise(
            emprise_brute,
            taille_tampon_km=2,
            nom="emprise utilisateur",
            enveloppe_convexe=False,
        )

        # Chargement des tronçons filtrés par l'emprise.
        # ⚠️ On passe emprise.geometry (GeoSeries PORTEUSE DE SON CRS) et non
        # un tuple : geopandas reprojette alors le filtre vers le CRS du
        # fichier lu. Avec un tuple, la bbox est supposée déjà dans le CRS
        # du fichier — d'où 0 entité si les CRS diffèrent.
        gdf_troncons = gpd.read_file(fichier_troncons, bbox=emprise.geometry)
        if gdf_troncons.crs and gdf_troncons.crs.to_epsg() != 2154:
            gdf_troncons = reprojeter_en_lambert.reprojeter_en_lambert(gdf_troncons, "tronçons")

    else:
        # ── Option B : les tronçons définissent eux-mêmes la zone ──

        gdf_troncons = gpd.read_file(fichier_troncons)
        if gdf_troncons.crs and gdf_troncons.crs.to_epsg() != 2154:
            gdf_troncons = reprojeter_en_lambert.reprojeter_en_lambert(gdf_troncons, "tronçons")

        # enveloppe_convexe=True : des tronçons sont des LIGNES, elles ne
        # délimitent aucune surface — il faut en dériver une enveloppe.
        # (c'est ce que faisait l'ancien code, mais buffer(0) vidait tout avant)
        emprise = construire_emprise.construire_emprise(
            gdf_troncons,
            taille_tampon_km=2,
            nom="emprise depuis tronçons",
            enveloppe_convexe=True,
        )
finally:
    _fen.destroy()

# NOTE — On ne conserve plus minx/miny/maxx/maxy comme variables globales.
# Les tuples de bornes étaient précisément la source du bug de filtrage :
# passés à gpd.read_file(bbox=...), ils sont interprétés dans le CRS DU
# FICHIER LU, sans reprojection. On passe désormais l'objet `emprise`
# lui-même, qui transporte son CRS — voir charger_couches_sig.py.

# Garde-fou (ajout 26.9.0) : un réseau vide ne permet aucun calcul. Cas
# typique : en Option A, un fichier de zone qui ne recouvre pas le réseau.
# Mieux vaut le dire maintenant que planter à la déduplication.
if len(gdf_troncons) == 0:
    _arret_springe(
        "Réseau routier vide",
        "Aucun tronçon du réseau routier n'a été trouvé dans la zone d'étude.\n\n"
        "Vérifiez que le fichier de zone d'emprise recouvre bien votre réseau "
        "routier (mêmes secteurs géographiques)."
    )

print(f"✔️  Tronçons lus  : {len(gdf_troncons)}")


# ════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 (suite) — IDENTIFIANT DES TRONÇONS
# ════════════════════════════════════════════════════════════════════════
# Liste déroulante des variables du réseau routier (26.9.0). La colonne de
# géométrie est exclue : elle ne peut pas servir d'identifiant.

_colonnes_troncons = [c for c in gdf_troncons.columns
                      if c != gdf_troncons.geometry.name]

_res_id = fenetre_identifiant_troncons.fenetre_identifiant_troncons(
    colonnes_disponibles = _colonnes_troncons
)

if _res_id["annule"]:
    raise SystemExit("SPRINGE annulé par l'utilisateur à l'étape 2 (identifiant des tronçons).")

colonne_id_origine = _res_id["colonne_id"]
print(f"✔️  Variable identifiant choisie : {colonne_id_origine}")


# ----------------------------------------------------------
# Renommage interne de l'identifiant en 'nom_plo_fi'
# ----------------------------------------------------------
# POURQUOI : de nombreux modules de calcul (calculer_*_impact,
# detecter_elements_sur_troncon, calculer_vulnerabilite_facon1,
# creer_objet_scoring appelé sans colonne_id…) et plusieurs affichages de
# ce script utilisent le nom 'nom_plo_fi' EN DUR. Tant que tout le monde
# tapait nom_plo_fi, ça passait ; avec une liste déroulante, un
# gestionnaire non-DIR choisira légitimement une autre variable.
#
# Plutôt que de modifier une quinzaine de modules à quelques jours de la
# livraison, on RENOMME la variable choisie en 'nom_plo_fi' dès la lecture.
# Tout l'aval voit alors le nom qu'il attend. Une seule ligne à maintenir.
#
# CONTREPARTIE : dans le GeoPackage de sortie, l'identifiant s'appelle
# 'nom_plo_fi' et non le nom d'origine. Le nom d'origine est conservé dans
# colonne_id_origine, affiché dans le récapitulatif et le rapport d'exécution.
#
# CONFLIT DE NOMS : si le fichier contient DÉJÀ une variable nommée
# nom_plo_fi (quelle que soit la casse) qui n'est PAS celle choisie, on la
# met de côté sous 'nom_plo_fi_origine' avant de renommer. La casse compte :
# le GeoPackage (SQLite) considère 'NOM_PLO_FI' et 'nom_plo_fi' comme la
# MÊME colonne et refuserait l'export.

COLONNE_ID_INTERNE = "nom_plo_fi"

if colonne_id_origine != COLONNE_ID_INTERNE:

    # Variables homonymes de nom_plo_fi (toutes casses) autres que le choix.
    _homonymes = [c for c in gdf_troncons.columns
                  if str(c).lower() == COLONNE_ID_INTERNE
                  and c != colonne_id_origine]

    for _homonyme in _homonymes:
        _nom_de_cote = f"{COLONNE_ID_INTERNE}_origine"
        gdf_troncons = gdf_troncons.rename(columns={_homonyme: _nom_de_cote})
        _WARNINGS_SPRINGE.append(
            f"Identifiant des tronçons : la variable « {_homonyme} » du réseau "
            f"routier a été renommée « {_nom_de_cote} » pour laisser la place à "
            f"l'identifiant choisi « {colonne_id_origine} »."
        )

    # Renommage effectif de la variable choisie.
    gdf_troncons = gdf_troncons.rename(columns={colonne_id_origine: COLONNE_ID_INTERNE})
    print(f"   ↳ renommée « {COLONNE_ID_INTERNE} » en interne")

# À partir d'ici, tout le script travaille avec 'nom_plo_fi'.
colonne_id = COLONNE_ID_INTERNE


# ════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 — RENSEIGNEMENT DES DONNÉES SIG D'ENTRÉE
# ════════════════════════════════════════════════════════════════════════
# Fenêtre de renseignement des chemins d'accès à toutes les couches SIG
# nécessaires au calcul des indicateurs. Elle regroupe la couche obligatoire
# (points EEE), les couches propres à chaque indicateur (patrimoine, carrefours,
# aires de repos…) et le trafic (TMJA), selon le profil DIR / non-DIR.
# Cette fenêtre ne fait que COLLECTER les chemins.
_res_donnees_indic = fenetre_donnees_indicateurs.fenetre_donnees_indicateurs()

# Annulation par l'utilisateur → arrêt propre du programme.
if _res_donnees_indic["annule"]:
    raise SystemExit("SPRINGE annulé par l'utilisateur à l'étape 3 (données SIG d'entrée).")

# Récupération des choix de l'utilisateur :
#   _est_dir  : True si gestionnaire d'une DIR (couches SI ROUTE nommées)
#   _chemins  : dict {nom_variable_couche: chemin_fichier ou None}
#   _supp_*   : listes de chemins de couches ajoutées manuellement par thème
_est_dir  = _res_donnees_indic["est_dir"]
_chemins  = _res_donnees_indic["couches"]
_supp_MS1 = _res_donnees_indic["supplementaires_MS1"]
_supp_MS2 = _res_donnees_indic["supplementaires_MS2"]
_supp_MS3 = _res_donnees_indic["supplementaires_MS3"]

# NOTE 26.9.0 — _fichier_tmja_path n'est plus extrait ici : il ne servait
# qu'à la ligne « Données TMJA » du récapitulatif, supprimée. Le TMJA reste
# chargé normalement en Partie 2 via _chemins["gdf_tmja"].

# Suivi console de ce que l'utilisateur a renseigné.
print(f"✔️  Mode : {'DIR' if _est_dir else 'non-DIR'}")
for _var, _chemin in _chemins.items():
    _etat = Path(_chemin).name if _chemin else "non renseigné"
    print(f"  {_var:30s} → {_etat}")
for _bloc, _paths in [("MS1", _supp_MS1), ("MS2", _supp_MS2), ("MS3", _supp_MS3)]:
    if _paths:
        print(f"  Couches supplémentaires {_bloc} : {len(_paths)}")


# ----------------------------------------------------------
# Lecture de la couche de points EEE
# ----------------------------------------------------------
# AJOUT 26.9.0. Auparavant, gdf_EEE était lu en Partie 2 avec toutes les
# autres couches (charger_couches_utilisateur). Les fenêtres de l'étape 4
# ayant été avancées AVANT le récapitulatif, la couche EEE doit être lue
# ici. On réutilise exactement la même fonction unitaire (charger_couche) :
# même filtrage sur l'emprise, même reprojection Lambert 93, mêmes messages.
#
# charger_couche ne lève pas d'exception : en cas d'échec elle renvoie None
# et ajoute un avertissement. Or la couche EEE est INDISPENSABLE : on arrête
# donc SPRINGE avec un message clair plutôt que de planter plus loin.

_ETAPE_COURANTE = "Lecture de la couche de points EEE"
_fen = traitement_en_cours.traitement_en_cours("Lecture de la couche de points EEE")
try:
    gdf_EEE = charger_couches_sig.charger_couche(
        chemin         = _chemins.get("gdf_EEE"),
        emprise        = emprise,
        nom_couche     = "gdf_EEE",
        warnings_liste = _WARNINGS_SPRINGE,
    )
finally:
    _fen.destroy()

if gdf_EEE is None:
    _arret_springe(
        "Couche de points EEE illisible",
        "La couche de points de présence EEE n'a pas pu être lue.\n\n"
        "Vérifiez que le fichier n'est pas ouvert en écriture dans un autre "
        "logiciel et qu'il n'est pas endommagé (détail dans la console)."
    )

if len(gdf_EEE) == 0:
    _arret_springe(
        "Aucun point EEE dans la zone d'étude",
        "La couche de points de présence EEE ne contient aucun point dans la "
        "zone d'étude.\n\nVérifiez que la couche EEE et la zone d'étude "
        "couvrent les mêmes secteurs géographiques."
    )

# Référence à la couche TELLE QUE LUE (avant mapping et filtrage des
# espèces). Elle sert uniquement au rapport d'exécution, qui liste le
# nombre d'entités de chaque couche SIG chargée (voir dict_sig, Partie 2).
_gdf_EEE_charge = gdf_EEE


# ════════════════════════════════════════════════════════════════════════
# ÉTAPE 4 — COMPRÉHENSION DES DONNÉES D'ENTRÉE
# ════════════════════════════════════════════════════════════════════════

# ── FENÊTRE « COMPRENDRE VOS DONNÉES » : SUPPRIMÉE EN 26.9.0 ────────────
# Elle posait deux questions :
#   1. Source des points (CamAlien / autre) → source_points.
#      N'alimentait plus aucun calcul. Remplacée par la question de
#      conformité au protocole Albert 2017 (fenetre_mapping_colonnes_EEE),
#      qui est la vraie condition de calcul de la caractérisation.
#   2. Couche SI ROUTE oui / non → source_pr.
#      Utilisée par caracteriser_populations_EEE UNIQUEMENT pour calculer la
#      longueur des tronçons (dist_fin - dist_deb). Or ce module vérifie
#      lui-même la présence des colonnes dist_deb et dist_fin, et avertit si
#      elles manquent. On lui passe donc désormais source_pr='si_route' en
#      permanence : c'est la présence des colonnes qui décide.
#      Limite connue : une couche non SI ROUTE qui aurait des colonnes
#      nommées dist_deb / dist_fin avec un autre sens serait prise au mot.
# Le fichier fenetre_comprendre_donnees.py peut être retiré de 00_fonctions/.


# ── ÉTAPE 4 — SÉLECTION DES ESPÈCES ─────────────────────────────────────
# Le gestionnaire choisit les espèces à analyser (4 principales par défaut).
_res_especes = fenetre_selection_especes.fenetre_selection_especes()

if _res_especes["annule"]:
    raise SystemExit("SPRINGE annulé par l'utilisateur à l'étape 4 (sélection des espèces).")

especes_retenues = _res_especes["especes"]   # ex. ['Renouees', 'Ailante', ...]
print(f"✔️  Espèces analysées : {especes_retenues}")


# ----------------------------------------------------------
# ÉTAPE 4 (suite) — Mapping des noms d'espèces EEE
# ----------------------------------------------------------
# DÉPLACÉ EN 26.9.0 depuis l'ancienne section 3.0 (Partie 3), pour que
# toutes les questions soient posées avant le récapitulatif.
#
# Fenêtre interactive : demande d'abord quelle colonne de gdf_EEE contient
# le nom d'espèce, puis la correspondance de chaque valeur trouvée vers une
# des 5 espèces cibles SPRINGE. Remplace l'ancien mapping.mapping(gdf_EEE)
# qui était figé en dur sur la colonne 'plante'.
#
# PLACÉ AVANT le filtrage des espèces retenues : le filtrage a besoin de la
# colonne 'species_name_sci' pour rester valable sur une couche EEE dont la
# colonne d'espèce ne s'appelle pas 'plante'.

_ETAPE_COURANTE = "Mapping des noms d'espèces EEE"

gdf_EEE_mapping, _colonne_espece_source, _mapping_especes_valeurs = (
    fenetre_mapping_especes.mapping_interactif_especes(gdf_EEE)
)

# On repart de gdf_EEE_mapping pour la suite du pipeline : c'est cette
# version, porteuse de la colonne 'species_name_sci', qui doit être utilisée
# par le filtrage ci-dessous ET par tout le reste du script (jointure
# tronçons, calcul des indicateurs...).
gdf_EEE = gdf_EEE_mapping


# ----------------------------------------------------------
# Filtrage des espèces retenues par le gestionnaire
# ----------------------------------------------------------
# DÉPLACÉ EN 26.9.0 depuis l'ancienne section 3.1.
#
# On retire de gdf_EEE les points des espèces non cochées. Fait sur la
# colonne 'species_name_sci' (issue du mapping ci-dessus) : les codes
# renvoyés par fenetre_selection_especes ('Renouees', 'Ailante'...) désignent
# un référentiel FIXE de 5 espèces cibles, indépendant de la structure de la
# couche EEE fournie -- il faut donc les traduire avant de filtrer.
#
# POURQUOI ICI, entre le mapping et la conformité : la fenêtre de
# conformité et le contrôle des modalités doivent porter sur les points
# qui seront réellement traités.

_ETAPE_COURANTE = "Filtrage des espèces retenues"

# Traduction des codes de sélection vers species_name_sci.
# .get(code, code) : un code inconnu (ne devrait pas arriver) est laissé tel
# quel plutôt que de planter -- il ne matchera simplement aucune ligne.
especes_retenues_sci = [
    fenetre_mapping_especes.CODES_SELECTION_VERS_SCI.get(code, code)
    for code in especes_retenues
]

_nb_avant_filtre = len(gdf_EEE)
gdf_EEE = gdf_EEE[gdf_EEE["species_name_sci"].isin(especes_retenues_sci)].copy()
_nb_retire = _nb_avant_filtre - len(gdf_EEE)

if _nb_retire > 0:
    print(f"✔️  Filtrage espèces : {_nb_retire} point(s) retiré(s) "
          f"({len(gdf_EEE)} conservé(s) sur {_nb_avant_filtre}).")
    _WARNINGS_SPRINGE.append(
        f"Sélection espèces : {_nb_retire} point(s) EEE écarté(s) "
        f"(espèces non retenues : hors de {especes_retenues})."
    )

# Garde-fou : si le filtrage ne laisse aucun point, SPRINGE n'a rien à
# scorer. Depuis 26.9.0, message à l'écran (et plus seulement en console).
if len(gdf_EEE) == 0:
    _arret_springe(
        "Aucun point EEE retenu",
        "Aucun point EEE ne correspond aux espèces sélectionnées.\n\n"
        "Vérifiez la correspondance des espèces ou élargissez la sélection."
    )


# ----------------------------------------------------------
# ÉTAPE 4 (suite) — Paramétrage de la caractérisation des populations EEE
# ----------------------------------------------------------
# DÉPLACÉ EN 26.9.0 depuis l'ancienne section 3.1bis.
#
# Deux questions posées au gestionnaire, en une seule fenêtre à deux écrans :
#   1. Vos données suivent-elles le protocole national de recensement
#      (Albert, A. coord. 2017, FCBN) ?
#   2. Si oui, quelle colonne de VOTRE couche porte chaque information
#      attendue (largeur, longueur, compacité, abscisse, ...) ?
#
# POURQUOI CETTE FENÊTRE EXISTE : le protocole normalise les VARIABLES et
# leurs MODALITÉS, pas les noms de colonnes des couches diffusées, qui
# varient selon la DIR, l'outil d'export et le millésime.
#
# CHOIX STRUCTURANT (CS-3) : si les données ne suivent PAS le protocole, la
# caractérisation n'est pas calculée du tout. Le reste de SPRINGE
# (indicateurs MS, N, P) n'est pas affecté.

_ETAPE_COURANTE = "Paramétrage de la caractérisation des populations EEE"

_caracterisation_active, _mapping_colonnes_EEE, _rapport_conformite_EEE = (
    fenetre_mapping_colonnes_EEE.mapping_interactif_colonnes_EEE(gdf_EEE)
)

if not _caracterisation_active:
    _WARNINGS_SPRINGE.append(
        "Caractérisation des populations EEE : non calculée "
        "(données non conformes au protocole Albert 2017, ou paramétrage "
        "non validé). Les indicateurs MS, N et P ne sont pas affectés."
    )


# ════════════════════════════════════════════════════════════════════════
# RÉCAPITULATIF AVANT DÉMARRAGE
# ════════════════════════════════════════════════════════════════════════
# Dernière vérification avant le calcul long. Boutons « Lancer SPRINGE »
# ou « Annuler SPRINGE ».

_ETAPE_COURANTE = "Récapitulatif avant démarrage"

# Traduction des codes d'espèces ('Renouees'…) en libellés lisibles
# ('Renouées asiatiques (Reynoutria sp.)'…), à partir du catalogue de la
# fenêtre de sélection : une seule source pour les libellés, aucune recopie.
_libelles_especes = {
    cle: libelle
    for cle, libelle, _coche_par_defaut in fenetre_selection_especes.ESPECES_CATALOGUE
}

_lancer = fenetre_recap.fenetre_recap(
    DIR                    = DIR,
    NOM                    = NOM,
    OUTPUT_DIR             = OUTPUT_DIR,
    colonne_id             = colonne_id_origine,   # nom CHOISI, pas le nom interne
    choix                  = choix,
    fichier_troncons       = fichier_troncons,
    fichier_emprise        = fichier_emprise,
    especes_retenues       = [_libelles_especes.get(c, c) for c in especes_retenues],
    # conforme_declare vaut True / False / None (None = fenêtre fermée sans répondre)
    conforme_protocole     = _rapport_conformite_EEE.get("conforme_declare"),
    caracterisation_prevue = _caracterisation_active,
)

if not _lancer:
    raise SystemExit("SPRINGE annulé par l'utilisateur au récapitulatif.")

print("\n✅ Configuration validée — lancement du traitement SPRINGE...\n")



# ==========================================================
# 🔵 PARTIE 2 - CHARGEMENT DES DONNÉES D'ENTRÉE
# ==========================================================

# ----------------------------------------------------------
# 2.1 - Emprise et tronçons : DÉPLACÉ EN PARTIE 1 (26.9.0)
# ----------------------------------------------------------
# La construction de l'emprise et la lecture du réseau routier sont
# désormais faites juste après l'étape 2 du questionnaire (voir plus haut),
# car la fenêtre de l'identifiant a besoin des colonnes du réseau.
# Les objets `emprise` et `gdf_troncons` sont donc déjà disponibles ici.


# ----------------------------------------------------------
# 2.2 - Importer les couches SIG renseignées par l'utilisateur
# ----------------------------------------------------------
# Les chemins ont été collectés en Partie 1. Ici on charge effectivement
# chaque couche, filtrée sur l'emprise pour ne lire que les entités
# pertinentes (gain de temps et de mémoire sur les grosses couches).

_ETAPE_COURANTE = "Chargement des couches SIG utilisateur"
_fen = traitement_en_cours.traitement_en_cours("Chargement des couches d'entrée")

# Couches principales. Les GeoDataFrames sont injectés dans globals()
# sous leur nom de variable (gdf_carrefours…), d'où construire_data
# les récupérera ensuite.
#
# La valeur de retour est conservée dans `dict_sig` : c'est le dictionnaire
# {nom_couche: GeoDataFrame|None} attendu par generer_rapport_execution
# pour lister les couches SIG dans le rapport de fin d'exécution.
# (elle remplace l'ancien retour de import_sig_interne, module supprimé)
#
# 26.9.0 — gdf_EEE a DÉJÀ été lu en Partie 1 (étape 3), puis mappé et
# filtré. On le retire donc des chemins à charger : sinon
# charger_couches_utilisateur le relirait et l'injecterait dans globals(),
# ÉCRASANT la version mappée par une version brute sans species_name_sci.
_chemins_sans_EEE = {var: chemin for var, chemin in _chemins.items()
                     if var != "gdf_EEE"}

dict_sig = charger_couches_sig.charger_couches_utilisateur(
    chemins        = _chemins_sans_EEE,
    emprise        = emprise,
    espace_noms    = globals(),
    warnings_liste = _WARNINGS_SPRINGE,
)

# Couches ajoutées manuellement par l'utilisateur (thèmes MS1/MS2/MS3).
_couches_supp_chargees = charger_couches_sig.charger_couches_supplementaires(
    supp_par_bloc  = {"MS1": _supp_MS1, "MS2": _supp_MS2, "MS3": _supp_MS3},
    emprise        = emprise,
    espace_noms    = globals(),
    warnings_liste = _WARNINGS_SPRINGE,
)

# On complète dict_sig avec les couches supplémentaires, pour qu'elles
# apparaissent elles aussi dans le rapport. charger_couches_supplementaires
# ne renvoie que des NOMS de variables : on récupère les GeoDataFrames
# correspondants dans globals().
for _bloc, _noms_supp in _couches_supp_chargees.items():
    for _nom_supp in _noms_supp:
        dict_sig[_nom_supp] = globals().get(_nom_supp)

# 26.9.0 — On réintègre la couche EEE, en tête de dict_sig, pour qu'elle
# figure toujours dans le rapport d'exécution. On y met la couche TELLE
# QUE LUE (_gdf_EEE_charge) : le rapport compte les entités chargées, pas
# celles restantes après le filtrage des espèces.
dict_sig = {"gdf_EEE": _gdf_EEE_charge, **dict_sig}

_fen.destroy()

# gdf_tmja_P2 : même objet que gdf_tmja, déjà chargé ci-dessus.
# On ne relit pas le fichier — un alias suffit.
gdf_tmja_P2 = globals().get("gdf_tmja")


# ----------------------------------------------------------
# 2.3 - Importer l'excel des caractéristiques EEE
# ----------------------------------------------------------
# code qui permet l'import spécifique de la base de données EEE (excel) restructuration des données (lignes en colonnes, une ligne par EEE)

# Définition de base_dir
try:
    base_dir = Path(__file__).parent  # en script .py
except NameError:
    base_dir = Path.cwd()            # en notebook Jupyter

# Chemins dérivés
data = base_dir / "01_data"

# Dossier contenant le fichier des caractéristiques EEE.
# NB : le nom du dossier a changé (ancien nom : "PATH_EEE_SHEET"),
# et le nom du fichier .csv lui-même peut varier d'un export à l'autre
# (ex : renommé à chaque nouvelle extraction du tableur Excel source).
# On ne fige donc plus le nom du fichier en dur : on va chercher
# automatiquement le seul .csv présent dans ce dossier.
DOSSIER_EEE_SHEET = data / "CSV_fichier_excel_caracteristiques_eee"

# Vérifie d'abord que le dossier existe bien (is_dir=True) avant d'aller
# chercher un fichier à l'intérieur : évite un message d'erreur confus
# si c'est le dossier lui-même qui est absent/mal nommé.
check_path.check_path(DOSSIER_EEE_SHEET, "Dossier CSV caractéristiques EEE", is_dir=True)

# .glob("*.csv") renvoie un générateur listant tous les fichiers se terminant
# par .csv dans le dossier ; list(...) le transforme en liste manipulable.
fichiers_csv_trouves = list(DOSSIER_EEE_SHEET.glob("*.csv"))

# Cas 1 : aucun fichier .csv trouvé --> on arrête le script proprement avec
# un message clair plutôt que de laisser pandas planter plus loin sur un
# chemin inexistant.
if len(fichiers_csv_trouves) == 0:
    raise FileNotFoundError(
        f"Aucun fichier .csv trouvé dans {DOSSIER_EEE_SHEET}. "
        "Merci d'y placer le fichier des caractéristiques EEE."
    )
# Cas 2 : plusieurs fichiers .csv trouvés --> ambigu, on ne devine pas
# lequel utiliser, on arrête le script en listant les fichiers en cause.
elif len(fichiers_csv_trouves) > 1:
    noms = ", ".join(f.name for f in fichiers_csv_trouves)
    raise FileNotFoundError(
        f"Plusieurs fichiers .csv trouvés dans {DOSSIER_EEE_SHEET} ({noms}). "
        "Le dossier doit contenir un seul fichier .csv (celui des caractéristiques EEE)."
    )

# Cas 3 (nominal) : un seul fichier .csv trouvé --> on le sélectionne.
# [0] : on prend le premier (et unique, cf. vérifications ci-dessus) élément de la liste
PATH_EEE_SHEET = fichiers_csv_trouves[0]
print(f" -> Fichier EEE sheet détecté automatiquement : {PATH_EEE_SHEET.name}")

check_path.check_path(PATH_EEE_SHEET, "EEE sheet")


# ---------------------------------------
# 2.3.1. Charger le fichier XL EEE_sheet
print("\nChargement base de données XL espèces EEE ... ")
print("-" * 80)


"""
Structure du fichier EEE_sheet.csv :
Contient les caractéristiques biologiques de chaque EEE référencée.
Format initial : variables en lignes, espèces en colonnes
Format souhaité pour analyse : espèces en lignes, variables en colonnes (=format tidy)

Transformation nécessaire :
    - transposition du tableau (lignes <-> colonnes)
    - mettre les noms d'espèces en index
"""

# Chargement du CSV
EEE_SHEET_original = pd.read_csv(PATH_EEE_SHEET, #pd.read_csv lit les fichiers CSV dans un DataFrame pandas
                        sep=',',
                        encoding='latin1') # encodage des caractères spéciaux français
# si PATH_EEE_SHEET est au format XLSL --> pd.read_excel(PATH_EEE_SHEET)

print(f" -> {len(EEE_SHEET_original)} lignes chargées") # f" = f-string (écrire une chaine de caractères depuis une variable = insérer des variables directement dans le texte)
print(f" -> {len(EEE_SHEET_original.columns)} colonnes détectées")
print("\n Chargement terminé")

# ---------------------------------------
# 2.3.2. Transormation du tableau (=pivotlonger)

EEE_test = EEE_SHEET_original.drop(columns=["description_variable", "Enjeu"])

# Étape 1 : Identifier les colonnes
variables = ["Variables"]
# Les colonnes d'espèces commencent à partir de "value" (colonne 4)
species_cols = EEE_test.columns[1:]  # De la 5e colonne jusqu'à la fin (pcq la colonne n°1 = 0 dans python)

print(f"Colonnes de métadonnées : {variables}")
print(f"Colonnes d'espèces détectées : {list(species_cols)}")

# Étape 2 : Transposer uniquement les colonnes d'espèces
# On garde "variable" comme index, on transpose les espèces
EEE_caracterisques_excel = (
    EEE_test
    .set_index('Variables')      # Mettre "variable" comme index
    [species_cols]              # Sélectionner uniquement les colonnes d'espèces
    .T                          # Transposer : espèces deviennent lignes
    .reset_index()              # Convertir l'index en colonne
    .rename(columns={'index': 'species_name'})  # Renommer la colonne
)

print(f"\n✓ Tableau transformé : {EEE_caracterisques_excel.shape[0]} espèces x {EEE_caracterisques_excel.shape[1]} variables")
print(f"✓ Espèces disponibles : {EEE_caracterisques_excel['species_name'].tolist()}")

# Afficher un aperçu
print("\nAperçu du tableau transformé :")
EEE_caracterisques_excel



# ----------------------------------------------------------
# 2.4 - Importer des données depuis des API
# ----------------------------------------------------------

# ══════════════════════════════════════════════════════════════════
# CATALOGUES DE COUCHES
# Format de chaque tuple : (nom_technique_wfs, variable_python, label)
# Le nom de variable DOIT correspondre à ce qu'attend get_gdf() plus bas
# dans le script — c'est le seul lien entre le chargement et DATA.
# ══════════════════════════════════════════════════════════════════

COUCHES_BDTOPO = [
    ("BDTOPO_V3:cours_d_eau",            "gdf_API_BDTOPO_cours_eau",   "Cours d'eau"),
    ("BDTOPO_V3:troncon_de_voie_ferree", "gdf_API_BDTOPO_voie_ferree", "Voies ferrées"),
]

COUCHES_IGN_BDCARTO = [
    ("BDCARTO_V5:zone_d_habitation",           "gdf_API_IGN_habitation_bdcarto",            "Zones d'habitation"),
    ("BDCARTO_V5:zone_d_activite_ou_d_interet","gdf_API_IGN_zone_activite_interet_bdcarto", "Zones d'activité"),
    # NOTE — cours d'eau BDCarto retiré : doublon avec BD TOPO cours_d_eau,
    # seule source utilisée par P2 (hydrochorie). On évite de télécharger
    # deux fois la même information.
]

COUCHES_INPN = [
    # Natura 2000
    ("Sites_d_importance_communautaire_JOUE__ZSC_SIC_", "gdf_API_INPN_SIC",  "SIC (ZSC/SIC)"),
    ("Zones_de_protection_speciale",                    "gdf_API_INPN_ZPS",  "ZPS"),
    ("ZICO",                                            "gdf_API_INPN_ZICO", "ZICO"),
    # Réserves naturelles
    ("Parcs_nationaux",                        "gdf_API_INPN_Parcs_Nationaux",     "Parcs Nationaux"),
    ("Reserves_Naturelles_Nationales",         "gdf_API_INPN_RNN",                 "RNN"),
    ("Reserves_naturelles_regionales",         "gdf_API_INPN_RNR",                 "RNR"),
    ("Reserves_Integrales_de_Parcs_Nationaux", "gdf_API_INPN_RIPN",                "RIPN"),
    ("Reserves_biologiques",                   "gdf_API_INPN_Reserves_Biologiques","Réserves Biologiques"),
    ("Perimetre_de_protection_dune_reserve_naturelle_nationale",
                                               "gdf_API_INPN_Perimetre_RNN",       "Périmètre RNN"),
    # Aires protégées
    ("Arretes_de_protection_d_habitats_naturels", "gdf_API_INPN_ArreteProtectionHabNat",  "Arrêté Protection Habitats Nat."),
    ("Arretes_de_protection_de_biotope",          "gdf_API_INPN_ArreteProtectionBiotope", "Arrêté Protection Biotope"),
    ("Sites_Ramsar",                              "gdf_API_INPN_RAMSAR",                  "Sites RAMSAR"),
    ("Terrains_acquis_des_Conservatoires_des_espaces_naturels",
                                                  "gdf_API_INPN_CEN",                     "CEN"),
    ("Terrains_du_Conservatoire_du_Littoral",     "gdf_API_INPN_ConservatoireLittoral",   "Conservatoire du Littoral"),
]


# ══════════════════════════════════════════════════════════════════
# APPELS
# Une seule boucle pour les trois services : même fonction, mêmes
# garanties (bbox effective, pagination, encodage, erreurs isolées).
# ══════════════════════════════════════════════════════════════════

_ETAPE_COURANTE = "Chargement des couches API"

_SERVICES = [
    # (nom, endpoint, catalogue, version WFS, CRS d'interrogation)
    ("API BD TOPO",
     "https://data.geopf.fr/wfs/ows",
     COUCHES_BDTOPO, "2.0.0", 2154),

    ("API IGN BDCarto",
     "https://data.geopf.fr/wfs/ows",
     COUCHES_IGN_BDCARTO, "2.0.0", 2154),

    ("API INPN",
     "http://ws.carmencarto.fr/WFS/119/fxx_inpn",
     COUCHES_INPN, "1.1.0", 2154),
]

for _nom, _endpoint, _catalogue, _version, _epsg in _SERVICES:

    _ETAPE_COURANTE = f"Chargement {_nom}"

    # Barre de progression : une coche par couche.
    _fen = traitement_en_cours.traitement_en_cours(
        f"{_nom} — Chargement des données",
        total=len(_catalogue)
    )

    _resultats, _statut = appel_api.appel_api(
        nom_api        = _nom,
        endpoint       = _endpoint,
        couches        = _catalogue,
        emprise        = emprise,
        code_epsg      = _epsg,
        version        = _version,
        on_progress    = _fen.avancer,
        warnings_liste = _WARNINGS_SPRINGE,
    )

    # globals().update() crée les variables gdf_API_* dans l'espace de
    # noms du script, exactement comme le faisait globals()[var] = gdf.
    # get_gdf() les retrouvera ensuite lors de la construction de DATA.
    globals().update(_resultats)

    _API_STATUTS[_nom] = _statut
    _fen.destroy()


# ── Ponts SNCF : API REST classique, pas un WFS ───────────────────
# Pas de filtrage côté serveur possible : on télécharge l'export
# national puis on découpe sur l'emprise.
_ETAPE_COURANTE = "Chargement des ponts SNCF"

gdf_API_ponts_sncf, _API_STATUTS["API SNCF (ponts)"] = appel_api.appel_api_geojson(
    nom_api        = "API SNCF (ponts)",
    url            = "https://data.sncf.com/api/explore/v2.1/catalog/"
                     "datasets/liste-des-ponts-route/exports/geojson",
    emprise        = emprise,
    warnings_liste = _WARNINGS_SPRINGE,
)


# ----------------------------------------------------------
# Fenêtre utilisateur : les données sont chargées
#
# 26.9.0 — PLUS DE BOUTON OK. L'ancien messagebox bloquait le script
# jusqu'au clic : sans clic, les calculs ne démarraient jamais.
# message_temporaire (traitement_en_cours.py) affiche le message pendant
# DUREE_MESSAGE_CHARGEMENT_MS, se ferme seul, puis le script enchaîne
# directement sur les calculs.

DUREE_MESSAGE_CHARGEMENT_MS = 3000   # durée d'affichage (3 s) ; modifiable ici

traitement_en_cours.message_temporaire(
    titre    = "Chargement terminé !",
    message  = "Les données d'entrée sont correctement chargées !\n\n"
               "Traitement en cours… chaîne de calculs de SPRINGE, "
               "merci de patienter.",
    duree_ms = DUREE_MESSAGE_CHARGEMENT_MS,
)



# ----------------------------------------------------------
# 2.5 - Construction du dictionnaire DATA
# ----------------------------------------------------------
# DATA est le registre central : il dit à chaque indicateur quelles
# couches croiser avec les tronçons. Sa construction (450 lignes de
# métadonnées) vit désormais dans construire_data.py.
#
# globals() est passé en argument car les couches (gdf_carrefours…)
# vivent dans l'espace de noms de CE script. Un globals() appelé depuis
# le module renverrait l'espace du module, qui est vide.

_ETAPE_COURANTE = "Construction du dictionnaire DATA"

DATA = construire_data.construire_data(
    espace_noms           = globals(),
    couches_supp_chargees = _couches_supp_chargees,
    est_dir               = _est_dir,
    warnings_liste        = _WARNINGS_SPRINGE,
)

# Retirer de DATA les couches non fournies : les indicateurs les
# ignoreront au lieu de lever un ValueError en plein calcul.
DATA = diagnostic_couches.nettoyer_data(DATA, warnings_liste=_WARNINGS_SPRINGE)

# Contrôle du filtrage spatial des API : chaque couche est-elle bien
# restreinte à l'emprise ? Un ratio proche de 1 = filtrage effectif ;
# un ratio à trois chiffres = la France entière a été téléchargée.
diagnostic_couches.diagnostic_emprise(
    [n for n in list(globals()) if n.startswith("gdf_API_")],
    globals(),
    emprise,
)

# Notes de développement remontées par construire_data (il ne dépend pas
# de travaux.py, c'est ce script qui les affiche).
for _note in construire_data.NOTES_TRAVAUX:
    travaux.travaux(_note)

print("✔️  Dictionnaire DATA construit et nettoyé\n")


# ==========================================================
# 🔵 PARTIE 3 - PREPARATION CALCULS SPRINGE
# ==========================================================

# ----------------------------------------------------------
# 3.0 / 3.1 / 3.1bis - DÉPLACÉES EN PARTIE 1 (26.9.0)
# ----------------------------------------------------------
# Le mapping des noms d'espèces, le filtrage des espèces retenues et le
# paramétrage de la caractérisation des populations EEE sont désormais
# faits pendant l'étape 4 du questionnaire, AVANT le récapitulatif.
# Motif : poser toutes les questions au début du run, plutôt qu'après
# plusieurs minutes de chargement des API.
#
# À ce stade, sont donc déjà disponibles :
#   gdf_EEE                  mappé (species_name_sci) et filtré
#   especes_retenues_sci     espèces retenues
#   _caracterisation_active, _mapping_colonnes_EEE, _rapport_conformite_EEE
# ----------------------------------------------------------
# 3.2 - Lier les PR avec les points de présence EEE
# ----------------------------------------------------------

#Les indicateurs fonctionnent par le calcul/définition des points de présence EEE rattachés à un PR/tronçon.
#Objectif : réaliser cette action une seule fois en amont du calcul des indicateurs

# ---------------------------------------
# 3.3.1. Nettoyage de gdf_troncons (PR)
"""
**WARNING**
dans gdf_troncons, y'a plusieurs polygones pour le même troncon, avec le meme identifiant nom_plo_fi
Je dois régler cà soit en :
option A : fusionnant tous les polygones qui ont le même nom_plo_fi
option B : attribué une lettre a,b,c etc. à l'identifiant pour les caractériser indépendement
--> question à régler selon les modalités de gestion des DIR
"""
#on va travailler avec la copie de gdf_troncon (=gdf_troncons_copy) pour tout le projet afin de ne pas modifier la couche initiale

# ── Appel sur gdf_troncons_copy ───────────────────────────────────────────────
_ETAPE_COURANTE = "Déduplication des tronçons"
gdf_troncons_copy = deduplication_troncons.deduplication_troncons(
    gdf_troncons  = gdf_troncons,
    colonne_id    = colonne_id,
    mode          = 'fusion'    # ← 'fusion' ou 'suffixe'
)

# ---------------------------------------
# 3.3.2. Attribuer les points EEE à un troncon
# utiliser la fonction
_ETAPE_COURANTE = "Attribution des points EEE aux tronçons (jointure spatiale)"
gdf_EEE = join_num_troncon_a_gdf_EEE.join_num_troncon_a_gdf_EEE(
    gdf_points = gdf_EEE, 
    gdf_polygones = gdf_troncons_copy, 
    colonne_id = colonne_id)

#vérifier le résultat obtenu
print(gdf_EEE[[colonne for colonne in gdf_EEE.columns if colonne != 'geometry']].head())
print(f"\nNombre de points avec tronçon: {(gdf_EEE['nom_plo_fi'] != 'NA').sum()}")
print(f"Nombre de points sans tronçon: {(gdf_EEE['nom_plo_fi'] == 'NA').sum()}")
   
 
# ----------------------------------------------------------
# 3.3 - Créer l'objet scoring
# ----------------------------------------------------------
# on créé l'objet scoring qui va contenir pour chaque troncon les points et scores indicateurs


# utiliser la fonction creer_objet_scoring pour créer l'objet
df_scoring = creer_objet_scoring.creer_objet_scoring(gdf_troncons_copy)
print("\nStructure de l'objet de scoring :")
print(df_scoring.head())



# ==========================================================
# 🔵 PARTIE 4 - CALCULS INDICATEURS SPRINGE
# ==========================================================

"""
La fonction 'detecter_elements_sur_troncon' est utilisée pour le calcul de nombreux indicateurs, 
elle est générique en se basant sur des dictionnaires contenant les couches de données à analyser 
pour chaque indicateur.
La fonction aboutie à une nouvelle colonne par couche dans gdf_troncons, 
avec oui/non (indication présence/absence)
"""

# ──────────────────────────────────────────────────────────────────────
# TAMPONS DE DÉTECTION — deux notions distinctes à ne pas confondre
# ──────────────────────────────────────────────────────────────────────
# 1. MARGE D'ERREUR (tolérance) — TAMPON_TOLERANCE_M
#    Absorbe le décalage de numérisation entre les couches. Les carrefours,
#    murs, etc. (SI ROUTE / RRNnc) sont censés être calés sur le réseau,
#    mais ne coïncident jamais au centimètre près avec l'axe des tronçons.
#    Sans marge, un 'intersects' strict les rate → sous-détection silencieuse.
#    Cette marge s'applique à TOUS les indicateurs : c'est la précision
#    commune qui rend leur fonctionnement cohérent entre eux.
#
# 2. DISTANCE SÉMANTIQUE — propre à chaque indicateur
#    Elle EST la définition de l'indicateur, et diffère volontairement :
#       MS2 (aires de repos)         : 200 m — public à proximité
#       N1 limitrophe                :  50 m — zone naturelle bordant la route
#       N1 proximité / P3            : 200 m — zone naturelle dans les environs
#       P2 (cours d'eau)             :  50 m — vecteur hydrochore au contact
#    Ces valeurs ne doivent PAS être uniformisées : les rendre égales
#    ferait perdre le sens (ex. N1 distingue « bordant » de « proche »).
#
# Règle appliquée : tampon effectif = max(distance_sémantique, TAMPON_TOLERANCE_M)
# → les indicateurs « sur réseau » (MS1, MS3), sans distance sémantique,
#   utilisent la seule marge de tolérance ; les autres gardent leur distance
#   (toutes ≥ 50 m, donc déjà supérieures à la marge).
TAMPON_TOLERANCE_M = 10


    # ======================================================
    # 🔵 ENJEU Maintenance et Sécurité (MS)
    # ======================================================
    #Objectif : Préserver la sécurité des usagers, protéger leur santé et maintenir l'intégrité du patrimoine routier.

# ----------------------------------------------------------
# MS1 - Impact des EEE sur la visibilité critique
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur MS1 - Visibilité critique"

# GARDE-FOU — Si aucune zone critique (carrefours, échangeurs…) n'a été
# fournie, la VULNÉRABILITÉ vaut 'non' partout, mais l'IMPACT reste
# calculé : il dépend des EEE (toujours présentes), pas des zones
# critiques. On neutralise donc uniquement la vulnérabilité, sans sauter
# le calcul d'impact plus bas.
if diagnostic_couches.indicateur_calculable(DATA, "MS", "MS1", _WARNINGS_SPRINGE):
    # *** détection des éléments d'intérêt sur les tronçons
    gdf_troncons_copy, stats_zones_critiques = detecter_elements_sur_troncon.detecter_elements_sur_troncon(
        gdf_PR=gdf_troncons_copy,
        dict_couches=DATA["MS"]["MS1"],
        nom_categorie='zones_visibilite_critique',
        mode = 'count',
        tampon = TAMPON_TOLERANCE_M   # marge d'erreur (calage SI ROUTE)
    )

    print(stats_zones_critiques)

    # *** calcul de la vulnérabilité des tronçons vis à vis de l'indicateur
    # il faut executer la fonction en direct pour ne pas écraser l'objet df_scoring
    calculer_vulnerabilite_facon1.calculer_vulnerabilite_facon1(
        gdf_analyse=gdf_troncons_copy,  # Votre GeoDataFrame (peu importe son nom)
        df_scoring=df_scoring,          # Votre DataFrame de scoring
        dict_couches=DATA["MS"]["MS1"],  # Le dictionnaire qui contient tout
        indicateur = 'MS1',
        methode= 'seuil'                 # La méthode recommandée
    )
else:
    # Aucune zone critique : tous les tronçons non vulnérables.
    df_scoring['MS1_vulnerabilite'] = 'non'
 
# Vérifier le résultat
print("\n✅ Colonne 'MS1_vulnerabilite' ajoutée au DataFrame de scoring :")
print(df_scoring[['nom_plo_fi', 'MS1_vulnerabilite']].head(20))

# Statistiques finales
print(f"\n📊 Statistiques MS1_vulnerabilite :")
print(df_scoring['MS1_vulnerabilite'].value_counts())
print(f"\nPourcentage de tronçons vulnérables : {round((df_scoring['MS1_vulnerabilite'] == 'oui').sum() / len(df_scoring) * 100, 1)}%")

# *** calcul de l'impact des EEE sur les tronçons pour l'indicateur
# utilisation de la fonction calculer_MS1_impact
        # Calcul de l'impact des EEE sur les troncons pour l'indicateur MS1 - visibilité critique
        # Logique : attribuer des points dans df_scoring<MS1_impact selon les conditions dans le troncon

df_scoring = calculer_MS1_impact.calculer_MS1_impact(gdf_EEE, EEE_caracterisques_excel, df_scoring)
print(df_scoring[['nom_plo_fi', 'MS1_vulnerabilite', 'MS1_impact']].head(20))

# ----------------------------------------------------------
# Seuil « fort trafic » commun à MS1b et P2 (mode Q3)
# ----------------------------------------------------------
# MODIFICATION 2026-09-28. Avant : MS1b recevait un seuil fixe écrit ici en
# dur (22 650 véh/j) et P2 recalculait de son côté le troisième quartile.
# Deux seuils pour une même notion rendaient MS1b et P2 incohérents.
#
# Décision : le mode Q3 s'applique PARTOUT. Le seuil est calculé UNE SEULE
# FOIS ici, puis transmis aux deux indicateurs.
#
# Principe du Q3 : c'est la valeur sous laquelle se trouvent 75 % des
# valeurs de TMJA de la zone traitée (la couche TMJA est déjà recadrée sur
# l'emprise au chargement). « TMJA > Q3 » désigne donc ~25 % des sections
# les plus chargées de LA zone, que la DIR soit rurale ou périurbaine.
# Limite assumée : le seuil est relatif à la zone, il change d'une exécution
# à l'autre. Il est donc écrit dans le rapport d'exécution (rubrique
# avertissements, ligne « Information — seuil fort trafic... »).
#
# _infos_tmja vaut None si :
#   - aucune couche TMJA n'a été fournie (donnée optionnelle) ;
#   - la couche n'a pas de colonne de trafic reconnue ;
#   - la colonne ne contient aucune valeur numérique.
# Dans ces trois cas, MS1b et le bonus TMJA de P2 sont neutralisés (0).
#
# globals().get("gdf_tmja") plutôt que gdf_tmja : renvoie None au lieu de
# lever une NameError si la variable n'a jamais été créée.

_ETAPE_COURANTE = "Calcul du seuil TMJA commun (Q3)"

_infos_tmja = calculer_seuil_tmja.calculer_seuil_tmja_q3(
    gdf_tmja             = globals().get("gdf_tmja"),
    liste_avertissements = _WARNINGS_SPRINGE,   # trace le seuil dans le rapport
)


# ----------------------------------------------------------
# MS1 b - Exposition des usagers liée au trafic
# ----------------------------------------------------------
# ⚠️ MS1b reçoit gdf_tmja en ARGUMENT DIRECT, pas via DATA : il échappe
# donc au filet de nettoyer_data(). Le garde-fou ci-dessous évite
# « AttributeError: 'NoneType' object has no attribute 'columns' » après
# ~20 min de calcul. Depuis 2026-09-28, on teste _infos_tmja (et non plus
# seulement gdf_tmja) : une couche fournie mais inexploitable (pas de
# colonne de trafic, que des « ND ») est aussi neutralisée proprement.

_ETAPE_COURANTE = "Calcul indicateur MS1b - Exposition au trafic"

if _infos_tmja is not None:
    df_scoring = calculer_MS1b_impact.calculer_MS1b_impact(
        gdf_troncons = gdf_troncons_copy,
        gdf_tmja     = gdf_tmja,
        df_scoring   = df_scoring,
        seuil_trafic = _infos_tmja["seuil"],    # Q3 de la zone (commun avec P2)
        col_tmja     = _infos_tmja["colonne"],  # même colonne que P2
    )
    print(df_scoring[['nom_plo_fi', 'MS1_vulnerabilite', 'MS1b_impact']].head(20))
else:
    # Pas de seuil calculable : on neutralise l'indicateur plutôt que de
    # planter. La colonne est créée à 0 pour que calculer_score_final (qui
    # détecte les colonnes *_impact dynamiquement) reste cohérent, et pour
    # éviter un KeyError sur les affichages en aval.
    print("⚠️  MS1b non calculé : aucune donnée TMJA exploitable.")
    _WARNINGS_SPRINGE.append(
        "MS1b non calculé — TMJA absent ou inexploitable (indicateur neutralisé à 0)"
    )
    df_scoring['MS1b_impact'] = 0



# ----------------------------------------------------------
# MS2 - Risque sanitaire
# ----------------------------------------------------------
# RÉACTIVÉ dans cette version (il était encadré par des triple-quotes,
# donc jamais exécuté : l'enjeu MS était scoré SANS MS2).
#
# Garde-fou : si aucune des couches d'accueil du public (aires de repos,
# gares…) n'a été fournie, DATA["MS"]["MS2"] est vide après nettoyage.
# On saute alors l'indicateur au lieu de calculer sur du vide.

if diagnostic_couches.indicateur_calculable(DATA, "MS", "MS2", _WARNINGS_SPRINGE):

    # ----------------------------------------------------------
    # MS2 - Risque sanitaire
    # ----------------------------------------------------------

    _ETAPE_COURANTE = "Calcul indicateur MS2 - Risque sanitaire"
    # Appeler la fonction detecter_elements_sur_troncon
    gdf_troncons_copy, stats_risque_sanitaire = detecter_elements_sur_troncon.detecter_elements_sur_troncon(
        gdf_PR=gdf_troncons_copy,
        dict_couches = DATA["MS"]["MS2"],
        nom_categorie = 'risque_sanitaire',
        mode = 'count',
        tampon = 200)

    # calcul de la vulnérabilité des tronçons vis à vis de MS2
    # il faut executer la fonction en direct pour ne pas écraser l'objet df_scoring
    calculer_vulnerabilite_facon1.calculer_vulnerabilite_facon1(
        gdf_analyse=gdf_troncons_copy,  # Votre GeoDataFrame (peu importe son nom)
        df_scoring=df_scoring,          # Votre DataFrame de scoring
        dict_couches=DATA["MS"]["MS2"],  # Le dictionnaire qui contient tout
        indicateur = 'MS2',
        methode= 'seuil'                 # La méthode recommandée
    )

    # Vérifier le résultat
    print("\n✅ Colonne 'MS2_vulnerabilite' ajoutée au DataFrame de scoring :")
    print(df_scoring[['nom_plo_fi', 'MS2_vulnerabilite']].head(20))

    # Statistiques finales
    print(f"\n📊 Statistiques MS2_vulnerabilite :")
    print(df_scoring['MS2_vulnerabilite'].value_counts())
    print(f"\nPourcentage de tronçons vulnérables : {round((df_scoring['MS2_vulnerabilite'] == 'oui').sum() / len(df_scoring) * 100, 1)}%")

    # Calcul de Impact MS2 : Impact des EEE (pouvoir allergène) sur les zones d'exposition des usagers de la route

    travaux.travaux("revoir mapping espèces à une place plus pertinente")

    df_scoring = calculer_MS2_impact.calculer_MS2_impact(
        gdf_EEE = gdf_EEE, 
        EEE_caracterisques_excel = EEE_caracterisques_excel,
        df_scoring = df_scoring)
    print(df_scoring[['nom_plo_fi', 'MS2_vulnerabilite', 'MS2_impact']].head(20))

else:
    # Indicateur non calculable : colonnes neutres pour ne pas casser
    # les affichages et le score final en aval.
    df_scoring['MS2_vulnerabilite'] = 'non'
    df_scoring['MS2_impact'] = 0


# ----------------------------------------------------------
# MS3 : Menace des EEE sur la préservation des infrastructures routière
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur MS3 - Patrimoine routier"

# GARDE-FOU — même logique que MS1 : sans couche de patrimoine (murs,
# ponts…), la vulnérabilité vaut 'non' partout, mais l'impact EEE reste
# calculé plus bas.
if diagnostic_couches.indicateur_calculable(DATA, "MS", "MS3", _WARNINGS_SPRINGE):
    # détection des éléments d'intérêt
    gdf_troncons_copy, stats_patrimoine = detecter_elements_sur_troncon.detecter_elements_sur_troncon(
        gdf_PR=gdf_troncons_copy,
        dict_couches = DATA["MS"]["MS3"],
        nom_categorie = 'patrimoine',
        mode = 'count',
        tampon = TAMPON_TOLERANCE_M)   # marge d'erreur (calage RRNnc)

    # calcul de la vulnérabilité des tronçons vis à vis de l'indicateur MS3
    # il faut executer la fonction en direct pour ne pas écraser l'objet df_scoring
    calculer_vulnerabilite_facon1.calculer_vulnerabilite_facon1(
        gdf_analyse=gdf_troncons_copy,  # Votre GeoDataFrame (peu importe son nom)
        df_scoring=df_scoring,          # Votre DataFrame de scoring
        dict_couches=DATA["MS"]["MS3"],  # Le dictionnaire qui contient tout
        indicateur = 'MS3',
        methode= 'seuil'                 # La méthode recommandée
    )
else:
    df_scoring['MS3_vulnerabilite'] = 'non'

# Vérifier le résultat
print("\n✅ Colonne 'MS3_vulnerabilite' ajoutée au DataFrame de scoring :")
print(df_scoring[['nom_plo_fi', 'MS3_vulnerabilite']].head(20))

# Statistiques finales
print(f"\n📊 Statistiques MS3_vulnerabilite :")
print(df_scoring['MS3_vulnerabilite'].value_counts())
print(f"\nPourcentage de tronçons vulnérables : {round((df_scoring['MS3_vulnerabilite'] == 'oui').sum() / len(df_scoring) * 100, 1)}%")

# calcul de l'impact des EEE par l'indicateur MS3
travaux.travaux("revoir mapping espèces à une place plus pertinente")

df_scoring = calculer_MS3_impact.calculer_MS3_impact(gdf_EEE, EEE_caracterisques_excel, df_scoring)


    # ======================================================
    # 🔵 ENJEU Environnement (N))
    # ======================================================
    # Objectif : Protéger la biodiversité et les milieux naturels adjacents à l'emprise routière de l'impact des EEE (temps t0)

# ----------------------------------------------------------
# N1 - Proximité et menace des EEE sur les zones naturelles sensibles
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur N1 - Zones naturelles sensibles"
# données SIG : dictionnaire de l'API INPN (couche des réserves naturelles nationales de INPN)

# détection des éléments d'intérêt sur le tronçon
    # ATTENTION : mécanisme quelque peu différent car dictionnaire en Niv -- concacenation de couches
'''
détection de la présence de zones naturelles protégées pour chaque troncon.

paramètres :

gdf_troncons : geodataframe polygones qui contient les PR
dict_couches_zone_naturelle : dictionnaire {nom_colonne : gdf_zone_naturelle}
    - nom_colonne : nom de la colonne à créer dans gdf_troncons
    - gdf_zone_naturelle : geodataframe du patrimoine (point ou lignes)

la fonction retourne :
 - un geodataframe avec colonne gdf_zone_naturelle, et oui/non le troncon est a coté de RNN
- dict avec statistiques d'affiliation
'''

# je veux des colonnes par niveau (et pas une colonne par couche)
# créer un dictionnaire avec les couches aggregees par niveau
# GARDE-FOU — N1 neutralisé si aucune couche fournie (sinon
# pd.concat([]) / détection sur dictionnaire vide lèverait une erreur).
if diagnostic_couches.indicateur_calculable(DATA, "N", "N1", _WARNINGS_SPRINGE):
    dict_zones_naturelles_agreggees = {}

    for niveau, sous_couches in DATA["N"]["N1"].items():
        #concaténer tous les GDF du niveau
        # On ne garde que les couches réellement présentes : un niveau
        # dont toutes les couches ont été retirées (déclarées absentes)
        # produirait pd.concat([]) → ValueError. On saute ce niveau.
        gdfs_niveau = [couche["gdf"] for couche in sous_couches.values()
                       if couche.get("gdf") is not None]
        if not gdfs_niveau:
            continue
        gdf_agrege = pd.concat(gdfs_niveau, ignore_index=True)

        dict_zones_naturelles_agreggees[niveau] = {
            "gdf": gdf_agrege,
            "type": "polygone",
            "source": "INPN API (aggrégé)",
            "description" : f"Agrégation de toutes des couches {niveau}"
        }
    
    #utiliser la fonction avec le dictionnaire agrégé
    gdf_troncons_copy, stats_zones_naturelles_limitrophes = detecter_elements_sur_troncon.detecter_elements_sur_troncon(
        gdf_PR=gdf_troncons_copy,
        dict_couches=dict_zones_naturelles_agreggees,
        nom_categorie='zones_naturelles_limitrophes',
        mode = 'count',
        tampon = 50
    )

    print(stats_zones_naturelles_limitrophes)

    travaux.travaux("voir comment gérer les niveauw d'aires naturelles protégées")

    # calcul vulnérabilité tronçons vis à vis de l'indicateur N1
    # il faut executer la fonction en direct pour ne pas écraser l'objet df_scoring
    calculer_vulnerabilite_facon1.calculer_vulnerabilite_facon1(
        gdf_analyse=gdf_troncons_copy,  # Votre GeoDataFrame (peu importe son nom)
        df_scoring=df_scoring,          # Votre DataFrame de scoring
        dict_couches=DATA["N"]["N1"],  # Le dictionnaire qui contient tout
        indicateur = 'N1',
        methode= 'seuil'                 # La méthode recommandée
    )

    # calcul impact EEE via indicateur N1
    df_scoring = calculer_N1_impact.calculer_N1_impact(
        gdf_EEE = gdf_EEE, #gdf_EEE_mapping
        gdf_troncons_copy = gdf_troncons_copy, 
        df_scoring = df_scoring)
    print(df_scoring[['nom_plo_fi', 'N1_vulnerabilite', 'N1_impact']].head(20))
else:
    df_scoring['N1_vulnerabilite'] = 'non'
    df_scoring['N1_impact'] = 0


# ----------------------------------------------------------
# N2 : Potentiel de transformation de l'habitat
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur N2 - Potentiel de transformation habitat"

'''
A noter : aucune espèce n'atteindra le score 5 (maximal = 6) sauf Reynoutria qui a les 3 transformations. 
Ailanthus plafonnera à 3 (modéré → N2_impact=3). 
C'est cohérent écologiquement — la Renouée est l'espèce la plus transformatrice des habitats en Europe.
'''

travaux.travaux("mapping gdf_EEE")
df_scoring = calculer_N2_impact.calculer_N2_impact(
    gdf_EEE = gdf_EEE, #gdf_EEE_mapping
    EEE_caracterisques_excel = EEE_caracterisques_excel, 
    df_scoring = df_scoring)

print(df_scoring[['nom_plo_fi', 'N2_impact']].head(20))

    # ======================================================
    # 🔵 ENJEU Propagation (P)
    # ======================================================

# ----------------------------------------------------------
# Indicateur P1 : Potentiel reproductif de l'EEE
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur P1 - Potentiel reproductif"

# on a pas besoin de faire une jointure spatiale avec gdf_troncons car on a deja l'info dans gdf_EEE grace à une jointure précédente
# pas de score de vulnérabilité (pas de sens)

#calcul de l'impact EEE par rapport à l'indicateur P1
df_scoring = calculer_P1_impact.calculer_P1_impact(gdf_EEE, #gdf_çEEE_mapping
                                EEE_caracterisques_excel, 
                                df_scoring, 
                                seuil_invasif=0.7)

print(df_scoring[['nom_plo_fi', 'P1_impact']].head(20))

# ----------------------------------------------------------
# Indicateur P2 : Proximité des vecteurs de dispersion des EEE
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur P2 — Vecteurs de dispersion"

# Calcul de l'impact P2.
# gdf_tmja_P2 est soit un GeoDataFrame (si l'utilisateur a fourni les données),
# soit None (si non disponible ou non sélectionné au moment de l'input utilisateur).
# La fonction gère les deux cas sans lever d'erreur.
# GARDE-FOU — P2 neutralisé si aucune couche fournie (sinon
# pd.concat([]) / détection sur dictionnaire vide lèverait une erreur).
if diagnostic_couches.indicateur_calculable(DATA, "P", "P2", _WARNINGS_SPRINGE):
    df_scoring = calculer_P2_impact.calculer_P2_impact(
        gdf_EEE       = gdf_EEE,
        gdf_troncons  = gdf_troncons_copy,
        df_scoring    = df_scoring,
        DATA_P2       = DATA["P"]["P2"],
        gdf_tmja      = gdf_tmja_P2,        # None si non fourni par l'utilisateur
        # 2026-09-28 : seuil et colonne COMMUNS avec MS1b, calculés une
        # seule fois plus haut (bloc « Seuil fort trafic commun »). Si
        # _infos_tmja est None (TMJA absent/inexploitable), on passe None :
        # P2 ignore alors le bonus TMJA (score max = 4) sans planter.
        seuil_tmja    = _infos_tmja["seuil"]   if _infos_tmja is not None else None,
        col_tmja      = _infos_tmja["colonne"] if _infos_tmja is not None else None,
        tampon_cours_eau = 50               # 50m autour des tronçons pour la détection cours d'eau
    )

    print(df_scoring[['nom_plo_fi', 'P2_impact']].head(20))
else:
    df_scoring['P2_impact'] = 0


# ----------------------------------------------------------
# Indicateur P3 : Proximité de zones naturelles sensibles à protéger de la colonisation
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur P3 - Proximité zones naturelles à protéger"

# détection des éléments d'intérêt :
    
# je veux des colonnes par niveau (et pas une colonne par couche)
# créer un dictionnaire avec les couches aggregees par niveau
# GARDE-FOU — P3 neutralisé si aucune couche fournie (sinon
# pd.concat([]) / détection sur dictionnaire vide lèverait une erreur).
if diagnostic_couches.indicateur_calculable(DATA, "P", "P3", _WARNINGS_SPRINGE):
    dict_zones_naturelles_proximite_agreggees = {}

    for niveau, sous_couches in DATA["P"]["P3"].items():
        #concaténer tous les GDF du niveau
        # On ne garde que les couches réellement présentes : un niveau
        # dont toutes les couches ont été retirées (déclarées absentes)
        # produirait pd.concat([]) → ValueError. On saute ce niveau.
        gdfs_niveau = [couche["gdf"] for couche in sous_couches.values()
                       if couche.get("gdf") is not None]
        if not gdfs_niveau:
            continue
        gdf_agrege = pd.concat(gdfs_niveau, ignore_index=True)

        dict_zones_naturelles_proximite_agreggees[niveau] = {
            "gdf": gdf_agrege,
            "type": "polygone",
            "source": "INPN API (aggrégé)",
            "description" : f"Agrégation de toutes des couches {niveau}"
        }
    
    #utiliser la fonction avec le dictionnaire agrégé
    gdf_troncons_copy, stats_zones_naturelles_proximite = detecter_elements_sur_troncon.detecter_elements_sur_troncon(
        gdf_PR=gdf_troncons_copy,
        dict_couches=dict_zones_naturelles_proximite_agreggees,
        nom_categorie='zones_naturelles_proximite',
        mode = 'count',
        tampon = 200
    )

    print(stats_zones_naturelles_proximite)


    calculer_vulnerabilite_facon1.calculer_vulnerabilite_facon1(
        gdf_analyse=gdf_troncons_copy,  # Votre GeoDataFrame (peu importe son nom)
        df_scoring=df_scoring,          # Votre DataFrame de scoring
        dict_couches=DATA["P"]["P3"],  # Le dictionnaire qui contient tout
        indicateur = 'P3',
        methode= 'seuil',                 # La méthode recommandée
    )

    df_scoring = calculer_P3_impact.calculer_P3_impact(
        gdf_EEE = gdf_EEE, 
        gdf_troncons_copy = gdf_troncons_copy, 
        df_scoring = df_scoring)
else:
    df_scoring['P3_vulnerabilite'] = 'non'
    df_scoring['P3_impact'] = 0

# ----------------------------------------------------------
# Indicateur P4 : Risque de colonisation des tronçons adjacents à enjeux
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul indicateur P4 - Colonisation tronçons adjacents"


df_scoring = calculer_P4_impact.calculer_P4_impact(
    gdf_EEE, # gdf-EEE-mapping
    gdf_troncons_copy,
    df_scoring)
print(df_scoring[['nom_plo_fi', 'P4_impact']].head(20))

# ==========================================================
# Scoring final par tronçon
# ----------------------------------------------------------

_ETAPE_COURANTE = "Calcul du score final par tronçon"
df_scoring = calculer_score_final.calculer_score_final(df_scoring)
print(df_scoring[['nom_plo_fi', 'score_enjeu_MS', 'score_enjeu_N', 'score_enjeu_P', 'score_troncon_final']].head(20))

'''
Niveau indicateur (coef_indicateurs) — pour différencier par exemple MS1 (visibilité, sécurité directe) de MS3 (patrimoine, impact différé).
Niveau enjeu (coef_enjeux) — pour hiérarchiser MS (sécurité usagers) > P (priorisation gestion) > N (biodiversité) selon la politique de ta DIR. Les deux niveaux sont multiplicatifs donc combinables librement.
'''

# ==========================================================
# Scoring final par tronçon
# ----------------------------------------------------------

# ----------------------------------------------------------
# Caractérisation des populations d'EEE
# ----------------------------------------------------------
# Remplace l'ancien calculer_densite_EEE (supprimé). Voir le document de
# cadrage v0.3 pour les motifs ; en résumé, l'ancienne logique sommait des
# rangs ordinaux (1 à 4) puis divisait par des kilomètres, opération non
# définie et dimensionnellement non homogène, et elle imputait les valeurs
# manquantes au plancher de classe, ce qui déplaçait la distribution.
#
# Le nouveau module ne produit AUCUN score, AUCUN rang, AUCUN adjectif de
# valeur : uniquement des comptages, des classes reprises telles quelles et
# des distances mesurées. Motif : l'information de colonisation alimente des
# décisions divergentes selon les gestionnaires (certains ciblent les foyers
# denses, d'autres les petits foyers isolés en front de colonisation). Un
# rang imposerait une lecture « plus haut = plus urgent » non fondée.
#
# Trois sorties :
#   - df_scoring enrichi des champs de SYNTHÈSE (statut_donnee,
#     nb_populations_total, nb_categories_presentes, synthese_EEE,
#     annee_releve_max) -> partiront dans la couche carto via
#     preparer_couche_gpkg, sans modification de ce dernier ;
#   - _df_caracterisation : la table LONGUE (tronçon × catégorie), écrite
#     plus bas dans le GeoPackage comme table attributaire sans géométrie ;
#   - _diagnostic_EEE : les chiffres de qualité, consommés par la notice.

_ETAPE_COURANTE = "Caractérisation des populations d'EEE"

# Valeurs par défaut : si la caractérisation n'a pas été activée pendant
# l'étape 4 du questionnaire (Partie 1), ces variables restent None et les
# blocs suivants les ignorent.
_df_caracterisation = None
_diagnostic_EEE = None

if _caracterisation_active:
    # Les catégories décrites sont celles que le gestionnaire a retenues dans
    # la fenêtre de sélection des espèces (Partie 1) : inutile de produire des
    # lignes pour des espèces qu'il a explicitement écartées.
    df_scoring, _df_caracterisation, _diagnostic_EEE = (
        caracteriser_populations_EEE.caracteriser_populations_EEE(
            gdf_EEE              = gdf_EEE,            # points déjà joints
            df_scoring           = df_scoring,
            gdf_troncons         = gdf_troncons_copy,  # copie dédupliquée
            mapping_colonnes     = _mapping_colonnes_EEE,
            categories_retenues  = especes_retenues_sci,
            colonne_id           = colonne_id,
            # 26.9.0 : valeur fixe, la fenêtre « Comprendre vos données »
            # étant supprimée. Avec 'si_route', le module calcule la longueur
            # des tronçons SI les colonnes dist_deb / dist_fin existent, et
            # avertit sinon : c'est la présence des colonnes qui décide.
            source_pr            = 'si_route',
            liste_avertissements = _WARNINGS_SPRINGE,
        )
    )
else:
    print("\nℹ️  Caractérisation des populations d'EEE : non calculée.")
    print("    Le GeoPackage ne contiendra ni les champs de synthèse, ni la")
    print("    table de caractérisation, ni la notice de lecture.")


# ==========================================================
# 🔵 PARTIE 5 - PRÉPARATION DE LA COUCHE GPKG FINALE
# ==========================================================

# -- Mémorisation pour le rapport --
_OUTPUT_DIR_RAPPORT = OUTPUT_DIR
_ETAPE_COURANTE = "Préparation de la couche GeoPackage finale et export"

# ─────────────────────────────────────────────────────────────────
# Préparation de la couche GeoPackage finale (descriptive/comparative)
# Remplace l'ancienne calculer_priorisation (cf. doc d'algorithme)
# ─────────────────────────────────────────────────────────────────
'''
df_scoring, gdf_priorisation = calculer_priorisation.calculer_priorisation(
    df_scoring        = df_scoring,
    gdf_troncons_copy = gdf_troncons_copy,
    name              = name,
    DIR               = DIR,
    output_dir        = OUTPUT_DIR
)

print(df_scoring[['nom_plo_fi', 'score_troncon_final',
                   'rang_priorite', 'annee_intervention']].head(20))
'''
# preparer_couche_gpkg renvoie désormais TROIS valeurs : le chemin réel du
# fichier écrit s'ajoute aux deux précédentes (ajout du 08/09/2026). Ce script
# n'a donc plus à reconstruire le nom de son côté — ce qu'il faisait jusqu'ici
# avec un commentaire « ⚠️ DOIT rester strictement cohérent », c'est-à-dire une
# duplication qu'il fallait maintenir à la main dans deux fichiers.
df_scoring, gdf_couche_finale, _chemin_fichier_sortie = (
    preparer_couche_gpkg.preparer_couche_gpkg(
        df_scoring        = df_scoring,
        gdf_troncons_copy = gdf_troncons_copy,
        name              = name,
        DIR               = DIR,
        output_dir        = OUTPUT_DIR,
        NOM               = NOM,
        date_reference    = _DATE_DEBUT_SPRINGE,
    )
)


# ----------------------------------------------------------
# Nom du GeoPackage produit
# ----------------------------------------------------------
# _chemin_fichier_sortie vient directement de preparer_couche_gpkg ci-dessus :
# c'est le chemin RÉELLEMENT écrit, plus une reconstruction à l'identique.
# On en dérive juste le nom court, utilisé dans la notice, le rapport
# d'exécution et le message de fin.
#
# Path.name donne le nom du fichier sans son dossier, Path.stem le même sans
# l'extension. _chemin_fichier_sortie peut être une chaîne (preparer_couche_gpkg
# utilise os.path.join), d'où le passage par Path() -- déjà importé en tête.
_chemin_fichier_sortie = Path(_chemin_fichier_sortie)
_nom_fichier_sortie    = _chemin_fichier_sortie.name
_nom_couche_sortie     = _chemin_fichier_sortie.stem


# ----------------------------------------------------------
# Ajout de la table de caractérisation au GeoPackage
# ----------------------------------------------------------
# preparer_couche_gpkg a écrit la couche cartographique (une ligne par
# tronçon, avec géométrie). Les champs de SYNTHÈSE de la caractérisation y
# sont déjà, puisqu'ils ont été ajoutés à df_scoring avant l'appel.
#
# Reste le DÉTAIL par (tronçon × catégorie) : 5 lignes par tronçon, donc
# impossible à loger dans une couche qui n'en a qu'une. On l'ajoute comme
# table attributaire SANS géométrie, ce que le standard GeoPackage prévoit
# explicitement. QGIS la charge via Couche > Ajouter une couche > Couche
# vecteur, et elle se joint à la couche carto par 'id_troncon'.
#
# POURQUOI PAS DES COLONNES SUFFIXÉES PAR ESPÈCE (choix structurant CS-16) :
# 5 catégories × ~14 métriques ≈ 70 colonnes, dont l'écrasante majorité vide
# ou nulle. Retrouver « combien de renouées sur ce PR » imposerait de faire
# défiler des dizaines de colonnes. Le champ 'synthese_EEE' de la couche
# carto compense le défaut de la table longue en donnant le résumé rédigé
# directement au clic, sans jointure.
#
# APPEL BLINDÉ : un échec ici ne doit pas faire perdre le GeoPackage, qui est
# déjà écrit à ce stade. Le module gère lui-même son repli en CSV.

if _caracterisation_active and _df_caracterisation is not None:
    _ETAPE_COURANTE = "Écriture de la table de caractérisation dans le GeoPackage"
    try:
        ecrire_table_caracterisation.ecrire_table_caracterisation(
            df_caracterisation   = _df_caracterisation,
            chemin_gpkg          = _chemin_fichier_sortie,
            liste_avertissements = _WARNINGS_SPRINGE,
        )
    except Exception as e:
        print(f"\n⚠️  Erreur lors de l'écriture de la table de caractérisation : {e}")
        print(f"    Le GeoPackage reste disponible : {_chemin_fichier_sortie}")
        _WARNINGS_SPRINGE.append(
            f"Table de caractérisation : écriture échouée — {str(e)[:100]}"
        )


# ----------------------------------------------------------
# Ajout de la couche harmonisée des populations au GeoPackage
# ----------------------------------------------------------
# AJOUT 2026-09-11. Troisième objet du GeoPackage : les points de populations
# d'EEE, avec des noms de colonnes et des modalités FIXES
# ('largeur', 'longueur', 'compacite'... valeurs 'Inf1m', 'Isoles', 'nr'...).
#
# POURQUOI : les styles QGIS désignent les colonnes par leur nom. La couche
# brute de chaque DIR a ses propres noms ('densite', 'localisati'...), donc un
# style construit sur l'une ne marcherait pas sur l'autre. Ici, on applique la
# correspondance déclarée par le gestionnaire dans les fenêtres de mapping
# (_mapping_colonnes_EEE, species_name_sci) et on écrit un résultat identique
# en structure pour toutes les DIR.
#
# CONDITION : caractérisation active. Sans elle, largeur / longueur / compacité
# ne sont pas identifiées et la couche n'aurait rien à représenter.
#
# CONTENU (détail dans le module) : une ligne par population (une population
# de bordure n'est pas dupliquée), populations hors tronçon exclues, colonnes
# facultatives toujours présentes (vides si non fournies).
#
# gdf_EEE est le même objet que celui passé à caracteriser_populations_EEE :
# mappé, filtré sur les espèces retenues, joint aux tronçons, et limité à
# l'emprise de la zone d'étude dès le chargement (couche recadrée : normal).
#
# crs_cible = système de la couche des tronçons écrite par
# preparer_couche_gpkg : les points sont reprojetés si besoin pour se
# superposer exactement dans QGIS.
#
# APPEL BLINDÉ : même logique que la table de caractérisation.

if _caracterisation_active:
    _ETAPE_COURANTE = "Écriture de la couche harmonisée des populations dans le GeoPackage"
    try:
        ecrire_couche_populations.ecrire_couche_populations(
            gdf_EEE              = gdf_EEE,
            mapping_colonnes     = _mapping_colonnes_EEE,
            chemin_gpkg          = _chemin_fichier_sortie,
            crs_cible            = gdf_couche_finale.crs,
            colonne_id           = colonne_id,
            liste_avertissements = _WARNINGS_SPRINGE,
        )
    except Exception as e:
        print(f"\n⚠️  Erreur lors de l'écriture de la couche des populations : {e}")
        print(f"    Le GeoPackage reste disponible : {_chemin_fichier_sortie}")
        _WARNINGS_SPRINGE.append(
            f"Couche des populations : écriture échouée — {str(e)[:100]}"
        )


# ----------------------------------------------------------
# Notice de lecture de la caractérisation
# ----------------------------------------------------------
# Fichier .txt régénéré à chaque exécution, spécifique à la zone traitée.
#
# POURQUOI (choix structurant CS-17) : ajouter des colonnes ne suffit pas à
# rendre l'information utilisable. Les définitions (population, compacité,
# pourquoi ce n'est PAS une densité), les hypothèses de calcul et surtout les
# taux de manquants de la zone concernée conditionnent l'interprétation.
#
# À NE PAS CONFONDRE avec 0_SPRINGE_presentation_algorithme.docx :
#   - le Word est la spécification de référence, stable : logique des calculs,
#     choix structurants, justification des seuils ;
#   - la notice répond à « comment lire MES résultats, et quelles précautions
#     prendre ? », avec les chiffres réels du run.
# Les seuils figurent dans les deux, mais leur justification reste dans le Word.
#
# APPEL BLINDÉ, même logique que le rapport d'exécution et les graphiques.

if _caracterisation_active and _diagnostic_EEE is not None:
    _ETAPE_COURANTE = "Génération de la notice de lecture"
    try:
        generer_notice_lecture.generer_notice_lecture(
            diagnostic           = _diagnostic_EEE,
            output_dir           = OUTPUT_DIR,
            name                 = name,
            DIR                  = DIR,
            nom_fichier_gpkg     = _nom_fichier_sortie,
            NOM                  = NOM,
            date_reference       = _DATE_DEBUT_SPRINGE,
            liste_avertissements = _WARNINGS_SPRINGE,
        )
    except Exception as e:
        print(f"\n⚠️  Erreur lors de la génération de la notice de lecture : {e}")
        _WARNINGS_SPRINGE.append(
            f"Notice de lecture : génération échouée — {str(e)[:100]}"
        )

"""
# Aperçu console : un échantillon des colonnes "synthèse" pour vérifier
# rapidement que le calcul s'est bien passé (scores agrégés + rangs)
print(df_scoring[['nom_plo_fi',
                  'score_enjeu_MS', 'rang_indicatif_MS',
                  'score_enjeu_N',  'rang_indicatif_N',
                  'score_enjeu_P',  'rang_indicatif_P',
                  'score_troncon_final', 'rang_indicatif_final']].head(20))
"""

# ==========================================================
# 🔵 RAPPORT D'EXÉCUTION FINAL
# ==========================================================

_ETAPE_COURANTE = "Génération du rapport d'exécution"
_DATE_FIN_SPRINGE = datetime.datetime.now()

# Construire le nom du fichier de sortie gpkg
# ⚠️ DOIT rester strictement cohérent avec ce qui est écrit
# par preparer_couche_gpkg.preparer_couche_gpkg (sinon le rapport
# pointera vers un fichier qui n'existe pas).

# ⚠️ DÉPLACÉ (2026-09-08) : ce bloc est désormais exécuté plus haut, juste
# après preparer_couche_gpkg. Motif : l'écriture de la table de
# caractérisation et la notice de lecture ont besoin de _chemin_fichier_sortie
# et s'exécutent avant le rapport. Les variables sont donc déjà définies ici.


"""
appel de la fonction generer_rapport_execution :
= généré à la fin d'une exécution réussie. Il produit un .txt avec :

    - Date, durée totale, DIR, opérateur, nom du projet
    - Mode de zone d'étude (Option 1 ou 2), fichier tronçons utilisé
    - Nb tronçons bruts → après déduplication
    - Nb points EEE total, associés à un tronçon, sans tronçon
    - Toutes les couches SIG internes : nom, nb entités, CRS
    - Statut API INPN / IGN / SNCF couche par couche (✔ ou ✘)
    - Scores moyens par enjeu (MS, N, P, score final)
    - Nom + chemin complet du fichier .gpkg de sortie
    - Avertissements non bloquants collectés pendant le run
"""

# ──────────────────────────────────────────────────────────────────────────
# APPEL BLINDÉ — génération du rapport d'exécution
# ──────────────────────────────────────────────────────────────────────────
# Si le rapport plante, on collecte l'erreur comme warning et on continue.
# Le gpkg est déjà écrit sur disque à ce stade : l'essentiel est fait.
#
# NOTE — les paramètres de generer_rapport_execution s'appellent
# `mode_emprise` et `fichier_troncons_path`. Un ancien « correctif » avait
# renommé les MOTS-CLÉS en `choix` / `fichier_troncons` pour coller aux
# variables du script : c'était l'inverse de ce qu'il fallait faire, puisque
# le nom du mot-clé doit correspondre à la SIGNATURE de la fonction, pas au
# nom de la variable qu'on lui passe. On rétablit les bons noms.

# 26.9.0 — _mode_emprise_libelle est désormais calculé en Partie 1, juste
# après la fenêtre de zone d'étude, pour que console, récapitulatif et
# rapport emploient exactement le même libellé.

try:
    generer_rapport.generer_rapport_execution(
        output_dir             = OUTPUT_DIR,
        name                   = name,
        DIR                    = DIR,
        NOM                    = NOM,
        gdf_troncons           = gdf_troncons,
        gdf_troncons_copy      = gdf_troncons_copy,
        colonne_id             = colonne_id,
        gdf_EEE                = gdf_EEE,
        dict_sig               = dict_sig,
        api_statuts            = _API_STATUTS,
        df_scoring             = df_scoring,
        chemin_fichier_sortie  = _chemin_fichier_sortie,
        nom_fichier_sortie     = _nom_fichier_sortie,
        date_debut             = _DATE_DEBUT_SPRINGE,
        date_fin               = _DATE_FIN_SPRINGE,
        mode_emprise           = _mode_emprise_libelle,
        fichier_troncons_path  = fichier_troncons,
        warnings_liste         = _WARNINGS_SPRINGE if _WARNINGS_SPRINGE else None,
        # 26.9.0 : nom de la variable identifiant choisie, affiché dans le
        # rapport à côté du nom interne 'nom_plo_fi'.
        colonne_id_origine     = colonne_id_origine,
    )
except Exception as e:
    print(f"\n⚠️  Erreur lors de la génération du rapport d'exécution : {e}")
    print(f"    Le fichier GeoPackage est quand même disponible : {_chemin_fichier_sortie}")
    _WARNINGS_SPRINGE.append(f"Rapport d'exécution : génération échouée — {str(e)[:100]}")

# ──────────────────────────────────────────────────────────────────────────
# APPEL BLINDÉ — génération des graphiques
# ──────────────────────────────────────────────────────────────────────────
# Si les graphiques plantent, on collecte l'erreur comme warning et on continue.
# Les graphiques sont un "nice to have", pas un bloquant.
try:
    generer_graphiques_plotly.generer_graphiques_plotly(
        df_scoring=df_scoring,
        gdf_EEE=gdf_EEE,
        colonne_id=colonne_id,
        output_dir=OUTPUT_DIR,
        # AJOUT 2026-09-28 — les paramètres ci-dessous existaient dans la
        # fonction mais n'étaient pas transmis par le lanceur :
        #   - name / DIR / NOM / date_reference : ligne de traçabilité en pied
        #     de chaque figure. Sans eux, le HTML affichait « exécuté le date
        #     non renseignée » et une figure copiée dans un rapport n'était
        #     plus rattachable à une exécution.
        name=name,
        DIR=DIR,
        NOM=NOM,
        date_reference=_DATE_DEBUT_SPRINGE,
        #   - df_caracterisation : table longue de la caractérisation. Sans
        #     elle, les figures « Ampleur » (3) et « Populations » (7) n'étaient
        #     JAMAIS produites, même quand la caractérisation était active, et
        #     le nuage (6) se rabattait sur le nombre de populations.
        #     Vaut None si la caractérisation est inactive : la fonction
        #     remplace alors ces deux figures par un message.
        df_caracterisation=_df_caracterisation,
        #   - liste_avertissements : figures non produites remontées dans la
        #     liste des avertissements (utile en console ; NB : le rapport
        #     d'exécution est écrit AVANT les graphiques, il ne les verra pas).
        liste_avertissements=_WARNINGS_SPRINGE,
    )
except Exception as e:
    print(f"\n⚠️  Erreur lors de la génération des graphiques : {e}")
    print(f"    Les graphiques n'ont pas pu être générés, mais le GeoPackage est disponible.")
    _WARNINGS_SPRINGE.append(f"Graphiques : génération échouée — {str(e)[:100]}")

# ----------------------------------------------------------
# Fenêtre utilisateur : les outputs sont téléchargés
# ----------------------------------------------------------

root = tk.Tk()
root.withdraw()

# Message avec f-string (⚠️ important pour afficher le chemin)
reponse = tk.messagebox.askyesno(
    "Téléchargement terminé !",
    f"Les fichiers SPRINGE sont disponibles ici :\n{_chemin_fichier_sortie}\n\n"
    "Voulez-vous ouvrir le dossier ?"
)

# Si OUI → ouvrir le dossier contenant le fichier
if reponse:
    dossier = os.path.dirname(_chemin_fichier_sortie)
    os.startfile(dossier)  # Windows uniquement

# Message final
tk.messagebox.showinfo(
    "Fin du programme",
    "Exécution de SPRINGE terminée.\nFermeture du programme."
)

# Fermeture propre
root.destroy()

print("\n✅ SPRINGE terminé avec succès.")

"""
FIN DU CODE DE SPRINGE
"""