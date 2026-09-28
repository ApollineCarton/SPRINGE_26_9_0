# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "import_sig"
Date : 2026-02-17
Objectif : Importer les données SIG stockées en local
═══════════════════════════════════════════════════════════════════

Charge une couche SIG avec bbox par défaut (emprise_zone calculée par get_emprise_zone)
+ affichage infos
+ reprojection systématique en Lambert

permet de simplifier l'import de couches SIG contenues dans l'ordinateur, aulieu du bloc de code qui se répète :

-------------------------------------------------------------------------------------------------------------------------------------------
# Unités spatiales (=points repères) / tronçons d'intervention
PATH_TRONCONS = r"R:\ECHANGE\DOSSIER_CARTO_Alix\carte_OAD\TRONCONS_DIR\reseau_par_DIR\Troncons_DIR_tampon_ZoneA_B_C.shp"
check_path(PATH_TRONCONS, "tronçons")
print("Chargement unité spatiales -- tronçons/points repères ...")
gdf_troncons = gpd.read_file(PATH_TRONCONS, bbox=(minx, miny, maxx, maxy)) # gpd.read_file lit les fichiers SIG (shapefile, geojson, etc.)
gdf indique GeoDataFrame
print(f" -> {len(gdf_troncons)} troncons chargés")
print(f" -> Projection : {gdf_troncons.crs}") # .crs = le système de coordonnées (projection spatiale)
gdf_troncons = reprojeter_en_lambert(gdf_troncons, "tronçons")
-------------------------------------------------------------------------------------------------------------------------------------------

            ===========
            ! WARNING !
            ===========
            la fonction import_sig commande l'appel des fonctions check_path et reprojeter_en_lambert !!!
"""
import check_path
import reprojeter_en_lambert

def import_sig(path, nom_couche):
    check_path(path, nom_couche)

    print(f"Chargement unités spatiales -- {nom_couche} ...")

    # Si la bbox globale existe, on l'utilise
    try:
        bbox = (minx, miny, maxx, maxy)
        gdf = gpd.read_file(path, bbox=bbox)
    except NameError:
        # Si minx/miny/... ne sont pas définis
        gdf = gpd.read_file(path)

    print(f" -> {len(gdf)} {nom_couche} chargés")
    print(f" -> Projection : {gdf.crs}")

    # Reprojection systématique
    gdf = reprojeter_en_lambert(gdf, nom_couche)

    return gdf