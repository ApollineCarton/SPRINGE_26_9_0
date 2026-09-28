# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "join_num_troncon_a_gdf_EEE"
Date : 2026-02-17
Objectif : Jointure entre points présence EEE et tronçons
═══════════════════════════════════════════════════════════════════

gdf_troncons > nom_plo_fi = n° du PR

principe du code : 
intercect les points EEE sur un troncon, création colonne nom_plo_fi dans gdf_EEE avec le n° de troncon intercecté

si un point intercect plusieurs troncons, alors mettre les deux n° sous la forme "numeroA, numeroB"

fonction qui attribue à chaque point de présence EEE le ou les numéros de tronçons dans lequel il se trouve

paramètres de la fonction :
    - gdf_point : le nom de la couche SIG avec les points de présence EEE
    - gdf_polygones : le nom de la couche SIG avec les polygones de troncons(PR)
    - colonne_id : string, le nom de la colonne qui contient l'identifiant des troncons

action de la fonction :
    retourne gdf_point avec nom_plo_fi ajouté


"""

import geopandas as gpd

def join_num_troncon_a_gdf_EEE(gdf_points, gdf_polygones, colonne_id):

    #faire une copie pour ne pas modifier l'original
    gdf_points = gdf_points.copy()

    #vérifier que les couches sont dans le même CRS (normalement c'est bon)
    if gdf_points.crs != gdf_polygones.crs:
        raise ValueError("Erreur dans l'exécution : les GeoDataFrame n'ont pas le même CRS")
        # arrêt de la fonction, il faudra projetter comme il faut plus haut dans le code

    jointure = gpd.sjoin(gdf_points, 
                         gdf_polygones[[colonne_id, 'geometry']],
                         how='left', #garde tous les points, même s'ils n'interceptent pas un tronçon
                         predicate='intersects')
    # on réalise une jointure spatiale pour trouver tous les tronçons intersectant chaque point
        #double [[ pour créer une liste
    ### ATTENTION : la jointure peut faire changer le nom des colonnes (ajout suffixe _left ou _rigth, provocant une erreur car la colonne 'nom_plo_fi' n'existe plus.
        ### on apporte une correction pour etre robuste face à cela :
    #--------------------
    # détecter où est la colonne nom_plo_fi avec la jointure
    #--------------------
    colonnes_candidates = [
        col for col in jointure.columns
        if colonne_id in col and col != "geometry"
    ]

    if len(colonnes_candidates) == 0:
        raise KeyError(
            f"Aucune colonne contenant '{colonne_id}' trouvée après la jointure.\n"
            f"Colonnes disponibles : {list(jointure.columns)}"
        )

    # Priorité : _right > nom exact > autre
    if len(colonnes_candidates) > 1:
        if f"{colonne_id}_right" in colonnes_candidates:
            colonne_troncon = f"{colonne_id}_right"
        elif colonne_id in colonnes_candidates:
            colonne_troncon = colonne_id
        else:
            colonne_troncon = colonnes_candidates[0]
    else:
        colonne_troncon = colonnes_candidates[0]

    
    def concatener_troncons(groupe):
    # grouper par l'index d'origine les points pour gérer des intersections multiples
        """concatène les numéros des PR, ou retourne NA"""
        troncons = groupe[colonne_troncon].dropna().unique()
        if len(troncons) == 0:
            return 'NA'
        else:
            return ', '.join(sorted(troncons.astype(str)))
            #trier et joindre avec des virgules si plusieurs troncons

    #agréger le résultat par points
    troncons_par_points = (
        jointure
        .groupby(jointure.index)
        .apply(concatener_troncons)
        .reset_index(name=colonne_id) # nom final standardisé
    )
        #jointure : resultat de gdp.join()
        #jointure.index : tous les polygones associés au meme point se regroupent
        #apply : appel de la fonction concatener_troncons
        #reset_index : pour transormer et avoir les valeurs dans colonne_id

    # si la colonne_id existe deja sous ce nom dans gdf_points, la renommer avec l'indice -original pour la conserver et executer la suite sans problème
    if colonne_id in gdf_points.columns:
        gdf_points = gdf_points.rename(columns={colonne_id: f"{colonne_id}_original"})

    #fusion du résultat avec les points originaux
    gdf_points = (
        gdf_points
        .merge(troncons_par_points, left_index=True, right_on="index")
        .drop(columns=["index"])
    )
                                  #,how='left'
                                 
        # gdf_points : les points d'origine
        #troncons_par_points : dataframe avec index (index des pts d'origine) et colonne_id (troncons concatenés)
        # merge : pandas prend chaque point et colle la valeur de colonne_id correspondant à son index
            # left_index=True : on utilise l'index de gdf_points comme clé
            #right_on='index' : on utilise la colonne index de troncons_par_points
            # ATTENTION : par defaut, merge supprimer les points sans correspondance (inner.join) --> how='left' pour les conservés tous, met NaN
            # MAIS dans notre cas how='left' non nécessaire car la fonction concatener_troncons met 'NA' comme chaine de caractère si pas de troncons
        # index vient de troncons_par_points, elle servait de clé de jointure, elle n'est plus utile désormais donc on la supprime (nettoyage)
       
    return gdf_points

