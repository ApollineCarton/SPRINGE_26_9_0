# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
- fonction reprojeter_en_lambert :configurer crs en L93

═══════════════════════════════════════════════════════════════════
Fonction "reprojeter_en_lambert"
Date : 2026-01-16
Objectif : Harmoniser la projection des couches SIG vers Lambert 93
═══════════════════════════════════════════════════════════════════

NB : choix de Lambert 93 qui est en métrique (mètres) (nécéssaire pour faire des buffer avec un rayon en mètres). Voir quelle autre projection choisir pour un usage européen (Lambert  étant la projection française)

Fonction qui vérifie la projection d'un GeoDataFrame et le reprojette en Lambert 93 si besoin.
Important car les calculs de distance (buffer, intersect) nécéssitent d'être dans un système métrique et similaire entre les couches SIG
-> Lambert 93 est le système officiel en France métropolitaine (unité = mètre)
-> mélanger des projections différentes assure des résultats faux !!

Arguments :
    - gdf : geopandas.GeoDataFrame, c'est la couche à reprojeter
    - nom_couche : str, c'est le nom descriptif de la couche à l'affichage
Retourne :
    - GeoDataFrame : la couche reprojetée dans le sytème L93
    target_crs : str
        CRS cible (ici EPSG:2154)
        -> EPSG:4326 = WGS84 (lat/long en degrés) - global
        -> EPSG:2154 = RGF93 / Lambert 93 (X/Y en mètres)
"""

import geopandas as gpd

# fonction projection
def reprojeter_en_lambert(gdf, nom_couche="couche", target_epsg=2154):

    print(f"\n Vérification projection {nom_couche}...")
    print(f" Projection actuelle : {gdf.crs}\n")

    # CAS 1 : CRS absent → on le DÉCLARE (pas de reprojection)
    if gdf.crs is None:
        print(f"⚠️ CRS manquant pour {nom_couche} → déclaration EPSG:{target_epsg}\n")
        gdf = gdf.set_crs(epsg=target_epsg)
        return gdf

    # CAS 2 : CRS présent mais différent → reprojection
    if gdf.crs.to_epsg() != target_epsg:
        print(f"🔄 Reprojection {nom_couche} vers EPSG:{target_epsg}\n")
        gdf = gdf.to_crs(epsg=target_epsg)

    else:
        print(f"✓ {nom_couche} déjà en EPSG:{target_epsg}\n")

    return gdf
