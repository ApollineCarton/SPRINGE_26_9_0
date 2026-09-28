# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "get_emprise_zone"
Date : 2026-02-17
Objectif : Charger les données SIG à l'emprise du projet pour ne pas alourdir plus que de raison
═══════════════════════════════════════════════════════════════════

Détermine l'emprise de la zone d'étude pour le traitement SIG.
libraries : import geopandas as gpd ; from pathlib import Path
    
Principe :
    - Cherche un dossier contenant les fichiers d'emprise (*.shp ou *.gpkg)
    - Si plusieurs polygones sont présents, fusionne en un polygone unique
    - Si nécessaire, applique un tampon autour du polygone
    - Retourne un GeoDataFrame prêt à être utilisé pour le découpage
    
Paramètres de la fonction:
    taille_tampon_km (float): taille du tampon autour du polygone en km (default=2km)
    
Retour de la fonction :
    gpd.GeoDataFrame: un GeoDataFrame avec l'emprise de la zone d'étude
"""

def get_emprise_zone(taille_tampon_km=2):
    
    # 🔹 Définir le chemin du dossier emprise
    dossier_emprise = Path(r"\\ad.intra\dfs\COMMUNS\CENTRAL\DGD-PCE\DRAS\FV\5_EEE\Apolline Carton\ETAPE 2 - OAD\OAD\datas_sig\emprise")
    
    # 🔹 Chercher tous les fichiers shapefile ou geopackage dans ce dossier
    fichiers_emprise = list(dossier_emprise.glob("*.shp")) + list(dossier_emprise.glob("*.gpkg"))
    
    # 🔹 Vérifier qu'au moins un fichier est trouvé
    if not fichiers_emprise:
        raise FileNotFoundError("❌ Aucun fichier d'emprise trouvé dans le dossier emprise.")

    # 🔹 Charger le premier fichier trouvé
    print(f"✅ Fichier d'emprise détecté : {fichiers_emprise[0].name}")
    gdf = gpd.read_file(fichiers_emprise[0])

    # 🔹 Fusionner tous les polygones en un seul si plusieurs entités présentes
    if len(gdf) > 1:
        print("⚠️ Plusieurs polygones détectés, fusion en un polygone unique")
        gdf = gdf.dissolve()
    
    # 🔹 Reprojection si nécessaire pour appliquer le tampon en mètres
    if gdf.crs.is_geographic:
        print("⚠️ CRS géographique détecté, reprojection en Lambert93 pour tampon")
        gdf = gdf.to_crs(epsg=2154)  # EPSG:2154 = Lambert 93
    
    # 🔹 Appliquer un tampon autour du polygone si demandé
    if taille_tampon_km > 0:
        tampon_m = taille_tampon_km * 1000
        gdf['geometry'] = gdf.buffer(tampon_m)
        print(f"🔹 Tampon de {taille_tampon_km} km appliqué sur l'emprise")
    
    # 🔹 Retourner le GeoDataFrame final
    return gdf