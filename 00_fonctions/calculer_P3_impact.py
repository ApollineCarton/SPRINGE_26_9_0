# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_P3_impact"
Date : 2026-02-17
Objectif : calculer l'indicateur P3 impact'
═══════════════════════════════════════════════════════════════════

Calcul de l'impact des EEE pour l'indicateur P3 - Proximité et menace sur zones naturelles sensibles.
Logique : croiser la présence d'EEE sur le tronçon avec le niveau de protection
          des zones naturelles adjacentes (dans gdf_troncons_copy colonnes Niv1 à Niv4).

Hiérarchie des niveaux (Niv1 > Niv2 > Niv3 > Niv4) :
    Niv1 : protection réglementaire stricte (RNN, APB, cœurs PN...)
    Niv2 : protection foncière (CEN, Conservatoire du Littoral...)
    Niv3 : protection contractuelle (Natura 2000, Ramsar...)
    Niv4 : inventaire (ZICO...)

Scoring :
    +2 : EEE présente ET P2 ≥ 2 ET Niv1 ou Niv2 dans tampon 200m
    +1 : EEE présente ET P2 ≥ 2 ET Niv3 ou Niv4 dans tampon 200m
    +0 : absence EEE, ou P2 < 2, ou aucune zone naturelle

Paramètres :
    - gdf_EEE : Gdf des points de présence EEE, colonnes 'nom_plo_fi' et géométrie
    - gdf_troncons_copy : Gdf des tronçons avec colonnes Niv1_propagation, Niv2_propagation, etc (suffixe à 200m)
    - df_scoring : DF contenant les tronçons et P3_vulnerabilite (oui/non)

Sortie : nouvelle colonne 'P3_impact' dans df_scoring, valeurs entières de 0 à 2.
"""
import pandas as pd

def calculer_P3_impact(gdf_EEE, gdf_troncons_copy, df_scoring):    

    print(f"\n{'='*70}")
    print("CALCUL P3_IMPACT - Proximité et menace EEE sur zones naturelles sensibles")
    print(f"{'='*70}\n")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1 — Vérification des colonnes nécessaires
    # ──────────────────────────────────────────────────────────────────────────
    if 'nom_plo_fi' not in gdf_EEE.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_EEE")
        
    if 'nom_plo_fi' not in gdf_troncons_copy.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_troncons_copy")
        
    if 'nom_plo_fi' not in df_scoring.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans df_scoring")
        
    if 'P3_vulnerabilite' not in df_scoring.columns:
        raise ValueError("❌ 'P3_vulnerabilite' introuvable dans df_scoring")
    
    # ✅ CORRECTION : chercher les colonnes à 200m (suffixées)
    # Essayer plusieurs suffixes possibles (selon config du lanceur)
    suffixes_candidats = ['_propagation', '_proximite', '']
    colonnes_niv = None
    suffixe_use = None
    
    for suffixe in suffixes_candidats:
        cols = [f'Niv{i}{suffixe}' for i in [1,2,3,4]]
        if all(col in gdf_troncons_copy.columns for col in cols):
            colonnes_niv = cols
            suffixe_use = suffixe
            break
    
    if colonnes_niv is None:
        niv_cols = [col for col in gdf_troncons_copy.columns if 'Niv' in col]
        raise ValueError(
            f"❌ Colonnes P3 (Niv1-Niv4 à 200m) non trouvées. \n"
            f"Colonnes Niv* disponibles : {niv_cols} \n"
            f"Vérifier l'appel detecter_elements_sur_troncon(tampon=200) au lanceur"
        )
    
    print(f"✅ Colonnes P3 détectées (200m) : {colonnes_niv}")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 — Identifier les tronçons colonisés par EEE
    # Même logique que N1 : on éclate les nom_plo_fi multi-valeurs
    # ──────────────────────────────────────────────────────────────────────────
    gdf_EEE_explode = gdf_EEE.copy()
    gdf_EEE_explode = gdf_EEE_explode.assign(
        nom_plo_fi=gdf_EEE_explode['nom_plo_fi'].str.split(',')
    ).explode('nom_plo_fi')
    gdf_EEE_explode['nom_plo_fi'] = gdf_EEE_explode['nom_plo_fi'].str.strip()

    troncons_colonises = set(gdf_EEE_explode['nom_plo_fi'].dropna().unique())
    print(f"Tronçons colonisés par EEE : {len(troncons_colonises)}")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Récupérer le niveau de protection max par tronçon (à 200m)
    # Niv1 > Niv2 > Niv3 > Niv4
    # ──────────────────────────────────────────────────────────────────────────
    def niveau_max_protection(row):
        for i in [1, 2, 3, 4]:
            col = f'Niv{i}{suffixe_use}'
            if row[col] > 0:
                return i
        return None

    gdf_troncons_niv = gdf_troncons_copy[['nom_plo_fi'] + colonnes_niv].copy()
    gdf_troncons_niv['niveau_protection'] = gdf_troncons_niv.apply(niveau_max_protection, axis=1)

    print("\nDistribution des niveaux de protection (à 200m) par tronçon :")
    print(gdf_troncons_niv['niveau_protection'].value_counts(dropna=False).sort_index())


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 4 — Jointure niveau_protection dans df_scoring
    # ──────────────────────────────────────────────────────────────────────────
    df_scoring = df_scoring.merge(
        gdf_troncons_niv[['nom_plo_fi', 'niveau_protection']],
        on='nom_plo_fi',
        how='left'
    )


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 5 — Scoring P3_impact
    # Croisement : présence EEE × P2 ≥ 2 × niveau_protection
    # ──────────────────────────────────────────────────────────────────────────
    def attribuer_points_P3(row):
        colonise   = row['nom_plo_fi'] in troncons_colonises
        vuln       = row['P3_vulnerabilite']
        niveau     = row['niveau_protection']
        p2_score   = row.get('P2_impact', 0)  # Récupérer P2 (calculé avant P3)

        # Pas d'EEE → 0
        if not colonise:
            return 0

        # EEE mais P2 < 2 (pas de vecteur de dispersion) → 0
        if p2_score < 2:
            return 0

        # EEE + P2 ≥ 2 mais pas de zone naturelle → 0
        if vuln == 'non' or pd.isna(niveau):
            return 0

        # EEE + P2 ≥ 2 + zone naturelle → scoring selon niveau de protection (à 200m)
        if niveau in [1, 2]:  # Niv1-2 = protection très forte
            return 2
        if niveau in [3, 4]:  # Niv3-4 = protection plus faible
            return 1

        return 0

    df_scoring.loc[:, 'P3_impact'] = df_scoring.apply(attribuer_points_P3, axis=1)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 6 — Nettoyage colonne temporaire
    # ──────────────────────────────────────────────────────────────────────────
    df_scoring.drop(columns=['niveau_protection'], inplace=True)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 7 — Statistiques de contrôle
    # ──────────────────────────────────────────────────────────────────────────
    nb_score_2 = (df_scoring['P3_impact'] == 2).sum()
    nb_score_1 = (df_scoring['P3_impact'] == 1).sum()

    print(f"\nRésultats :")
    print(f"  Tronçons colonisés par EEE : {len(troncons_colonises)}")
    print(f"  Score +2 (Niv1-2) : {nb_score_2} tronçons")
    print(f"  Score +1 (Niv3-4) : {nb_score_1} tronçons")
    print(f"  Distribution des scores :")
    for score, count in df_scoring['P3_impact'].value_counts().sort_index().items():
        print(f"    Score {score} : {count} tronçons")
    print(f"\n{'='*70}\n")

    return df_scoring
