# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_vulnerabilite_facon1"
Date : 2026-02-17
Objectif : calcul indicateurs vulnérabilité (troncon en enjeu fort ou non)
═══════════════════════════════════════════════════════════════════

"""
#pas besoin d'importer de libraries

def calculer_vulnerabilite_facon1(gdf_analyse, # nom générique, mettre gdf_troncons_copy
                               df_scoring,
                               dict_couches=None, # on peut directement passer le dictionnaire pour trouver les colonnes à analyser
                               colonnes_zones_critiques=None, #en option si il n'y a pas de dictionnaire
                               indicateur = 'MS1', # renseigner le nom de l'indicateur calculé
                               methode='seuil'): #seuil est la valeur par défaut
    """
    Détermine si un tronçon est vulnérable en visibilité critique

    Paramètres de la fonction :
        
        - gdf_analyse : GDF enrichi avec les colonnes de zones critiques (c'est gdf_troncons_copy)
        
        - df_scoring : dataframe de scoring à enrichir

        - dict_couches : dict, optionnel, dictionnaire ex : DATA[MS][MS1], si fourni, les colonnes seront extraites automatiquement
        
        - colonnes_zones_critiques : list, optionnel : liste des noms de colonnes à analyser, utilisé seulement si dict_couches_M1 n'est pas fourni

        - indicateur : str, nom de l'indicateur, utilisé pour nommer la colonne de sortie : {indicateur}_vulnerabilite
        
        - methode : str
            'seuil' : vulnérable si au moins 1 élément dans 1 catégorie
            'moyenne': vulnérable si nombre éléments sup à moy de la catégorie
            'percentile' : vulnérable si dans le x% les plus élevés

        la fonction retourne df_scoring enrichi avec la colonne MS1_vulnerabilite

    ------------------------
        Exemples d'utilisation :
    
    # Méthode 1 : Automatique avec le dictionnaire
    df_scoring = calculer_vulnerabilite_facon1(
        gdf_analyse=gdf_troncons_copy,
        df_scoring=df_scoring,
        dict_couches_MS1=DATA["MS"]["MS1"],
        methode='seuil'
    )
    
    # Méthode 2 : Manuel avec liste de colonnes
    df_scoring = calculer_vulnerabilite_facon1(
        gdf_analyse=gdf_troncons_copy,
        df_scoring=df_scoring,
        colonnes_zones_critiques=['carrefours', 'echangeurs', 'passages à niveaux'],
        methode='seuil'
    )
    ------------------------
    
    """
    # Détection automatique des colonnes
    # si le dict est fournun extraire les nimls de colonnes automatiquement
    if dict_couches is not None:
        print("Extraction automatique des colonnes depuis le dictionnaire")

        #extraire les clés du dict = noms de colonnes
        colonnes_zones_critiques = list(dict_couches.keys())
        print(f"Colonnes détectées : {colonnes_zones_critiques}")

    #si lni dict ni colonnes manuelles ne sont fournies -> erreur
    elif colonnes_zones_critiques is None:
        raise ValueError(
            "ERREUR : Vous devez fournir soit 'dict_MS1' soit 'colonnes_zones_critiques'")

    #Vérifier que toutes les colonnes existent dans le GDF
    colonnes_manquantes = [
        col for col in colonnes_zones_critiques
        if col not in gdf_analyse.columns]
    if colonnes_manquantes:
        raise ValueError(
            f"ERREUR : Les colonnes suivantes n'existent pas dans gdf_analyses :\n"
            f"   {colonnes_manquantes}\n"
            f"   Colonnes disponibles : {list(gdf_analyse.columns)}"
        )


    print(f"\n{'='*70}")
    print(f"CALCUL DE LA VULNÉRABILITÉ {indicateur} - MÉTHODE : {methode.upper()}")
    print(f"📋 Colonnes analysées : {colonnes_zones_critiques}")
    print(f"📊 Nombre de tronçons : {len(gdf_analyse)}\n")
    print(f"{'='*70}\n")

    # nom de la colonne de sortie (dynamique)
    nom_colonne_vuln = f"{indicateur}_vulnerabilite"

    # Méthode 1 - SEUIL SIMPLE (au moins 1 élément)
    if methode == 'seuil':
        print("Méthode : Vulnérable si au moins 1 élément critique présent")

        # créer une colonne pour stocker le résultat
        # par défaut, tous les tronçons sont "non" vulnérables
        df_scoring[nom_colonne_vuln] = 'non'

        # pour chaque tronçon, on va vérifier s'il a au moins 1 élément
        gdf_analyse['total_elements_critiques'] = gdf_analyse[colonnes_zones_critiques].sum(axis=1)

        #explication de axis=1:
            #axis=1 veut dire "somme en ligne" = addition des valeurs des colonnes pour chaque ligne
            #ex pour un troncon : carrefour=3, echangeurs=0, passages_niveaux=1 --> total-elements_critiques = 3+0+1=4

        #♦ identifier les tronçons avec au moins 1 élément critique
        # on récupère les nom_plo_fi des tronçons où total >0
        troncons_vulnerables = gdf_analyse[
            gdf_analyse['total_elements_critiques'] > 0
        ]['nom_plo_fi'].values

        # marquer ces tronçons comme vulnérables dans df_scoring
        # isin() permet de vérifier si la valeur de nom_plo_fi est dans la liste
        df_scoring.loc[
            df_scoring['nom_plo_fi'].isin(troncons_vulnerables),
            nom_colonne_vuln
        ] = 'oui'

        # calculer les statistiques
        nb_vulnerables = (df_scoring[nom_colonne_vuln] == 'oui').sum()
        pct_vulnerables = round(nb_vulnerables / len(df_scoring) * 100, 1)

        print(f"Résultats :")
        print(f"Tronçons vulnérables : {nb_vulnerables} ({pct_vulnerables}%)")
        print(f"Tronçons non vulnérables : {len(df_scoring) - nb_vulnerables}")

        # nettoyer la colonne temporaire
        gdf_analyse.drop('total_elements_critiques', axis=1, inplace=True)

    # ========================================================================
    # MÉTHODE MOYENNE (code identique, juste avec gdf_analyse)
    # ========================================================================
    
    elif methode == 'moyenne':
        print("🔍 Méthode : Vulnérable si nombre d'éléments > moyenne de SA catégorie\n")
        
        df_scoring[nom_colonne_vuln] = 'non'
        
        print("📈 Calcul des moyennes par catégorie :\n")
        
        tous_troncons_vulnerables = set()
        
        for colonne in colonnes_zones_critiques:
            moyenne = gdf_analyse[colonne].mean()
            
            troncons_au_dessus_moyenne = gdf_analyse[
                gdf_analyse[colonne] > moyenne
            ]['nom_plo_fi'].values
            
            tous_troncons_vulnerables.update(troncons_au_dessus_moyenne)
            
            nb_au_dessus = len(troncons_au_dessus_moyenne)
            pct_au_dessus = round(nb_au_dessus / len(gdf_analyse) * 100, 1)
            
            print(f"   {colonne} :")
            print(f"      • Moyenne : {moyenne:.2f} éléments/tronçon")
            print(f"      • Tronçons > moyenne : {nb_au_dessus} ({pct_au_dessus}%)")
        
        df_scoring.loc[
            df_scoring['nom_plo_fi'].isin(tous_troncons_vulnerables),
            nom_colonne_vuln
        ] = 'oui'
        
        nb_vulnerables = (df_scoring[nom_colonne_vuln] == 'oui').sum()
        pct_vulnerables = round(nb_vulnerables / len(df_scoring) * 100, 1)
        
        print(f"\n📊 Résultats globaux :")
        print(f"   • Tronçons vulnérables : {nb_vulnerables} ({pct_vulnerables}%)")
        print(f"   • Tronçons non vulnérables : {len(df_scoring) - nb_vulnerables}")
    
    # ========================================================================
    # MÉTHODE PERCENTILE (code identique, avec gdf_analyse)
    # ========================================================================
    
    elif methode == 'percentile':
        print("🔍 Méthode : Vulnérable si dans les 50% avec le plus d'éléments\n")
        
        gdf_analyse['total_elements_critiques'] = gdf_analyse[colonnes_zones_critiques].sum(axis=1)
        
        seuil_percentile_50 = gdf_analyse['total_elements_critiques'].quantile(0.50)
        
        print(f"📊 Analyse de distribution :")
        print(f"   • Percentile 50 (médiane) : {seuil_percentile_50:.2f} éléments")
        print(f"   • Percentile 75 : {gdf_analyse['total_elements_critiques'].quantile(0.75):.2f} éléments")
        print(f"   • Percentile 90 : {gdf_analyse['total_elements_critiques'].quantile(0.90):.2f} éléments")
        print(f"   • Maximum : {gdf_analyse['total_elements_critiques'].max():.0f} éléments\n")
        
        df_scoring[nom_colonne_vuln] = 'non'
        
        troncons_vulnerables = gdf_analyse[
            gdf_analyse['total_elements_critiques'] > seuil_percentile_50
        ]['nom_plo_fi'].values
        
        df_scoring.loc[
            df_scoring['nom_plo_fi'].isin(troncons_vulnerables),
            nom_colonne_vuln
        ] = 'oui'
        
        nb_vulnerables = (df_scoring[nom_colonne_vuln] == 'oui').sum()
        pct_vulnerables = round(nb_vulnerables / len(df_scoring) * 100, 1)
        
        print(f"📊 Résultats :")
        print(f"   • Tronçons vulnérables : {nb_vulnerables} ({pct_vulnerables}%)")
        print(f"   • Tronçons non vulnérables : {len(df_scoring) - nb_vulnerables}")
        
        gdf_analyse.drop('total_elements_critiques', axis=1, inplace=True)
    
    else:
        raise ValueError(
            f"❌ Méthode inconnue : {methode}\n"
            f"   Utilisez 'seuil', 'moyenne' ou 'percentile'"
        )
    
    print(f"\n{'='*70}\n")
    
    return df_scoring