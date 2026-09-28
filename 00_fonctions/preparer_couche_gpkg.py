# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Fonction "preparer_couche_gpkg"
Date : 2026-05-10
Modifié le : 2026-09-02 — ajout de l'axe densité EEE dans l'export
Remplace : calculer_priorisation (changement de philosophie)
═══════════════════════════════════════════════════════════════════

OBJECTIF
────────
Préparer la couche GeoPackage finale de SPRINGE en assemblant, pour
chaque tronçon, l'ensemble des éléments permettant à l'utilisateur de
COMPARER les tronçons entre eux et de prioriser LUI-MÊME selon ses
propres besoins/préférences.

PHILOSOPHIE
───────────
Contrairement à l'ancienne version (calculer_priorisation), cette
fonction ne produit PLUS de plan d'action prescriptif (plus de
"annee_intervention" qui imposait un découpage en tiers, plus de
tri lexicographique unique qui imposait une hiérarchie d'enjeux).

À la place, on fournit dans le gpkg :
    - les indicateurs bruts (MS1..MS3, N1..N2, P1..P4)
    - les scores agrégés par enjeu (MS, N, P)
    - le score final agrégé
    - 4 rangs indicatifs (un par enjeu + un global)
    - l'axe densité EEE (nb_points_EEE, densite_EEE_valeur,
      densite_EEE_par_km, densite_EEE_categorie, rang_indicatif_densite)
      → axe INDÉPENDANT des enjeux MS/N/P, cf. calculer_densite_EEE.py :
      il ne modifie aucun score d'enjeu, c'est une dimension d'info
      supplémentaire livrée en parallèle (donc pas rattaché à un bloc
      MS/N/P dans l'ordre des colonnes, voir ÉTAPE 4).

L'utilisateur dispose ainsi des 3 niveaux de granularité (détail /
synthèse par enjeu / synthèse globale) + de l'axe densité, et peut
configurer sa propre symbologie QGIS sur la colonne qui correspond
à SA priorité métier.

GESTION DES EX-AEQUO
────────────────────
Les rangs sont calculés avec la méthode 'min' de pandas.rank() :
deux tronçons à égalité reçoivent le même rang, et le rang suivant
saute (ex : 1, 1, 3, 4...). C'est la convention la plus honnête pour
un outil non-prescriptif, et elle reflète fidèlement la notion
d'égalité de score sans artifice de départage.
(Le rang de densité, lui, est calculé en amont dans
calculer_densite_EEE.py avec la même méthode 'min' — on ne fait ici
que le récupérer tel quel dans df_scoring, pas de recalcul.)

