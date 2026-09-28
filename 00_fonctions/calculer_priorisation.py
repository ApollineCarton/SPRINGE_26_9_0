# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_priorisation"
Date : 2026-03-09
Objectif : calculer les tronçons prioritaires pour la gestion
═══════════════════════════════════════════════════════════════════
Calcul de la priorisation des tronçons sur 3 ans et export en GeoPackage.

Tri lexicographique pour les ex-aequo (justifié par la littérature MCDA) :
    1. score_troncon_final (critère principal)
    2. score_enjeu_MS (sécurité usagers — critère le plus immédiat)
    3. score_enjeu_P  (priorisation gestion)
    4. score_enjeu_N  (biodiversité)
    5. tirage aléatoire reproductible (seed fixe) si vraie égalité résiduelle
       → STB (Single Tie-Breaking), plus stable que MTB (cf. littérature)

Paramètres :
    - df_scoring        : DF contenant score_troncon_final et scores par enjeu
    - gdf_troncons_copy : Gdf des tronçons avec géométrie et nom_plo_fi
    - name              : str, nom du projet (ex: 'EEE_2026')
    - DIR               : str, nom de la DIR (ex: 'DIRO')
    - output_dir        : str, répertoire de sortie

Sortie :
    - df_scoring enrichi de 'annee_intervention' et 'rang_priorite'
    - fichier GeoPackage exporté dans output_dir
"""
import pandas as pd
import numpy as np
import geopandas as gpd
from datetime import date

def calculer_priorisation(df_scoring, gdf_troncons_copy, name, DIR, output_dir="."):
    

    print(f"\n{'='*70}")
    print("CALCUL PRIORISATION - Plan d'action 3 ans")
    print(f"{'='*70}\n")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1 — Vérification des colonnes nécessaires
    # ──────────────────────────────────────────────────────────────────────────
    cols_requises = ['nom_plo_fi', 'score_troncon_final',
                     'score_enjeu_MS', 'score_enjeu_N', 'score_enjeu_P']
    for col in cols_requises:
        if col not in df_scoring.columns:
            raise ValueError(f"❌ '{col}' introuvable dans df_scoring")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 — Tri lexicographique avec départage
    # Ordre : score_final > MS > P > N > aléatoire reproductible
    # ──────────────────────────────────────────────────────────────────────────
    RANDOM_SEED = 42  # seed fixe → résultats reproductibles d'un run à l'autre

    df_prio = df_scoring[cols_requises].copy()

    # Colonne de bruit aléatoire reproductible pour départager les vraies égalités
    rng = np.random.default_rng(seed=RANDOM_SEED)
    df_prio['_tiebreak_alea'] = rng.random(len(df_prio))

    # Tri lexicographique décroissant sur tous les critères
    df_prio = df_prio.sort_values(
        by=['score_troncon_final', 'score_enjeu_MS', 'score_enjeu_P',
            'score_enjeu_N', '_tiebreak_alea'],
        ascending=False
    ).reset_index(drop=True)

    # Rang de priorité (1 = plus prioritaire)
    df_prio['rang_priorite'] = df_prio.index + 1

    # Diagnostic ex-aequo : combien de tronçons ont le même score final ?
    nb_exaequo = df_prio.duplicated(
        subset=['score_troncon_final', 'score_enjeu_MS', 'score_enjeu_P', 'score_enjeu_N'],
        keep=False
    ).sum()
    print(f"Tronçons avec égalité résiduelle (départagés par tirage) : {nb_exaequo}")
    if nb_exaequo > 0:
        print(f"  → Seed aléatoire utilisé : {RANDOM_SEED} (résultats reproductibles)")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Attribution des années d'intervention
    # N%3 tronçons excédentaires → année 1 (gestion anticipée)
    # ──────────────────────────────────────────────────────────────────────────
    N            = len(df_prio)
    taille_base  = N // 3
    excedent     = N % 3

    taille_an1 = taille_base + excedent
    taille_an2 = taille_base
    taille_an3 = taille_base

    df_prio['annee_intervention'] = 0
    df_prio.loc[df_prio.index < taille_an1,
                'annee_intervention'] = 1
    df_prio.loc[(df_prio.index >= taille_an1) &
                (df_prio.index < taille_an1 + taille_an2),
                'annee_intervention'] = 2
    df_prio.loc[df_prio.index >= taille_an1 + taille_an2,
                'annee_intervention'] = 3

    print(f"\nNombre total de tronçons : {N} (excédent N%3={excedent} → année 1)")
    for annee in [1, 2, 3]:
        sous = df_prio[df_prio['annee_intervention'] == annee]
        print(f"  Année {annee} : {len(sous)} tronçons | "
              f"score [{sous['score_troncon_final'].min():.1f}"
              f" → {sous['score_troncon_final'].max():.1f}]")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 4 — Rapatrier annee_intervention et rang_priorite dans df_scoring
    # ──────────────────────────────────────────────────────────────────────────

    # Nettoyage colonne technique avant merge
    df_prio = df_prio.drop(columns=['_tiebreak_alea'])

    df_scoring = df_scoring.merge(
        df_prio[['nom_plo_fi', 'rang_priorite', 'annee_intervention']],
        on='nom_plo_fi',
        how='left'
    )


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 5 — Jointure spatiale avec gdf_troncons_copy
    # ──────────────────────────────────────────────────────────────────────────
    cols_localisation = [col for col in gdf_troncons_copy.columns if col != 'geometry']
    print(f"\nColonnes de localisation récupérées : {cols_localisation}")

    cols_export = ['nom_plo_fi', 'score_enjeu_MS', 'score_enjeu_N', 'score_enjeu_P',
                   'score_troncon_final', 'rang_priorite', 'annee_intervention']

    gdf_export = gdf_troncons_copy[cols_localisation + ['geometry']].merge(
        df_scoring[cols_export],
        on='nom_plo_fi',
        how='inner'
    )

    if not isinstance(gdf_export, gpd.GeoDataFrame):
        gdf_export = gpd.GeoDataFrame(gdf_export, geometry='geometry',
                                      crs=gdf_troncons_copy.crs)


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 6 — Export GeoPackage
    # ──────────────────────────────────────────────────────────────────────────
    date_jour    = date.today().strftime('%Y%m%d')
    nom_couche   = f"plan_priorisation_{name}_{DIR}_{date_jour}"
    nom_fichier  = f"{nom_couche}.gpkg"
    chemin_export = f"{output_dir}\\{nom_fichier}"

    gdf_export.to_file(chemin_export, layer=nom_couche, driver='GPKG')

    print(f"\n✅ Export réussi :")
    print(f"   Fichier  : {nom_fichier}")
    print(f"   Couche   : {nom_couche}")
    print(f"   Tronçons : {len(gdf_export)}")
    print(f"   Chemin   : {chemin_export}")
    print(f"\n{'='*70}\n")

    return df_scoring, gdf_export