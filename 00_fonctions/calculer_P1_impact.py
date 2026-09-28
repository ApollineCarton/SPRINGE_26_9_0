# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_P1_impact"
Date : 2026-02-17
Objectif : calculer l'indicateur P1 impact'
═══════════════════════════════════════════════════════════════════

on a pas besoin de faire une jointure spatiale avec gdf_troncons car on a deja l'info dans gdf_EEE grace à une jointure précédente

Bonus P1 : Espèce avec fort potentiel invasif

Logique :
- Tronçon a au moins 1 EEE avec invasive_potential_score > seuil
- Jointure gdf_EEE (colonne 'species_name_sci') ↔ EEE_SHEET (colonne à identifier)

Paramètres :
-----------
gdf_EEE : GeoDataFrame des points EEE (avec 'nom_plo_fi' et 'species_name_sci')
EEE_caracterisques_excel : DataFrame des caractéristiques EEE
df_scoring : DataFrame de scoring
seuil_invasif : float, seuil de potentiel invasif (défaut=0.7)
"""
import pandas as pd

def calculer_P1_impact(gdf_EEE, EEE_caracterisques_excel, df_scoring, seuil_invasif=0.7):
    
    
    print(f"\n{'='*70}")
    print("CALCUL P1_IMPACT - BONUS POTENTIEL INVASIF")
    print(f"{'='*70}\n")
    
    # Vérifier colonnes
    if 'nom_plo_fi' not in gdf_EEE.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_EEE")
    
    if 'species_name_sci' not in gdf_EEE.columns:
        raise ValueError(
            "❌ 'species_name_sci' introuvable dans gdf_EEE. "
            "fenetre_mapping_especes.mapping_interactif_especes() doit être "
            "appelée avant ce module."
        )
    
    if 'invasive_potential_score' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'invasive_potential_score' introuvable dans EEE_caracterisques_excel")
    
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
    
    # Jointure avec EEE_SHEET pour récupérer invasive_potential_score
    gdf_EEE_enrichi = gdf_EEE_mapped.merge(
        EEE_caracterisques_excel[['species_name_sci', 'invasive_potential_score']],
        on='species_name_sci',
        how='left'
    )

    # BUG CORRIGÉ #1 : invasive_potential_score lu comme string depuis l'Excel
    # pd.to_numeric force la conversion en float
    # errors='coerce' : valeurs non convertibles → NaN (filtre > seuil retourne False)
    gdf_EEE_enrichi['invasive_potential_score'] = pd.to_numeric(
        gdf_EEE_enrichi['invasive_potential_score'], errors='coerce'
    )
    
    print(f"\n📋 Scores invasifs par espèce :")
    scores_par_espece = (
        gdf_EEE_enrichi[['species_name_sci', 'invasive_potential_score']]
        .drop_duplicates()
        .sort_values('invasive_potential_score', ascending=False)
    )
    for _, row in scores_par_espece.iterrows():
        print(f"   • {row['species_name_sci']}: {row['invasive_potential_score']}")

    # BUG CORRIGÉ #2 : nom_plo_fi multi-valeurs non éclatées
    # ex: "35PR12D, 35PR12G" → deux lignes séparées
    # sans ça, isin() ne trouve jamais de correspondance avec df_scoring
    gdf_EEE_enrichi = gdf_EEE_enrichi.assign(
        nom_plo_fi=gdf_EEE_enrichi['nom_plo_fi'].str.split(',')
    ).explode('nom_plo_fi')
    gdf_EEE_enrichi['nom_plo_fi'] = gdf_EEE_enrichi['nom_plo_fi'].str.strip()

    # Filtrer les EEE avec score > seuil
    eee_invasives = gdf_EEE_enrichi[
        gdf_EEE_enrichi['invasive_potential_score'] > seuil_invasif
    ]
    
    print(f"\n✅ Espèces avec score > {seuil_invasif} :")
    for esp in eee_invasives['species_name_sci'].unique():
        score = eee_invasives[eee_invasives['species_name_sci'] == esp]['invasive_potential_score'].iloc[0]
        print(f"   • {esp} (score = {score})")
    
    # Trouver les tronçons avec ces espèces invasives
    troncons_avec_invasives = eee_invasives['nom_plo_fi'].unique()
    
    # Par défaut : pas de bonus
    df_scoring['P1_impact'] = 0
    
    # Attribuer le bonus
    df_scoring.loc[
        df_scoring['nom_plo_fi'].isin(troncons_avec_invasives),
        'P1_impact'
    ] = 1
    
    # Statistiques
    nb_bonus = (df_scoring['P1_impact'] == 1).sum()
    nb_troncons_avec_eee = gdf_EEE['nom_plo_fi'].nunique()
    
    print(f"\n📊 Résultats :")
    print(f"   • Tronçons avec EEE : {nb_troncons_avec_eee}")
    print(f"   • Tronçons avec EEE invasives : {len(troncons_avec_invasives)}")
    print(f"   • ✅ Bonus P1 attribués : {nb_bonus}")
    
    print(f"\n{'='*70}\n")

    # BUG CORRIGÉ #3 : la fonction ne retournait pas df_scoring
    # → les modifications étaient perdues à la sortie de la fonction
    return df_scoring
