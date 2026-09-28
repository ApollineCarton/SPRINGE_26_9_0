# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""


"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_score_final"
Date : 2026-02-17
Objectif : calculer les scores finaux de chaque tronçons à partir des points indicateurs
═══════════════════════════════════════════════════════════════════

Calcul des scores finaux par enjeu puis score global du tronçon.
    
    Logique :
        1. score_enjeu_MS = somme des MS*_impact (coefficients ajustables)
        2. score_enjeu_N  = somme des N*_impact  (coefficients ajustables)
        3. score_enjeu_P  = somme des P*_impact  (coefficients ajustables)
        4. score_troncon_final = score_enjeu_MS + score_enjeu_N + score_enjeu_P
                                 (avec coefficient par enjeu, ajustable)

    Paramètres :
        - df_scoring : DF contenant toutes les colonnes *_impact

    Sortie : df_scoring enrichi des colonnes score_enjeu_* et score_troncon_final
   
"""
import pandas as pd

def calculer_score_final(df_scoring):

    print(f"\n{'='*70}")
    print("CALCUL SCORES FINAUX - Par enjeu puis score global tronçon")
    print(f"{'='*70}\n")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1 — Détection dynamique des colonnes *_impact par enjeu
    # On groupe automatiquement les colonnes par préfixe (MS, N, P)
    # → flexible si de nouveaux indicateurs sont ajoutés plus tard
    # ──────────────────────────────────────────────────────────────────────────
    cols_impact = [col for col in df_scoring.columns if col.endswith('_impact')]

    cols_MS = [col for col in cols_impact if col.startswith('MS')]
    cols_N  = [col for col in cols_impact if col.startswith('N')]
    cols_P  = [col for col in cols_impact if col.startswith('P')]

    print(f"Indicateurs MS détectés : {cols_MS}")
    print(f"Indicateurs N  détectés : {cols_N}")
    print(f"Indicateurs P  détectés : {cols_P}")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 — Coefficients par indicateur
    # Tous à 1 pour l'instant — à ajuster selon la hiérarchie des enjeux
    # ──────────────────────────────────────────────────────────────────────────
    coef_indicateurs = {col: 1 for col in cols_impact}

    # Exemple futur pour pondérer :
    # coef_indicateurs['MS1_impact'] = 1.5
    # coef_indicateurs['N2_impact']  = 0.8

    print(f"\nCoefficients indicateurs : {coef_indicateurs}")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Coefficients par enjeu
    # Tous à 1 pour l'instant — à ajuster selon la priorité des enjeux
    # ──────────────────────────────────────────────────────────────────────────
    coef_enjeux = {
        'MS': 1,
        'N':  1,
        'P':  1
    }

    # Exemple futur pour pondérer :
    # coef_enjeux['MS'] = 1.5   # enjeu sécurité routière prioritaire
    # coef_enjeux['N']  = 0.8

    print(f"Coefficients enjeux      : {coef_enjeux}")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 4 — Calcul des scores par enjeu
    # score_enjeu = somme(indicateur × coef_indicateur) × coef_enjeu
    # ──────────────────────────────────────────────────────────────────────────
    def score_enjeu(cols):
        return sum(df_scoring[col] * coef_indicateurs[col] for col in cols)

    df_scoring['score_enjeu_MS'] = score_enjeu(cols_MS) * coef_enjeux['MS']
    df_scoring['score_enjeu_N']  = score_enjeu(cols_N)  * coef_enjeux['N']
    df_scoring['score_enjeu_P']  = score_enjeu(cols_P)  * coef_enjeux['P']

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 5 — Score final du tronçon
    # ──────────────────────────────────────────────────────────────────────────
    df_scoring['score_troncon_final'] = (
        df_scoring['score_enjeu_MS'] +
        df_scoring['score_enjeu_N']  +
        df_scoring['score_enjeu_P']
    )

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 6 — Statistiques de contrôle
    # ──────────────────────────────────────────────────────────────────────────
    # Vérification : toutes les colonnes *_impact présentes dans df_scoring ?
    print("─" * 50)
    print("VÉRIFICATION — Colonnes *_impact dans df_scoring :")
    cols_impact_presentes = [col for col in df_scoring.columns if col.endswith('_impact')]
    cols_impact_manquantes = [col for col in cols_impact if col not in df_scoring.columns]
    print(f"  Toutes les colonnes détectées : {cols_impact_presentes}")
    if cols_impact_manquantes:
        print(f"  ⚠️  Colonnes manquantes : {cols_impact_manquantes}")
    else:
        print(f"  ✅ Toutes les colonnes sont présentes dans df_scoring")

    # Détail de la composition par enjeu
    print("\n─" * 50)
    print("COMPOSITION DES SCORES PAR ENJEU :")
    print(f"\n  enjeu MS (coef enjeu × {coef_enjeux['MS']}) :")
    for col in cols_MS:
        print(f"    + {col} × {coef_indicateurs[col]}")

    print(f"\n  enjeu N (coef enjeu × {coef_enjeux['N']}) :")
    for col in cols_N:
        print(f"    + {col} × {coef_indicateurs[col]}")

    print(f"\n  enjeu P (coef enjeu × {coef_enjeux['P']}) :")
    for col in cols_P:
        print(f"    + {col} × {coef_indicateurs[col]}")

    print(f"\n  score_troncon_final = score_enjeu_MS + score_enjeu_N + score_enjeu_P")

    # Scores max théoriques
    print("\n─" * 50)
    print("SCORES MAX THÉORIQUES :")
    score_max_MS = sum(5 * coef_indicateurs[c] for c in cols_MS) * coef_enjeux['MS']
    score_max_N  = sum(5 * coef_indicateurs[c] for c in cols_N)  * coef_enjeux['N']
    score_max_P  = sum(4 * coef_indicateurs[c] for c in cols_P)  * coef_enjeux['P']
    print(f"  MS  : {score_max_MS}")
    print(f"  N   : {score_max_N}")
    print(f"  P   : {score_max_P}")
    print(f"  TOTAL max théorique : {score_max_MS + score_max_N + score_max_P}")

    # Distribution finale
    print("\n─" * 50)
    print("DISTRIBUTION score_troncon_final :")
    print(f"{df_scoring['score_troncon_final'].describe()}")
    print(f"\n{'='*70}\n")

    return df_scoring
