# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "creer_objet_scoring"
Date : 2026-02-17
Objectif : Créer un objet tableau pour stocker les résultats de calcul
═══════════════════════════════════════════════════════════════════
--> on créé l'objet scoring qui va contenir pour chaque troncon les points et scores

création d'un DataFrame de scoring initial contenant l'identifiant des tronçons.
cet objet sert à centraliser les points d'indicateurs puis à calculer les scores.

les paramètres de la fonction :
- gdf_troncons : GeoDataFrame, contenant les identifiants de troncons avec la colonne 'nom_plo_fi"

utilise la library pandas

retourne : un DataFrame avec la colonne 'nom_plo_fi' (identifiant unique des troncons)

"""
import pandas as pd

def creer_objet_scoring(gdf_troncons_copy, colonne_id='nom_plo_fi'):
        
    df_scoring = pd.DataFrame({
        
    colonne_id : gdf_troncons_copy[colonne_id].values})
    
    # création d'un dataframe avec la colonne nom_plo_fi
    print(f" Objet tableau des scores créé avec {len(df_scoring)} tronçons")
    
    return df_scoring