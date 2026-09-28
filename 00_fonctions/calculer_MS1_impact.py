# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_MS1_impact"
Date : 2026-02-17
Objectif : calcul indicateur MS1
═══════════════════════════════════════════════════════════════════

Calcul de l'impact des EEE sur les troncons pour l'indicateur MS1 - visibilité critique
     
Logique : attribuer des points dans df_scoring<MS1_impact selon les conditions dans le troncon

Paramètres de la fonction :

  - gdf_EEE : Gdf des points de présence EEE, avec une colonne de jointure "nom_plo_fi" et "plante" pour avoir le nom de l'espèce EEE
  - EEE_SHEET : Xl des caractéristiques biologiques de chaque EEE
  - df_scoring : DF créé pour contenir les points et scores des indicateurs

La fonction sort : une nouvelle colonne 'MS1_impact' dans df_scoring, avec des valeurs numérique entier de 5 à 0 compris.
    
"""
import pandas as pd

def calculer_MS1_impact(gdf_EEE, EEE_caracterisques_excel, df_scoring):
    
    
    print(f"\n{'='*70}")
    print("CALCUL MS1_IMPACT - Imapct des EEE sur la visibilité critique dans le tronçon")
    print(f"{'='*70}\n")

    # Vérifier l'existance des colonnes d'intêret
    # Vérifier colonnes
    if 'nom_plo_fi' not in gdf_EEE.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_EEE")
    
    if 'species_name_sci' not in gdf_EEE.columns:
        raise ValueError(
            "❌ 'species_name_sci' introuvable dans gdf_EEE. "
            "fenetre_mapping_especes.mapping_interactif_especes() doit être "
            "appelée avant ce module."
            )

    if 'species_name_sci' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'species_name_sci' introuvable dans EEE_caracterisques_excel")

    if 'height_max_cm' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'height_max_cm' introuvable dans EEE_caracterisques_excel")

    if 'MS1_vulnerabilite' not in df_scoring.columns:
        raise ValueError("❌ 'MS1_vulnerabilite' introuvable dans df_scoring")


    # ──────────────────────────────────────────────────────────────────────────
    # Espèces : on consomme le mapping déjà fait, on ne le refait pas
    # ──────────────────────────────────────────────────────────────────────────
    # MODIFICATION DU 2026-09-08 — suppression du dictionnaire local.
    #
    # Ce module embarquait sa propre table {'Renouees': 'Reynoutria sp', ...}
    # figée sur la colonne 'plante'. Cinq modules en avaient chacun une copie,
    # ce qui neutralisait purement et simplement le travail de
    # fenetre_mapping_especes : le gestionnaire pouvait déclarer que sa colonne
    # d'espèces s'appelle 'ESPECE' et contient 'REYNOUTRIA JAPONICA', le module
    # cherchait quand même 'plante' et 'Renouees', et sortait des NaN partout.
    #
    # On consomme désormais 'species_name_sci', produit une seule fois en amont
    # par la fenêtre de mapping et déjà utilisé comme clé de jointure ici.
    gdf_EEE_mapped = gdf_EEE.copy()

    # Un point sans espèce reconnue n'est pas une erreur : le gestionnaire a pu
    # choisir « aucune correspondance » pour une espèce hors référentiel SPRINGE.
    # Ces points seront écartés par la jointure ci-dessous, on le signale.
    non_mappes = int(gdf_EEE_mapped['species_name_sci'].isna().sum())
    if non_mappes > 0:
        print(f"ℹ️  {non_mappes} point(s) sans espèce de référence (écartés du calcul)")

    #jointure avec EEE_caracterisques_excel pour récupérer 'hauteur_EEE'
    gdf_EEE_enrichi = gdf_EEE_mapped.merge(
        EEE_caracterisques_excel[['species_name_sci', 'height_max_cm']],
        on= 'species_name_sci',
        how='left'
    )

    print("Hauteur par espèce EEE:")
    hauteur_eee = (
        gdf_EEE_enrichi[['species_name_sci','height_max_cm']]
        .drop_duplicates()
        .sort_values('height_max_cm', ascending=False)
    )
    for _, row in hauteur_eee.iterrows():
        print(f"{row['species_name_sci']}: {row['height_max_cm']}")

    # Les hauteurs EEE sont numériques, trnasformer en catégories
    def categoriser_hauteur(valeur):
        try:
            # Certaines valeurs sont des ranges "450-500", on prend le max
            if '-' in str(valeur):
                valeur = max([int(x) for x in str(valeur).split('-')])
            valeur = int(valeur)
            if valeur >= 400:    return 'haute'
            elif valeur >= 200:  return 'moyenne'
            else:                return 'basse'
        except:
            return None  # si valeur manquante ou non parseable

    gdf_EEE_enrichi['hauteur_cat'] = gdf_EEE_enrichi['height_max_cm'].apply(categoriser_hauteur)

    # hauteur maximale par troncon
    ordre_hauteur = {'haute':3, 'moyenne':2, 'basse':1}

    # ── Éclatement des points de bordure (harmonisation du 2026-09-08) ──────
    # PROBLÈME CORRIGÉ : join_num_troncon_a_gdf_EEE écrit "A, B" dans
    # nom_plo_fi quand un point tombe à cheval sur deux tronçons. Sans
    # éclatement, le groupby ci-dessous crée un groupe pour la clé LITTÉRALE
    # "A, B", qui ne correspond à aucun tronçon de df_scoring : le merge de
    # l'étape suivante ne le rattache nulle part et le point DISPARAÎT
    # silencieusement du calcul, pour les DEUX tronçons concernés.
    #
    # CHOIX RETENU (CS-14 du cadrage) : le point est compté sur CHACUN des
    # tronçons qu'il intersecte. La plante existe physiquement sur les deux et
    # les deux gestionnaires sont concernés. L'alternative — arbitrer un
    # tronçon unique — attribuerait arbitrairement la charge à l'un des deux.
    #
    # Ce comportement est celui de MS3, N1, N2, P1, P3, P4 et de la
    # caractérisation des populations : MS1 et MS2 étaient les deux exceptions.
    #
    # Pourquoi éclater ICI et pas sur gdf_EEE en début de fonction :
    # gdf_EEE est un GeoDataFrame, dont .explode() vise la GÉOMÉTRIE et non
    # une colonne. En travaillant sur l'extraction à deux colonnes ci-dessous,
    # qui est un DataFrame pandas ordinaire, il n'y a aucune ambiguïté.
    #
    # Effet à connaître : un point de bordure porte le maximum de hauteur sur
    # les deux tronçons. C'est voulu.

    hauteur_par_point = gdf_EEE_enrichi[['nom_plo_fi', 'hauteur_cat']].copy()
    # "A, B" -> ["A", " B"], puis une ligne par élément de la liste
    hauteur_par_point['nom_plo_fi'] = (
        hauteur_par_point['nom_plo_fi'].astype(str).str.split(',')
    )
    hauteur_par_point = hauteur_par_point.explode('nom_plo_fi')
    # .strip() enlève l'espace laissé après la virgule par le split
    hauteur_par_point['nom_plo_fi'] = hauteur_par_point['nom_plo_fi'].str.strip()

    hauteur_max_eee_par_troncons = (
        hauteur_par_point
        .dropna(subset=['hauteur_cat'])
        .assign(hauteur_rank=lambda x: x['hauteur_cat'].map(ordre_hauteur))
        .sort_values('hauteur_rank', ascending=False)
        .groupby('nom_plo_fi')
        .first()
        .reset_index()
        [['nom_plo_fi', 'hauteur_cat']]
    )

    #jointure avec df_scoring
    df_scoring = df_scoring.merge(
        hauteur_max_eee_par_troncons,
        on='nom_plo_fi',
        how='left'
    )

    #les troncons sans EEE ont hauteur_EEE = NaN
    df_scoring['hauteur_cat'] = df_scoring['hauteur_cat'].fillna('aucune')

    # Scoring MS1 imapct
    def attribuer_points_MS1(row):
        vuln = row['MS1_vulnerabilite']
        haut = row['hauteur_cat']
        
        # ✅ CORRECTION : si pas d'EEE, toujours 0
        if haut == 'aucune':
            return 0
        
        if vuln == 'oui':
            if haut == 'haute':    return 5
            if haut == 'moyenne':  return 4
            else:  # haut == 'basse'
                return 3
        else:  # vuln == 'non'
            if haut == 'haute':    return 3
            if haut == 'moyenne':  return 2
            else:  # haut == 'basse'
                return 1

    df_scoring.loc[:, 'MS1_impact'] = df_scoring.apply(attribuer_points_MS1, axis=1)

    # Nettoyage : supprimer la colonne temporaire hauteur_EEE de df_scoring
    df_scoring.drop(columns=['hauteur_cat'], inplace=True)

    
    # ── Statistiques ─────────────────────────────────────────────────────────
    # nunique() sur la colonne BRUTE compterait la clé littérale "A, B" comme
    # un tronçon à part entière, en plus de A et de B. On compte donc sur la
    # version éclatée, qui reflète les tronçons réellement concernés.
    nb_troncons_eee = hauteur_par_point['nom_plo_fi'].nunique()
    nb_score_max    = (df_scoring['MS1_impact'] == 5).sum()

    print(f"\nRésultats :")
    print(f"  Tronçons avec EEE : {nb_troncons_eee}")
    print(f"  Tronçons score max (5) : {nb_score_max}")
    print(f"  Distribution des scores :\n{df_scoring['MS1_impact'].value_counts().sort_index()}")
    print(f"\n{'='*70}\n")

    return df_scoring
