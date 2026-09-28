# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""


"""
═══════════════════════════════════════════════════════════════════
Fonction "deduplication_troncons"
Date : 2026-02-17
Objectif : Dédupliquer les polygones ayant le même identifiant de tronçon
═══════════════════════════════════════════════════════════════════

Le fichier contenant les unités spatiales peuvent présenter plusieurs polygones avec le même identifiant de tronçon
Cela pose problème pour la suite des calculs 
--> Solution trouvée : homogénéiser les polygones selon leur numéro d'identifiants pour éviter des duplcats

Deux modes disponibles :
    - 'fusion' : union géométrique des polygones → 1 seul polygone par identifiant de tronçon
                 (emprise totale, peut créer des multipolygones si non contigus)
    - 'suffixe' : suffixe alphabétique ajouté à l'identifiant → FB1_a, FB1_b...
                 (géométries originales conservées, identifiant unique par polygone)

Paramètres :
    - gdf_troncons : GeoDataFrame des tronçons
    - colonne_id   : str, nom de la colonne identifiant (défaut : 'nom_plo_fi')
    - mode         : str, 'fusion' ou 'suffixe' (défaut : 'fusion')

Sortie :
    - GeoDataFrame dédupliqué
"""
import string
from shapely.ops import unary_union
import geopandas as gpd

#on va travailler avec la copie de gdf_troncon (=gdf_troncons_copy) pour tout le projet afin de ne pas modifier la couche initiale
def deduplication_troncons(gdf_troncons, colonne_id='nom_plo_fi', mode='fusion'):
    
    print(f"\n{'='*70}")
    print(f"DÉDUPLICATION TRONÇONS — mode : {mode.upper()}")
    print(f"{'='*70}\n")

    # ──────────────────────────────────────────────────────────────────────────
    # Vérifications
    # ──────────────────────────────────────────────────────────────────────────
    if colonne_id not in gdf_troncons.columns:
        raise ValueError(f"❌ '{colonne_id}' introuvable dans gdf_troncons")
    if mode not in ['fusion', 'suffixe']:
        raise ValueError(f"❌ mode '{mode}' invalide — utiliser 'fusion' ou 'suffixe'")

    nb_avant   = len(gdf_troncons)
    nb_uniques = gdf_troncons[colonne_id].nunique()
    nb_doublons = nb_avant - nb_uniques

    print(f"Lignes avant       : {nb_avant}")
    print(f"Identifiants uniques : {nb_uniques}")
    print(f"Polygones en doublon : {nb_doublons}")

    # ──────────────────────────────────────────────────────────────────────────
    # Si pas de doublons : rien à faire
    # ──────────────────────────────────────────────────────────────────────────
    if nb_doublons == 0:
        print(f"\n✅ Aucun doublon détecté — GeoDataFrame retourné sans modification")
        print(f"{'='*70}\n")
        return gdf_troncons.copy()

    # ──────────────────────────────────────────────────────────────────────────
    # MODE FUSION — union géométrique par identifiant
    # ──────────────────────────────────────────────────────────────────────────
    if mode == 'fusion':

        cols_attributaires = [col for col in gdf_troncons.columns
                              if col not in ['geometry', colonne_id]]

        gdf_resultat = (
            gdf_troncons
            .groupby(colonne_id, as_index=False)
            .agg(
                geometry=(  'geometry', unary_union),
                **{col: (col, 'first') for col in cols_attributaires}
            )
        )

        gdf_resultat = gpd.GeoDataFrame(
            gdf_resultat,
            geometry='geometry',
            crs=gdf_troncons.crs
        )

        # Statistiques sur les multipolygones créés
        nb_multi = gdf_resultat['geometry'].geom_type.eq('MultiPolygon').sum()

        print(f"\nRésultat :")
        print(f"  Lignes après fusion     : {len(gdf_resultat)}")
        print(f"  Multipolygones créés    : {nb_multi} "
              f"(polygones non contigus — normaux pour les échangeurs)")

    # ──────────────────────────────────────────────────────────────────────────
    # MODE SUFFIXE — suffixe alphabétique reproductible
    # ──────────────────────────────────────────────────────────────────────────
    elif mode == 'suffixe':

        def generer_suffixe(i):
            """Génère un suffixe alphabétique : 0→a, 1→b... 25→z, 26→aa..."""
            lettres = string.ascii_lowercase
            if i < 26:
                return lettres[i]
            return lettres[(i // 26) - 1] + lettres[i % 26]

        gdf_resultat = gdf_troncons.copy()

        # Conserver l'identifiant original dans une colonne dédiée
        gdf_resultat[f'{colonne_id}_original'] = gdf_resultat[colonne_id]

        # Rang de chaque polygone dans son groupe (0, 1, 2...)
        # sort=False : ordre stable → même suffixe à chaque run
        rang = gdf_resultat.groupby(colonne_id, sort=False).cumcount()

        # Identifier les tronçons avec plusieurs polygones
        nb_par_troncon = gdf_resultat.groupby(colonne_id)[colonne_id].transform('count')
        masque_doublons = nb_par_troncon > 1

        # Appliquer le suffixe uniquement aux tronçons dupliqués
        gdf_resultat.loc[masque_doublons, colonne_id] = (
            gdf_resultat.loc[masque_doublons, colonne_id] + '_' +
            rang[masque_doublons].apply(generer_suffixe)
        )

        print(f"\nRésultat :")
        print(f"  Lignes après suffixe    : {len(gdf_resultat)} (inchangé)")
        print(f"  Identifiants uniques    : {gdf_resultat[colonne_id].nunique()}")
        print(f"\n  Exemple (5 premiers doublons traités) :")
        exemple = gdf_resultat[gdf_resultat[f'{colonne_id}_original'] == 'FB1'][
            [colonne_id, f'{colonne_id}_original']
        ].head(5)
        print(exemple.to_string(index=False))

    print(f"\n{'='*70}\n")
    return gdf_resultat
