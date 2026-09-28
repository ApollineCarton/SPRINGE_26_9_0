# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""


"""
═══════════════════════════════════════════════════════════════════
Fonction "mapping"
Date : 2026-03-17
Objectif : faire le mapping des noms d'espèces'
═══════════════════════════════════════════════════════════════════

Mapping des noms d'espèces EEE'
Logique : réaliser un mapping pour créer une équivalence entre les noms d'espèces gérés par les fichiers points EEE et l

Paramètres :
    - gdf_EEE : Gdf des points de présence EEE, colonnes 'nom_plo_fi' et 'plante'

Sortie : gdf_EEE_mapping : une copie de gdf_EEE avec le mapping

"""
'''
def mapping(gdf_EEE):
    mapping_EEE = {
        'Renouees': 'Reynoutria sp',
        'Ailante': 'Ailanthus altissima',
        'Ambroisie': 'Ambrosia artemisiifolia',
        'BerceCaucase': 'Heracleum mantegazzianum',
        'Autre': 'EEE autre'
    }

    gdf_EEE_mapping = gdf_EEE.copy()
    gdf_EEE_mapping['species_name_sci'] = gdf_EEE_mapping['plante'].map(mapping_EEE)

    non_mappes = gdf_EEE_mapping[gdf_EEE_mapping['species_name_sci'].isna()]['plante'].unique()
    if len(non_mappes) > 0:
        print(f"⚠️ Espèces non mappées : {non_mappes}")
    
    return gdf_EEE_mapping
'''

def mapping(gdf_EEE):
    
    #on map les noms d'espèces qui désignent une espèce similaire
    mapping_EEE = {
        'Renouees': 'Reynoutria sp',
        'Ailante': 'Ailanthus altissima',
        'Ambroisie': 'Ambrosia artemisiifolia',
        'BerceCaucase': 'Heracleum mantegazzianum',
        'Autre': 'EEE autre'
    }

    #on travaille sur une copye de gdf_EEE pour ne pas avoir d'effets de bord
    gdf_EEE_mapping = gdf_EEE.copy()
    gdf_EEE_mapping['species_name_sci'] = gdf_EEE_mapping['plante'].map(mapping_EEE)

    #on peut avoir des espèces non mappées, c'est lutilisateur qui les gère
    
    # Détection des espèces non mappées
    non_mappes = gdf_EEE_mapping[gdf_EEE_mapping['species_name_sci'].isna()]['plante'].unique()

    for espece in non_mappes:
        print(f"\n⚠️ Espèce non mappée : {espece}")
        print("Choisir une catégorie : Renouees / Ailante / Ambroisie / BerceCaucase / Autre")

        choix = input("👉 Votre choix : ")

        if choix in mapping_EEE:
            mapping_EEE[espece] = mapping_EEE[choix]
        else:
            print("❌ Choix invalide → classé en 'Autre'")
            mapping_EEE[espece] = mapping_EEE['Autre']

    # Recalcul avec mapping complété
    gdf_EEE_mapping['species_name_sci'] = gdf_EEE_mapping['plante'].map(mapping_EEE)

    return gdf_EEE_mapping