PARAMÈTRES
──────────
    df_scoring        : DataFrame contenant les colonnes *_impact,
                        score_enjeu_MS/N/P, score_troncon_final
                        (sortie de calculer_score_final) ET les
                        colonnes de densité EEE (sortie de
                        calculer_densite_EEE, si cette étape a été
                        exécutée avant l'appel à cette fonction)
    gdf_troncons_copy : GeoDataFrame des tronçons avec géométrie et
                        l'identifiant 'nom_plo_fi'
    name              : str, nom du projet (ex: 'SPRINGE_modele_...')
    DIR               : str, nom de la DIR (ex: 'DIRO')
    output_dir        : str ou Path, répertoire de sortie

SORTIE
──────
    df_scoring : enrichi des 4 colonnes rang_indicatif_*
    gdf_export : GeoDataFrame final, écrit aussi en .gpkg sur disque
                 (inclut désormais l'axe densité EEE si présent dans
                 df_scoring — voir correctif du 2026-09-02 ci-dessous)

CORRECTIF DU 2026-09-02
────────────────────────
Bug identifié : calculer_densite_EEE() calcule bien nb_points_EEE,
densite_EEE_valeur, densite_EEE_par_km, densite_EEE_categorie et
rang_indicatif_densite dans df_scoring (appelée en amont, ligne 1366
de lancer_SPRINGE_version_juillet.py, donc AVANT cette fonction).
Mais l'ancienne version de preparer_couche_gpkg ne sélectionnait que
les colonnes finissant par '_impact' + une liste fixe de colonnes
d'enjeu — les colonnes de densité ne correspondent à aucun de ces
deux critères, donc jamais incluses dans cols_export : elles
existaient en mémoire mais étaient silencieusement absentes du gpkg
final. Voir ÉTAPE 3bis et ÉTAPE 4 ci-dessous pour la correction.

PISTES D'AMÉLIORATION (à documenter dans le doc d'algorithme)
─────────────────────
    - Ajouter des catégories textuelles (faible/moyen/fort) par enjeu
      pour faciliter une symbologie QGIS catégorielle prête à l'emploi
    - Ajouter des pourcentages par rapport au max observé pour
      comparer les enjeux entre eux malgré leurs échelles différentes
    - Ajouter un comptage du nombre d'indicateurs "actifs" par enjeu
      (nécessite de définir précisément ce qu'est un indicateur actif)
    - Lier automatiquement des styles QGIS (.qml) à chaque colonne
═══════════════════════════════════════════════════════════════════
"""

# ──────────────────────────────────────────────────────────────────
# Imports
# ──────────────────────────────────────────────────────────────────
import geopandas as gpd                  # pour manipuler le gdf final et exporter en .gpkg
from datetime import date                # pour horodater le nom du fichier de sortie

# Nommage centralisé (2026-09-08) : ce module ne fabrique plus ses noms de
# fichiers lui-même. Voir nommer_fichiers_sortie.py pour la trame et les
# motifs — en résumé, le nom était construit ici ET reconstruit à l'identique
# dans lancer_SPRINGE, avec les désynchronisations que ça implique.
import nommer_fichiers_sortie


def preparer_couche_gpkg(df_scoring, gdf_troncons_copy, name, DIR, output_dir=".",
                         NOM="utilisateur", date_reference=None):
    """
    Prépare la couche GeoPackage finale (descriptive/comparative,
    non-prescriptive). Voir docstring du module pour le détail.
    """

    # ══════════════════════════════════════════════════════════════
    # En-tête console pour le suivi d'exécution
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print("PRÉPARATION DE LA COUCHE GPKG - Comparaison des tronçons")
    print(f"{'='*70}\n")

    # ──────────────────────────────────────────────────────────────
    # ÉTAPE 1 — Vérification des colonnes nécessaires
    # ──────────────────────────────────────────────────────────────
    # On vérifie que df_scoring contient bien tout ce qu'on attend en
    # amont (scores agrégés issus de calculer_score_final). Si l'une
    # de ces colonnes manque, on lève une erreur explicite plutôt
    # que de produire un gpkg corrompu ou silencieusement incomplet.
    #
    # NB : on ne rend PAS les colonnes de densité obligatoires ici.
    # calculer_densite_EEE est un module optionnel/indépendant (axe
    # descriptif à part) : un utilisateur qui ne l'exécute pas doit
    # quand même pouvoir produire un gpkg valide avec les enjeux
    # MS/N/P seuls. La vérification de présence des colonnes densité
    # se fait plus loin, colonne par colonne (ÉTAPE 3bis), pas ici.
    cols_requises = [
        'nom_plo_fi',           # identifiant du tronçon (clé de jointure)
        'score_troncon_final',  # score global agrégé
        'score_enjeu_MS',       # score agrégé pour l'enjeu MS (sécurité usagers)
        'score_enjeu_N',        # score agrégé pour l'enjeu N (biodiversité)
        'score_enjeu_P',        # score agrégé pour l'enjeu P (gestion EEE)
    ]
    for col in cols_requises:
        if col not in df_scoring.columns:
            raise ValueError(f"❌ '{col}' introuvable dans df_scoring")


    # ──────────────────────────────────────────────────────────────
    # ÉTAPE 2 — Calcul des 4 rangs indicatifs (MS / N / P / final)
    # ──────────────────────────────────────────────────────────────
    # Un rang par enjeu + un rang global. Tous calculés indépendamment
    # les uns des autres pour éviter d'imposer une hiérarchie entre
    # enjeux. C'est à l'utilisateur, dans QGIS, de choisir sur quel
    # rang il veut baser sa symbologie/priorisation.
    #
    # Méthode 'min' : pour les ex-aequo, tous reçoivent le rang minimal
    # commun (ex : 1, 1, 3, 4...). Choix justifié dans la docstring.
    #
    # ascending=False : on veut que le score le plus élevé = rang 1
    # (le plus prioritaire au sens du score). Pandas trie par défaut
    # en ordre croissant, donc il faut explicitement inverser.
    #
    # NB : le rang de densité (rang_indicatif_densite) n'est PAS
    # recalculé ici — il est déjà produit par calculer_densite_EEE
    # et arrive tel quel dans df_scoring. On se contente de le
    # récupérer à l'ÉTAPE 3bis, comme les autres colonnes de densité.

    df_scoring['rang_indicatif_MS'] = df_scoring['score_enjeu_MS'].rank(
        method='min', ascending=False
    ).astype(int)

    df_scoring['rang_indicatif_N'] = df_scoring['score_enjeu_N'].rank(
        method='min', ascending=False
    ).astype(int)

    df_scoring['rang_indicatif_P'] = df_scoring['score_enjeu_P'].rank(
        method='min', ascending=False
    ).astype(int)

    df_scoring['rang_indicatif_final'] = df_scoring['score_troncon_final'].rank(
        method='min', ascending=False
    ).astype(int)

    # Diagnostic console : combien d'ex-aequo sur le rang final ?
    # Utile pour que l'utilisateur sache si sa symbologie QGIS basée
    # sur le rang_indicatif_final va regrouper beaucoup de tronçons.
    nb_exaequo_final = (
        df_scoring['rang_indicatif_final']
        .duplicated(keep=False)
        .sum()
    )
    print(f"Nombre total de tronçons             : {len(df_scoring)}")
    print(f"Tronçons ex-aequo sur le rang final  : {nb_exaequo_final}")
    print("  → Méthode 'min' : ex-aequo conservés à rangs égaux")


    # ──────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Détection des colonnes d'indicateurs bruts disponibles
    # ──────────────────────────────────────────────────────────────
    # On ne fige pas en dur la liste MS1..MS3, N1..N2, P1..P4 dans le
    # code : on détecte automatiquement les colonnes *_impact dans
    # df_scoring. Cela permet à la fonction de continuer à fonctionner
    # si demain on ajoute MS4, N3, P5... sans avoir à la modifier.
    cols_impact = [c for c in df_scoring.columns if c.endswith('_impact')]

    # On les répartit par enjeu en se basant sur le préfixe du nom.
    # Convention SPRINGE : un indicateur s'appelle <enjeu><num>_impact
    # ex : MS1_impact, N2_impact, P3_impact.
    # On trie pour avoir un ordre stable (MS1 avant MS2 avant MS3...).
    cols_MS = sorted([c for c in cols_impact if c.startswith('MS')])
    cols_N  = sorted([c for c in cols_impact if c.startswith('N')])
    cols_P  = sorted([c for c in cols_impact if c.startswith('P')])

    print(f"\nIndicateurs MS détectés : {cols_MS}")
    print(f"Indicateurs N  détectés : {cols_N}")
    print(f"Indicateurs P  détectés : {cols_P}")


    # ──────────────────────────────────────────────────────────────
    # ÉTAPE 3bis — Détection des colonnes de l'axe densité EEE
    # ──────────────────────────────────────────────────────────────
    # /!\ CORRECTIF : ce bloc est nouveau. Contrairement aux
    # indicateurs d'enjeu (MS1_impact, N2_impact...), les colonnes de
    # densité ne suivent pas la convention <enjeu><num>_impact — donc
    # la détection automatique par suffixe de l'ÉTAPE 3 ne les
    # capture jamais. Il faut les lister explicitement.
    #
    # On ne les rend pas obligatoires (contrairement à cols_requises
    # de l'ÉTAPE 1) : si calculer_densite_EEE n'a pas été exécutée en
    # amont dans le launcher, ces colonnes n'existeront simplement pas
    # dans df_scoring, et on ne veut pas que ça fasse planter l'export
    # du gpkg pour autant — l'axe densité est optionnel/indépendant.
    # D'où le filtre "if c in df_scoring.columns" : on ne garde que
    # celles qui sont réellement présentes.
    # MISE À JOUR DU 2026-09-08 : la liste ci-dessous a entièrement changé.
    # calculer_densite_EEE a été remplacé par caracteriser_populations_EEE, et
    # AUCUNE des anciennes colonnes ne subsiste :
    #   - nb_points_EEE            -> nb_populations_total (un point est une
    #                                 POPULATION au sens du protocole, pas une
    #                                 plante : le nom induisait en erreur)
    #   - densite_EEE_valeur       -> supprimé (sommait des rangs ordinaux puis
    #                                 divisait par des km : non défini et non
    #                                 homogène dimensionnellement)
    #   - densite_EEE_par_km       -> supprimé, même motif
    #   - densite_EEE_categorie    -> supprimé (découpage en quartiles calculé
    #                                 sur le run courant, donc non comparable
    #                                 d'une exécution à l'autre)
    #   - rang_indicatif_densite   -> supprimé (l'axe est descriptif : aucun
    #                                 rang, aucun score, aucun adjectif)
    #
    # Sans cette mise à jour, le bug corrigé le 2026-09-02 se serait reproduit
    # à l'identique : les nouvelles colonnes existeraient dans df_scoring mais
    # seraient silencieusement absentes du gpkg, faute de figurer ici.
    cols_caracterisation_possibles = [
        'statut_donnee',            # "observations enregistrees" / "aucune observation enregistree"
        'nb_populations_total',     # populations rattachées, toutes catégories
        'nb_categories_presentes',  # nombre de catégories d'EEE présentes (0 à 5)
        'synthese_EEE',             # résumé rédigé, lisible au clic dans QGIS
        'annee_releve_max',         # année du relevé le plus récent
    ]
    cols_densite = [c for c in cols_caracterisation_possibles
                    if c in df_scoring.columns]

    if cols_densite:
        print(f"Colonnes de caractérisation EEE détectées : {cols_densite}")
    else:
        print("ℹ️  Aucune colonne de caractérisation EEE dans df_scoring "
              "(données non conformes au protocole, ou paramétrage non validé) "
              "→ le gpkg sera produit sans cet axe.")


    # ──────────────────────────────────────────────────────────────
    # ÉTAPE 4 — Construction de la liste ordonnée des colonnes à exporter
    # ──────────────────────────────────────────────────────────────
    # Ordre par enjeu (validé avec Antoine) :
    #     loc → MS bruts + score_MS + rang_MS
    #         → N  bruts + score_N  + rang_N
    #         → P  bruts + score_P  + rang_P
    #         → score_final + rang_final
    #         → axe densité EEE (bloc à part, cf. correctif ci-dessous)
    #
    # L'utilisateur ouvrant la table attributaire QGIS verra donc
    # successivement, par bloc thématique, toutes les infos d'un
    # enjeu avant de passer au suivant — c'est plus lisible que
    # d'avoir indicateurs / scores / rangs éparpillés.
    #
    # /!\ CORRECTIF : cols_densite est ajouté ICI, à la fin. C'est la
    # seule ligne qui manquait pour que l'axe densité arrive dans le
    # gpkg final — tout le reste (calcul, ordre du bloc en dernier
    # pour respecter son statut d'axe indépendant plutôt que rattaché
    # à un enjeu) était déjà en place dans calculer_densite_EEE.
    cols_export_metier = (
        cols_MS + ['score_enjeu_MS', 'rang_indicatif_MS']
        + cols_N + ['score_enjeu_N', 'rang_indicatif_N']
        + cols_P + ['score_enjeu_P', 'rang_indicatif_P']
        + ['score_troncon_final', 'rang_indicatif_final']
        + cols_densite   # ← LA CORRECTION : bloc densité, à part des enjeux
    )

    # On préfixe avec 'nom_plo_fi' qui sert de clé de jointure
    # (et qui n'apparaît qu'une seule fois grâce à 'on=' du merge).
    cols_export = ['nom_plo_fi'] + cols_export_metier


    # ──────────────────────────────────────────────────────────────
    # ÉTAPE 5 — Jointure spatiale avec gdf_troncons_copy
    # ──────────────────────────────────────────────────────────────
    # On part du gdf des tronçons (qui contient la géométrie et les
    # colonnes de localisation : numéro de route, PR début/fin, etc.)
    # et on lui rattache les colonnes métier de df_scoring.
    #
    # On récupère TOUTES les colonnes du gdf_troncons_copy hors
    # géométrie pour les remettre devant dans le gpkg (colonnes
    # de localisation au début, métier ensuite, géométrie à la fin).
    cols_localisation = [
        col for col in gdf_troncons_copy.columns if col != 'geometry'
    ]
    print(f"\nColonnes de localisation conservées : {cols_localisation}")

    # Merge inner : on ne garde que les tronçons présents dans les
    # deux DataFrames (sécurité, évite les NaN dans le gpkg final).
    gdf_export = gdf_troncons_copy[cols_localisation + ['geometry']].merge(
        df_scoring[cols_export],
        on='nom_plo_fi',
        how='inner'
    )

    # Le merge pandas peut transformer un GeoDataFrame en simple
    # DataFrame si la géométrie n'est pas la colonne active : on
    # reconstruit explicitement le GeoDataFrame pour garantir
    # l'export .gpkg correct.
    if not isinstance(gdf_export, gpd.GeoDataFrame):
        gdf_export = gpd.GeoDataFrame(
            gdf_export,
            geometry='geometry',
            crs=gdf_troncons_copy.crs
        )

    # Réordonnancement final des colonnes :
    # localisation → métier ordonnées par enjeu (+ densité) → géométrie en dernier.
    # (Le merge ne garantit pas l'ordre, donc on force ici.)
    ordre_final = cols_localisation + cols_export_metier + ['geometry']
    gdf_export = gdf_export[ordre_final]


    # ──────────────────────────────────────────────────────────────
    # ÉTAPE 6 — Export GeoPackage
    # ──────────────────────────────────────────────────────────────
    # Convention de nommage : projet_SPRINGE_{name}_{DIR}_{date}.gpkg
    # Le {name} contient déjà DIR et NOM (voir lancer_SPRINGE), mais
    # on remet DIR ici par cohérence avec la version précédente du
    # code et pour faciliter la recherche par DIR dans un répertoire
    # contenant des sorties de plusieurs DIR.
    # NOMMAGE CENTRALISÉ (2026-09-08). Trame :
    #     SPRINGE_version202609_<opérateur>_<structure>_<date>.gpkg
    # Le nom de la couche interne est identique au nom du fichier, pour que le
    # gestionnaire fasse le lien sans réfléchir dans le panneau QGIS.
    #
    # `name` n'entre PLUS dans le nom : il valait
    # "SPRINGE_modele_Version2026_{DIR}_{NOM}", donc il contenait déjà la
    # structure et l'opérateur, que le nom de fichier rajoutait ensuite. D'où
    # le doublon "SPRINGE...SPRINGE" et "cbn...cbn" constaté le 08/09/2026.
    # `name` reste dans la signature parce qu'il sert encore d'intitulé de
    # projet affiché dans le rapport d'exécution.
    nom_couche    = nommer_fichiers_sortie.nom_couche_gpkg(NOM, DIR, date_reference)
    nom_fichier   = nommer_fichiers_sortie.nom_fichier_gpkg(NOM, DIR, date_reference)

    # Pathlib-friendly : on accepte aussi bien un str qu'un Path en
    # entrée (output_dir). On utilise os.path.join pour rester
    # portable (le séparateur Windows '\\' du code précédent posait
    # potentiellement problème sur Linux/Mac).
    import os
    chemin_export = os.path.join(str(output_dir), nom_fichier)

    gdf_export.to_file(chemin_export, layer=nom_couche, driver='GPKG')

    # Bilan console : confirmation du chemin réel d'écriture
    print(f"\n✅ Export réussi :")
    print(f"   Fichier  : {nom_fichier}")
    print(f"   Couche   : {nom_couche}")
    print(f"   Tronçons : {len(gdf_export)}")
    print(f"   Chemin   : {chemin_export}")
    print(f"\n{'='*70}\n")

    # On retourne df_scoring (enrichi des 4 rangs), gdf_export, ET le chemin
    # réellement écrit.
    #
    # AJOUT DU 2026-09-08 — pourquoi ce troisième élément : jusqu'ici,
    # lancer_SPRINGE RECONSTRUISAIT le nom du fichier de son côté pour pouvoir
    # le retrouver, avec un commentaire « ⚠️ DOIT rester strictement cohérent ».
    # Toute évolution du nommage ici devait être répercutée là-bas à la main,
    # sans quoi le script pointait vers un fichier inexistant. Renvoyer le
    # chemin supprime la duplication : il n'y a plus qu'une source de vérité.
    return df_scoring, gdf_export, chemin_export
