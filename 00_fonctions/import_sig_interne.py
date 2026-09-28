# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "import_sig_interne"
Date : 2026-03-18
Objectif : importer toutes les couches SIG d'un dossier en local
# et les nommer selon le dossier parent
═══════════════════════════════════════════════════════════════════

Charge tous les fichiers .shp ou .gpkg contenus dans un dossier.
Chaque GeoDataFrame sera stocké dans un dict avec clé = nom du dossier parent.

Parameters
----------
dossier : str ou Path
    Chemin du dossier contenant les fichiers SIG
reproj : bool
    Si True, reprojette en Lambert 93
bbox : tuple
    (minx, miny, maxx, maxy) pour filtrer les fichiers

Returns

PS : il faut utiliser .rglob() au lieu de .glob() pour avoir une recherche récursive des sous dossiers
-------
dict
    Dictionnaire : {nom_du_dossier_parent : GeoDataFrame}
"""
from pathlib import Path
import geopandas as gpd
from reprojeter_en_lambert import reprojeter_en_lambert

def import_sig_interne(dossier, reproj=True, bbox=None):
    
    
    dossier = Path(dossier)
    sig_dict = {}
    
    # Nom du dossier parent (pour la clé)
    nom_parent = dossier.name
    
    # Boucle récurssive sur tous les fichiers shapefile et gpkg dans lessous-dossiers
    for fichier in dossier.rglob("*.*"):
        if fichier.suffix.lower() not in [".shp", ".gpkg", ".geojson"]:
            continue
        
        
        #Clé : nom du dossier parent (ex: gdf_carrefour)
        nom_cle = fichier.parent.name
        
        print(f"Chargement de la couche : {fichier.name} -> clé '{nom_cle}' ...")
        
        # Charger le fichier
        if bbox:
            gdf = gpd.read_file(fichier, bbox=bbox)
        else:
            gdf = gpd.read_file(fichier)
        
        # Reprojection systématique
        if reproj:
            gdf = reprojeter_en_lambert(gdf, nom_parent)
        
        
        # Stocker dans le dict avec clé = nom du dossier parent
        sig_dict[nom_cle] = gdf
        
        print(f"{nom_cle} chargé ({len(gdf)} entités)")
        
        print(f"{fichier.name} chargé")
    
    print(f"\nToutes les couches du dossier '{nom_parent}' ont été chargées !\n")
    return sig_dict