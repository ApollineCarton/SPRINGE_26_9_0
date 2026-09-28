# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_N1_impact"
Date : 2026-02-17
Objectif : calculer l'indicateur N1 impact'
═══════════════════════════════════════════════════════════════════

Calcul de l'impact des EEE pour l'indicateur N1 - Proximité et menace sur zones naturelles sensibles.
Logique : croiser la présence d'EEE sur le tronçon avec le niveau de protection
          des zones naturelles adjacentes (dans gdf_troncons_copy colonnes Niv1 à Niv4).

Hiérarchie des niveaux (Niv1 > Niv2 > Niv3 > Niv4) :
    Niv1 : protection réglementaire stricte (RNN, APB, cœurs PN...)
    Niv2 : protection foncière (CEN, Conservatoire du Littoral...)
    Niv3 : protection contractuelle (Natura 2000, Ramsar...)
    Niv4 : inventaire (ZICO...)

Scoring :
    0 : absence EEE
    1 : présence EEE, N1_vulnerabilite = non (aucune zone naturelle adjacente)
    2 : présence EEE + N1_vulnerabilite = oui + Niv4 dominant
    3 : présence EEE + N1_vulnerabilite = oui + Niv3 dominant
    4 : présence EEE + N1_vulnerabilite = oui + Niv2 dominant
    5 : présence EEE + N1_vulnerabilite = oui + Niv1 dominant

Paramètres :
    - gdf_EEE : Gdf des points de présence EEE, colonnes 'nom_plo_fi' et géométrie
    - gdf_troncons_copy : Gdf des tronçons avec colonnes Niv1, Niv2, Niv3, Niv4 (entiers)
    - df_scoring : DF contenant les tronçons et N1_vulnerabilite (oui/non)

Sortie : nouvelle colonne 'N1_impact' dans df_scoring, valeurs entières de 0 à 5.
"""
import pandas as pd # merge(), apply(), isna(), value_count(), explode()

def calculer_N1_impact(gdf_EEE, gdf_troncons_copy, df_scoring):    

    print(f"\n{'='*70}")
    print("CALCUL N1_IMPACT - Proximité et menace EEE sur zones naturelles sensibles")
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
        
    if 'N1_vulnerabilite' not in df_scoring.columns:
        raise ValueError("❌ 'N1_vulnerabilite' introuvable dans df_scoring")
    
    for col in ['Niv1', 'Niv2', 'Niv3', 'Niv4']:
        if col not in gdf_troncons_copy.columns:
            raise ValueError(f"❌ '{col}' introuvable dans gdf_troncons_copy")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 — Identifier les tronçons colonisés par EEE
    # Même logique que P4 : on éclate les nom_plo_fi multi-valeurs
    # ──────────────────────────────────────────────────────────────────────────
    gdf_EEE_explode = gdf_EEE.copy()
    gdf_EEE_explode = gdf_EEE_explode.assign(
        nom_plo_fi=gdf_EEE_explode['nom_plo_fi'].str.split(',')
    ).explode('nom_plo_fi')
    gdf_EEE_explode['nom_plo_fi'] = gdf_EEE_explode['nom_plo_fi'].str.strip()

    troncons_colonises = set(gdf_EEE_explode['nom_plo_fi'].dropna().unique())
    print(f"Tronçons colonisés par EEE : {len(troncons_colonises)}")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Récupérer le niveau de protection max par tronçon
    # depuis gdf_troncons_copy (Niv1 > Niv2 > Niv3 > Niv4)
    # Un tronçon peut avoir plusieurs niveaux simultanément → on prend le plus protégé
    # Niv1 > 0 → niveau dominant = 1, sinon Niv2 > 0 → 2, etc.
    # ──────────────────────────────────────────────────────────────────────────
    def niveau_max_protection(row):
        if row['Niv1'] > 0: return 1
        if row['Niv2'] > 0: return 2
        if row['Niv3'] > 0: return 3
        if row['Niv4'] > 0: return 4
        return None  # aucune zone naturelle

    gdf_troncons_niv = gdf_troncons_copy[['nom_plo_fi', 'Niv1', 'Niv2', 'Niv3', 'Niv4']].copy()
    gdf_troncons_niv['niveau_protection'] = gdf_troncons_niv.apply(niveau_max_protection, axis=1)

    # Affichage de contrôle
    print("\nDistribution des niveaux de protection par tronçon :")
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
    # ÉTAPE 5 — Scoring N1_impact
    # Croisement : présence EEE × N1_vulnerabilite × niveau_protection
    # ──────────────────────────────────────────────────────────────────────────
    def attribuer_points_N1(row):
        colonise   = row['nom_plo_fi'] in troncons_colonises
        vuln       = row['N1_vulnerabilite']
        niveau     = row['niveau_protection']

        # Pas d'EEE → 0
        if not colonise:
            return 0

        # EEE présente mais pas de zone naturelle adjacente → 1
        if vuln == 'non' or pd.isna(niveau):
            return 1

        # EEE présente + zone naturelle → score selon niveau de protection
        if niveau == 1: return 5
        if niveau == 2: return 4
        if niveau == 3: return 3
        if niveau == 4: return 2

        return 1  # sécurité

    df_scoring.loc[:, 'N1_impact'] = df_scoring.apply(attribuer_points_N1, axis=1)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 6 — Nettoyage colonne temporaire
    # ──────────────────────────────────────────────────────────────────────────
    df_scoring.drop(columns=['niveau_protection'], inplace=True)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 7 — Statistiques de contrôle
    # ──────────────────────────────────────────────────────────────────────────
    nb_score_max = (df_scoring['N1_impact'] == 5).sum()

    print(f"\nRésultats :")
    print(f"  Tronçons colonisés par EEE : {len(troncons_colonises)}")
    print(f"  Tronçons score max (5) : {nb_score_max}")
    print(f"  Distribution des scores :")
    for score, count in df_scoring['N1_impact'].value_counts().sort_index().items():
        print(f"    Score {score} : {count} tronçons")
    print(f"\n{'='*70}\n")

    return df_scoring
