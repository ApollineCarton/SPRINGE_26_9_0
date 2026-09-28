# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_N2_impact"
Date : 2026-09-09
Objectif : calculer l'indicateur N2 impact'
═══════════════════════════════════════════════════════════════════

Calcul de l'impact des EEE pour l'indicateur N2 - potentiel de transformation des habitats adjacents.
Logique : scorer le potentiel de transformation écologique des EEE présentes sur le tronçon,
          via un score pondéré des 3 variables de transformation (hydro > sol > structure).

Pondération justifiée par la littérature (contexte européen) :
    - habitat_transformation_hydrology × 3 : impact cascadant sur toute la communauté,
      modification durable du régime hydrique (poids maximal)
    - habitat_transformation_soil × 2 : effets legacy persistants après élimination EEE
    - habitat_transformation_structure × 1 : impact direct mais réversible

Paramètres :
    - gdf_EEE : Gdf des points de présence EEE, colonnes 'nom_plo_fi' et 'species_name_sci'
    - EEE_caracterisques_excel : Xl des caractéristiques biologiques de chaque EEE
    - df_scoring : DF contenant les tronçons

Sortie : nouvelle colonne 'N2_impact' dans df_scoring, valeurs entières de 0 à 5.
Pas de colonne N2_vulnerabilite : N2 est un indicateur purement bonus EEE.
"""
import pandas as pd

def calculer_N2_impact(gdf_EEE, EEE_caracterisques_excel, df_scoring):

    print(f"\n{'='*70}")
    print("CALCUL N2_IMPACT - Potentiel de transformation des habitats adjacents")
    print(f"{'='*70}\n")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1 — Vérification des colonnes nécessaires
    # ──────────────────────────────────────────────────────────────────────────
    if 'nom_plo_fi' not in gdf_EEE.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_EEE")
        
    if 'species_name_sci' not in gdf_EEE.columns:
        raise ValueError(
            "❌ 'species_name_sci' introuvable dans gdf_EEE. "
            "fenetre_mapping_especes.mapping_interactif_especes() doit être "
            "appelée avant ce module."
        )
        
    for col in ['species_name_sci', 'habitat_transformation_hydrology',
                'habitat_transformation_soil', 'habitat_transformation_structure']:
        if col not in EEE_caracterisques_excel.columns:
            raise ValueError(f"❌ '{col}' introuvable dans EEE_caracterisques_excel")
            
    if 'nom_plo_fi' not in df_scoring.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans df_scoring")


    # ──────────────────────────────────────────────────────────────────────────
    # Espèces : on consomme le mapping déjà fait, on ne le refait pas
    # ──────────────────────────────────────────────────────────────────────────
    # MODIFICATION DU 2026-09-08 — suppression du dictionnaire local.
    #
    # Ce module embarquait sa propre table {'Renouees': 'Reynoutria sp', ...}
    # figée sur la colonne 'species_name_sci'. Cinq modules en avaient chacun une copie,
    # ce qui neutralisait purement et simplement le travail de
    # fenetre_mapping_especes : le gestionnaire pouvait déclarer que sa colonne
    # d'espèces s'appelle 'ESPECE' et contient 'REYNOUTRIA JAPONICA', le module
    # cherchait quand même 'species_name_sci' et 'Renouees', et sortait des NaN partout.
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

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 — Jointure avec EEE_caracterisques_excel
    # On récupère les 3 variables de transformation pour chaque point EEE.
    # ──────────────────────────────────────────────────────────────────────────
    gdf_EEE_enrichi = gdf_EEE_mapped.merge(
        EEE_caracterisques_excel[[
            'species_name_sci',
            'habitat_transformation_hydrology',
            'habitat_transformation_soil',
            'habitat_transformation_structure'
        ]],
        on='species_name_sci',
        how='left'
    )


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Calcul du score de transformation pondéré
    # On convertit oui/non en 1/0 puis on applique les poids.
    # transformation_score = (hydro × 3) + (sol × 2) + (structure × 1)
    # Échelle résultante : 0 à 6
    # ──────────────────────────────────────────────────────────────────────────
    for col in ['habitat_transformation_hydrology',
                'habitat_transformation_soil',
                'habitat_transformation_structure']:
        gdf_EEE_enrichi[col] = gdf_EEE_enrichi[col].map({'oui': 1, 'non': 0}).fillna(0).astype(int)

    gdf_EEE_enrichi['transformation_score'] = (
        gdf_EEE_enrichi['habitat_transformation_hydrology'] * 3 +
        gdf_EEE_enrichi['habitat_transformation_soil']      * 2 +
        gdf_EEE_enrichi['habitat_transformation_structure'] * 1
    )

    # Affichage de contrôle par espèce
    print("Score de transformation par espèce EEE :")
    transfo_eee = (
        gdf_EEE_enrichi[[
            'species_name_sci',
            'habitat_transformation_hydrology',
            'habitat_transformation_soil',
            'habitat_transformation_structure',
            'transformation_score'
        ]]
        .drop_duplicates()
        .sort_values('transformation_score', ascending=False)
    )
    for _, row in transfo_eee.iterrows():
        print(f"  {row['species_name_sci']}: hydro={row['habitat_transformation_hydrology']}, "
              f"sol={row['habitat_transformation_soil']}, "
              f"structure={row['habitat_transformation_structure']} "
              f"→ score={row['transformation_score']}")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 4 — Catégorisation du score de transformation
    # 6       → maximal
    # 4–5     → fort
    # 2–3     → modéré
    # 1       → faible
    # 0       → nul  (EEE présente mais aucune transformation documentée)
    # ──────────────────────────────────────────────────────────────────────────
    def categoriser_transformation(valeur):
        try:
            if valeur == 6:   return 'maximal'
            elif valeur >= 4: return 'fort'
            elif valeur >= 2: return 'modéré'
            elif valeur == 1: return 'faible'
            else:             return 'nul'
        except:
            return None

    gdf_EEE_enrichi['categorie_transformation'] = gdf_EEE_enrichi['transformation_score'].apply(categoriser_transformation)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 5 — Éclatement des nom_plo_fi multi-valeurs + agrégation par tronçon
    # On garde la catégorie de transformation MAX par tronçon.
    # ──────────────────────────────────────────────────────────────────────────
    nb_avant = len(gdf_EEE_enrichi)
    gdf_EEE_enrichi = gdf_EEE_enrichi.assign(
        nom_plo_fi=gdf_EEE_enrichi['nom_plo_fi'].str.split(',')
    ).explode('nom_plo_fi')
    gdf_EEE_enrichi['nom_plo_fi'] = gdf_EEE_enrichi['nom_plo_fi'].str.strip()

    print(f"\nÉclatement nom_plo_fi : {nb_avant} lignes → {len(gdf_EEE_enrichi)} lignes")

    ordre_transformation = {'maximal': 4, 'fort': 3, 'modéré': 2, 'faible': 1, 'nul': 0}

    transformation_par_troncon = (
        gdf_EEE_enrichi[['nom_plo_fi', 'categorie_transformation']]
        .dropna(subset=['categorie_transformation'])
        .assign(transfo_rank=lambda x: x['categorie_transformation'].map(ordre_transformation))
        .sort_values('transfo_rank', ascending=False)
        .groupby('nom_plo_fi')
        .first()
        .reset_index()
        [['nom_plo_fi', 'categorie_transformation']]
    )


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 6 — Jointure avec df_scoring
    # Tronçons sans EEE → categorie_transformation = NaN → 'aucune'
    # ──────────────────────────────────────────────────────────────────────────
    df_scoring = df_scoring.merge(
        transformation_par_troncon,
        on='nom_plo_fi',
        how='left'
    )

    df_scoring['categorie_transformation'] = df_scoring['categorie_transformation'].fillna('aucune')


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 7 — Scoring N2_impact
    # maximal → 5 | fort → 4 | modéré → 3 | faible → 2 | nul → 1 | aucune EEE → 0
    # ──────────────────────────────────────────────────────────────────────────
    def attribuer_points_N2(row):
        cat = row['categorie_transformation']
        if cat == 'maximal': return 5
        if cat == 'fort':    return 4
        if cat == 'modéré':  return 3
        if cat == 'faible':  return 2
        if cat == 'nul':     return 1
        return 0  # aucune EEE

    df_scoring.loc[:, 'N2_impact'] = df_scoring.apply(attribuer_points_N2, axis=1)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 8 — Nettoyage colonne temporaire
    # ──────────────────────────────────────────────────────────────────────────
    df_scoring.drop(columns=['categorie_transformation'], inplace=True)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 9 — Statistiques de contrôle
    # ──────────────────────────────────────────────────────────────────────────
    nb_troncons_eee = gdf_EEE['nom_plo_fi'].nunique()
    nb_score_max    = (df_scoring['N2_impact'] == 5).sum()

    print(f"\nRésultats :")
    print(f"  Tronçons avec EEE : {nb_troncons_eee}")
    print(f"  Tronçons score max (5) : {nb_score_max}")
    print(f"  Distribution des scores :\n{df_scoring['N2_impact'].value_counts().sort_index()}")
    print(f"\n{'='*70}\n")

    return df_scoring
