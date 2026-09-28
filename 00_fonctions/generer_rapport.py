# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Fonction "generer_rapport"
Date : 2026-03-23
Objectif : Générer un rapport de fin d'exécution SPRINGE (.txt)
           ou un rapport d'incident en cas de crash
═══════════════════════════════════════════════════════════════════
"""

import datetime
import traceback
from pathlib import Path

# Nommage centralisé (2026-09-08) : ce module ne fabrique plus ses noms de
# fichiers lui-même, pour que rapport, incident, GeoPackage et notice
# suivent la même trame. Voir nommer_fichiers_sortie.py.
import nommer_fichiers_sortie

# ** Deux fonctions sont contenues dans ce .py**

# ** Fonction A :
# ──────────────────────────────────────────────────────────────────
# Rapport de fin d'exécution (succès)
# ──────────────────────────────────────────────────────────────────

def generer_rapport_execution(
    output_dir,
    name,
    DIR,
    NOM,
    gdf_troncons,
    gdf_troncons_copy,
    colonne_id,
    gdf_EEE,
    dict_sig,
    api_statuts,           # dict {nom_api: {"ok": bool, "couches": {nom: bool}, "erreur": str|None}}
    df_scoring,
    chemin_fichier_sortie,
    nom_fichier_sortie,
    date_debut,
    date_fin,
    mode_emprise,          # "Option A (fichier zone d'emprise + réseau routier)" ou "Option B (réseau routier = zone d'étude)"
    fichier_troncons_path,
    warnings_liste=None,   # liste de str, avertissements non bloquants
    colonne_id_origine=None,  # (26.9.0) nom de la variable identifiant CHOISIE par
                              # l'utilisateur, avant son renommage interne en
                              # 'nom_plo_fi'. None → comportement antérieur.
):
    """
    Génère un rapport .txt de fin d'exécution SPRINGE.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    duree = date_fin - date_debut
    duree_str = str(datetime.timedelta(seconds=int(duree.total_seconds())))

    # Libellé de la colonne identifiant pour le rapport (26.9.0).
    # Trois cas : pas d'information d'origine (appel ancien), variable déjà
    # nommée nom_plo_fi (rien à signaler), ou variable renommée en interne.
    if not colonne_id_origine or colonne_id_origine == colonne_id:
        _libelle_colonne_id = colonne_id
    else:
        _libelle_colonne_id = (f"{colonne_id_origine}  "
                               f"(renommée « {colonne_id} » en interne)")

    # Stats EEE
    nb_pts_eee_total = len(gdf_EEE)
    nb_pts_eee_avec_troncon = (gdf_EEE[colonne_id] != 'NA').sum() if colonne_id in gdf_EEE.columns else "N/A"
    nb_pts_eee_sans_troncon = (gdf_EEE[colonne_id] == 'NA').sum() if colonne_id in gdf_EEE.columns else "N/A"

    # Stats tronçons
    nb_troncons_brut = len(gdf_troncons)
    nb_troncons_dedup = len(gdf_troncons_copy)

    # Colonnes scores présentes
    cols_scores = [c for c in df_scoring.columns if "_impact" in c or "_vulnerabilite" in c or "score" in c]

    lignes = []
    sep = "=" * 72

    lignes += [
        sep,
        " SPRINGE — RAPPORT D'EXÉCUTION",
        sep,
        f"  Date / heure         : {date_debut.strftime('%d/%m/%Y à %H:%M:%S')}",
        f"  Durée totale         : {duree_str}",
        f"  DIR                  : {DIR}",
        f"  Opérateur            : {NOM}",
        f"  Nom du projet        : {name}",
        "",
        sep,
        " 1. DONNÉES D'ENTRÉE",
        sep,
        f"  Mode zone d'étude    : {mode_emprise}",
        f"  Fichier tronçons     : {fichier_troncons_path}",
        # (26.9.0) Si la variable choisie a été renommée en interne, le rapport
        # affiche le nom D'ORIGINE : c'est celui que le gestionnaire retrouvera
        # dans sa table attributaire. colonne_id ('nom_plo_fi') reste utilisé
        # plus haut pour compter les points EEE rattachés à un tronçon.
        f"  Colonne identifiant  : {_libelle_colonne_id}",
        "",
        f"  Tronçons bruts       : {nb_troncons_brut}",
        f"  Tronçons après dédup : {nb_troncons_dedup}",
        "",
        f"  Points EEE total     : {nb_pts_eee_total}",
        f"  → associés à un tronçon  : {nb_pts_eee_avec_troncon}",
        f"  → sans tronçon associé   : {nb_pts_eee_sans_troncon}",
        "",
    ]

    # Couches SIG internes
    lignes += [
        sep,
        " 2. COUCHES SIG INTERNES (01_data)",
        sep,
    ]
    for nom_couche, gdf_couche in dict_sig.items():
        nb_entites = len(gdf_couche) if gdf_couche is not None else 0
        crs = gdf_couche.crs.to_epsg() if gdf_couche is not None and gdf_couche.crs else "?"
        lignes.append(f"  ✔  {nom_couche:<35} {nb_entites:>6} entités   CRS = EPSG:{crs}")
    lignes.append("")

    # APIs
    lignes += [
        sep,
        " 3. COUCHES ISSUES DES API",
        sep,
    ]
    for nom_api, info in api_statuts.items():
        statut_global = "✔  OK" if info["ok"] else "✘  ERREUR"
        lignes.append(f"  {statut_global}  — {nom_api}")
        if info.get("couches"):
            for nom_couche, ok in info["couches"].items():
                symbole = "    ✔" if ok else "    ✘"
                lignes.append(f"  {symbole}  {nom_couche}")
        if not info["ok"] and info.get("erreur"):
            lignes.append(f"       Erreur : {info['erreur'][:120]}")
        lignes.append("")

    # Résultats calculs
    lignes += [
        sep,
        " 4. RÉSULTATS DES CALCULS",
        sep,
        f"  Indicateurs calculés : {', '.join(cols_scores) if cols_scores else 'aucun'}",
        "",
    ]

    # Scores moyens par enjeu
    for col in ["score_enjeu_MS", "score_enjeu_N", "score_enjeu_P", "score_troncon_final"]:
        if col in df_scoring.columns:
            moy = df_scoring[col].mean()
            lignes.append(f"  Moyenne {col:<25} : {moy:.2f}")
    lignes.append("")

    # Fichier de sortie
    lignes += [
        sep,
        " 5. FICHIER DE SORTIE",
        sep,
        f"  Nom du fichier       : {nom_fichier_sortie}",
        f"  Répertoire           : {output_dir}",
        f"  Chemin complet       : {chemin_fichier_sortie}",
        "",
    ]

    # Avertissements
    if warnings_liste:
        lignes += [
            sep,
            " 6. AVERTISSEMENTS (non bloquants)",
            sep,
        ]
        for w in warnings_liste:
            lignes.append(f"  ⚠  {w}")
        lignes.append("")

    lignes += [sep, " FIN DU RAPPORT", sep]

    contenu = "\n".join(lignes)

    # NOMMAGE CENTRALISÉ (2026-09-08). Trame commune à toutes les sorties :
    #     SPRINGE_version202609_<opérateur>_<structure>_<date>_RAPPORT.txt
    #
    # Deux changements par rapport à l'ancien RAPPORT_SPRINGE_{DIR}_{date_heure} :
    #   - le socle passe EN TÊTE, si bien que tous les fichiers d'une même
    #     exécution se retrouvent côte à côte dans l'explorateur au lieu
    #     d'être triés par type ;
    #   - l'heure disparaît du nom (décision du 08/09/2026). Comme deux runs
    #     dans la journée produiraient alors le même nom, la fonction ajoute
    #     un suffixe _02, _03... UNIQUEMENT en cas de collision réelle : un
    #     rapport d'exécution est un historique, l'écraser ferait perdre la
    #     trace du run précédent.
    #
    # On passe date_debut et non la date du jour : un run lancé à 23h58 doit
    # produire des fichiers datés du jour de son DÉBUT, même s'il franchit
    # minuit, sinon ses sorties se retrouvent éparpillées sur deux dates.
    nom_rapport = nommer_fichiers_sortie.nom_fichier_rapport(
        output_dir, NOM, DIR, date_reference=date_debut
    )
    chemin_rapport = output_dir / nom_rapport

    with open(chemin_rapport, "w", encoding="utf-8") as f:
        f.write(contenu)

    print(f"\n📄 Rapport d'exécution enregistré : {chemin_rapport}")
    return chemin_rapport


# Fonction B :
# ──────────────────────────────────────────────────────────────────
# Rapport d'incident (crash)
# ──────────────────────────────────────────────────────────────────

def generer_rapport_incident(
    output_dir,
    exc,                  # exception Python attrapée
    etape,               # str : description de l'étape en cours au moment du crash
    date_debut,
    DIR="DIR",
    NOM="utilisateur",
    name="SPRINGE",
    contexte=None,        # dict optionnel {cle: valeur} infos de contexte au moment du crash
):
    """
    Génère un rapport d'incident .txt en cas de crash de SPRINGE.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_crash = datetime.datetime.now()
    tb_str = traceback.format_exc()

    sep = "=" * 72
    sep2 = "-" * 72

    lignes = [
        sep,
        " SPRINGE — RAPPORT D'INCIDENT",
        sep,
        f"  Date / heure du crash  : {date_crash.strftime('%d/%m/%Y à %H:%M:%S')}",
        f"  Durée avant crash      : {str(datetime.timedelta(seconds=int((date_crash - date_debut).total_seconds())))}",
        f"  DIR                    : {DIR}",
        f"  Opérateur              : {NOM}",
        f"  Nom du projet          : {name}",
        "",
        sep,
        " ÉTAPE EN COURS AU MOMENT DU CRASH",
        sep,
        f"  {etape}",
        "",
        sep,
        " TYPE D'ERREUR",
        sep,
        f"  {type(exc).__name__} : {str(exc)}",
        "",
        sep,
        " TRACEBACK COMPLET",
        sep,
        tb_str,
    ]

    if contexte:
        lignes += [
            sep,
            " CONTEXTE AU MOMENT DU CRASH",
            sep,
        ]
        for cle, val in contexte.items():
            lignes.append(f"  {cle:<30} : {val}")
        lignes.append("")

    lignes += [
        sep,
        " CONSEILS DE DIAGNOSTIC",
        sep,
        "  1. Relire le message d'erreur ci-dessus et le numéro de ligne indiqué.",
        "  2. Vérifier que les fichiers d'entrée existent et sont valides.",
        "  3. Vérifier la connexion internet si l'erreur vient d'une API.",
        "  4. Vérifier que les bibliothèques sont correctement installées (installer.py).",
        "",
        sep,
        " FIN DU RAPPORT D'INCIDENT",
        sep,
    ]

    contenu = "\n".join(lignes)

    # NOMMAGE CENTRALISÉ (2026-09-08), même trame que le rapport d'exécution :
    #     SPRINGE_version202609_<opérateur>_<structure>_<date>_INCIDENT.txt
    #
    # Le suffixe incrémental (_02, _03...) compte double ici : pendant une
    # séance de débogage, plusieurs crashs successifs sont la norme, et c'est
    # souvent le PREMIER qui porte l'erreur d'origine. L'écraser reviendrait
    # à perdre l'information au moment précis où on en a besoin.
    #
    # On date sur date_debut et non sur date_crash : les fichiers d'un même
    # run restent groupés même si le plantage survient après minuit.
    nom_rapport = nommer_fichiers_sortie.nom_fichier_incident(
        output_dir, NOM, DIR, date_reference=date_debut
    )
    chemin_rapport = output_dir / nom_rapport

    with open(chemin_rapport, "w", encoding="utf-8") as f:
        f.write(contenu)

    print(f"\n🚨 Rapport d'incident enregistré : {chemin_rapport}")
    return chemin_rapport
