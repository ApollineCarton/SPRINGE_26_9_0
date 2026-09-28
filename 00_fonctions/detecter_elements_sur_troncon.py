# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "detecter_elements_sur_troncon"
Date : 2026-02-17
Objectif : Intersect des éléments rencontrés sur un tronçon
═══════════════════════════════════════════════════════════════════

    Détection générique de la présence d'éléments géographiques pour chaque troncons.
    Cette fonction permet de détecter si des éléments (patrimoine, carrefour..) intersectent les tronçons routiers. 
    Elle crée une colonne 'oui'/'non' pour chaque type d'élément et calcule des statistiques détaillées.
    
    paramètres de la fonction :
    
        - gdf_PR : geodataframe polygones qui contient les PR ; Doit contenir au minimum une colonne 'nom_plo_fi' et une colonne 'geometry'
    
        - dict_couches : dictionnaire
            format : {nom_colonne : gdf_elements}
            - nom_colonne, str : nom de la colonne à créer dans gdf_troncons
            - gdf_eleme,ts, GDF : geodataframe des éléments à détecter (point, lignes, polygones)
        
        - nom_categorie, str : nom de la catégorie (lien avec l'indicateur) d'éléments analysés (ex : patrimoine, zone_critique)
                        ce nom est utilisé pour nommer les objets de statistiques créés
    
        - mode : paramètre qui rend la fonction flexible sans la dupliquer, pour une sortie oui/non (presence) ou en nb d'éléments (count)

        - tampon : int ou None, si fourni, crée un tampon autour des tronçons (en mètres)
            exemple : tampon = 50 --> tampon de 50 mètres
                        
    la fonction retourne :
    - gdf_PR : enrichi avec les nouvelles colonnes. chaque colonne contient 'oui' si présence de l'élément, et 'non' sinon
    - stat : dict contenant statistiques d'affiliation pour chaque type d'élément
        structure : {nom_colonne: {statistiques détaillées}}

    exemple d'utilisation :
    # Détecter du patrimoine sensible
    dict_patrimoine = {
        'ecransAcoustiques': gdf_ecransAcoustiques,
        'mursConsedes': gdf_mursConsedes,
        'pontsConsedes': gdf_pontsConsedes
    }
    gdf_troncons_copy, stats = detecter_elements_sur_troncons(
        gdf_troncons_copy, 
        dict_patrimoine, 
        'patrimoine'
    )
    

"""
import geopandas as gpd

def detecter_elements_sur_troncon(gdf_PR, 
                                  dict_couches, 
                                  nom_categorie, 
                                  mode,
                                  tampon=None #assigner un tampon autour des tronçons si besoin
                                 ):

    # ============================================================================
    # ÉTAPE 0 : LES MODES DE SORTIE
    # ============================================================================
    
    if mode not in ["presence", "count"]:
        raise ValueError("Erreur : Le paramètre 'mode' doit être 'presence' ou 'count'")

    # ============================================================================
    # ÉTAPE 1 : PRÉPARATION
    # ============================================================================
    
    # Initialiser le dictionnaire pour stocker toutes les statistiques
    # Ce dictionnaire aura un format : {nom_colonne: {stat1: val1, stat2: val2, ...}}
    stats = {}

    print(f"\n{'='*70}")
    print(f"DÉTECTION D'ÉLÉMENTS : {nom_categorie.upper()}")
    print(f"{'='*70}")
    print(f"Nombre de tronçons à analyser : {len(gdf_PR)}")
    print(f"Nombre de couches à traiter : {len(dict_couches)}")

    # CREATION DU TAMPON SI DEMANDE
    if tampon:
        print(f"Création du tampon de {tampon} mètres autour des tronçons ...")

        # créer une copie du GDF avec la géométrie tamponnée
        gdf_PR_tampon = gdf_PR[['nom_plo_fi', 'geometry']].copy()
        gdf_PR_tampon['geometry'] = gdf_PR_tampon['geometry'].buffer(tampon)

        print(f"Tampon crée pour {len(gdf_PR_tampon)} tronçons")

        # utiliser le gdf tampon pour les jointures
        gdf_pour_jointure = gdf_PR_tampon

    else:
        #pas de tampon : utiliser la géométrie originale des tronçons
        gdf_pour_jointure = gdf_PR[['nom_plo_fi', 'geometry']]
    

        
    # ============================================================================
    # ÉTAPE 2 : TRAITEMENT DE CHAQUE COUCHE
    # ============================================================================
    
    # Parcourir chaque couche du dictionnaire
    '''# SI UTILISATIONS DE DICTIONNAIRES SIMPLES
    for nom_colonne, gdf_elements in dict_couches.items():
        print(f"\n---Traitement de la couche {nom_colonne}---")
    '''
    # code pour rendre compatible la fonction avec des dictionnaires "simples" ou le DATA
    for nom_colonne, couche in dict_couches.items():

        print(f"--Traitement de la couche {nom_colonne}")
        
        # gérer la compatibilité double format de dict
        # soit on reçoit directement n GDF, soit on reçoit un dict structuré avec une clé 'gdf'
        if isinstance(couche, dict):
            if "gdf" not in couche:
                raise ValueError(
                    f"La couche '{nom_colonne}' est un dictionnaire mais ne contient pas de clé 'gdf'.")
            gdf_elements = couche["gdf"]
        else:
            gdf_elements = couche
        
        #ajouter une sécurité
        if not isinstance(gdf_elements, gpd.GeoDataFrame):
            raise ValueError(
                f"La couche '{nom_colonne}' n'est pas un GeoDataFrame valide"
                f"(type reçu : {type(gdf_elements)})")        
            

        '''
        # ------------------------------------------------------------------------
        # VÉRIFICATION DU SYSTÈME DE PROJECTION
        # ------------------------------------------------------------------------
        # Les GeoDataFrame doivent avoir le même CRS pour faire des jointures spatiales
        # Si ce n'est pas le cas, il faut reprojeter avant d'appeler cette fonction
        if gdf_elements.crs != gdf_PR.crs:
            raise ValueError(
                f"ERREUR : Les systèmes de projection ne correspondent pas !\n"
                f"  - Tronçons : {gdf_PR.crs}\n"
                f"  - {nom_colonne} : {gdf_elements.crs}\n"
                f"Veuillez reprojeter vos données dans le même CRS avant d'utiliser cette fonction."
            )
        '''
        # ------------------------------------------------------------------------
        # JOINTURE SPATIALE : TRONÇONS → ÉLÉMENTS
        # ------------------------------------------------------------------------
        # On cherche quels éléments intersectent chaque tronçon
        # how='inner' : on ne garde que les intersections (les tronçons sans éléments 
        #               seront gérés plus tard)
        # predicate='intersects' : fonctionne pour tous types de géométries 
        #                          (points, lignes, polygones)
        jointure = gpd.sjoin(
            gdf_pour_jointure[['nom_plo_fi', 'geometry']],  # On ne garde que les colonnes essentielles
            # utiliser le gdf tampon si besoin grace à gdf_pour_jointure
            gdf_elements,
            how='inner',
            predicate='intersects'
        )
        
        # ------------------------------------------------------------------------
        # IDENTIFICATION DES TRONÇONS CONCERNÉS
        # ------------------------------------------------------------------------
        # Récupérer les index uniques des tronçons qui ont au moins une intersection
        # Un même tronçon peut apparaître plusieurs fois dans la jointure s'il intersecte
        # plusieurs éléments, donc on prend les valeurs uniques
        troncons_avec_elements = jointure.index.unique()
        
        # ------------------------------------------------------------------------
        # CRÉATION DE LA COLONNE INDICATRICE SELON LE MODE CHOISI
        # ------------------------------------------------------------------------
        
        # MODE presence (oui/non) :

        if mode == "presence":
            
            # Par défaut, tous les tronçons ont la valeur 'non'
            gdf_PR[nom_colonne] = 'non'
        
            # On change en 'oui' uniquement pour les tronçons qui ont au moins un élément
            gdf_PR.loc[troncons_avec_elements, nom_colonne] = 'oui'  

        # MODE count :

        elif mode == "count":

            #Compter le nombre d'éléments par tronçon
            nb_elements_par_troncon = jointure.groupby(jointure.index).size()

            #Initialiser la colonne à 0 par défaut
            gdf_PR[nom_colonne] = 0

            #Remplir avec le nombre réel d'éléments pour les tronçons concernés
            gdf_PR.loc[nb_elements_par_troncon.index, nom_colonne] = nb_elements_par_troncon

            # résultat attendu :
            # 0 -> aucun élément intersectant
            # 1 -> un élément
            # 2 -> deux éléments, etc.
        # ------------------------------------------------------------------------
        # CALCUL DES STATISTIQUES à partir de la jointure (étape facultative mais utile pour validation)
        # ------------------------------------------------------------------------

        '''
        # JOINTURE INVERSE : ÉLÉMENTS → TRONÇONS
        # Cette fois, on part des éléments pour voir lesquels touchent des tronçons
        # how='left' : on garde tous les éléments, même ceux sans tronçon
        jointure_inverse = gpd.sjoin(
            gdf_elements,
            gdf_PR[['nom_plo_fi', 'geometry']],
            how='left',
            predicate='intersects'
        )
        '''
        # CALCUL 1 : Nombre total d'éléments dans la couche
        nb_total = len(gdf_elements)
        
        # CALCUL 2 : Nombre d'affiliations (= nombre total de lignes dans jointure_inverse)
        # Si un élément touche 3 tronçons, il compte pour 3 affiliations
        
        '''nb_affiliations = jointure_inverse['nom_plo_fi'].notna().sum()'''
        nb_affiliations = len(jointure)
        
        # CALCUL 3 : Nombre d'éléments UNIQUES qui touchent au moins 1 tronçon
        # On compte les index uniques qui ont une valeur non-nulle dans 'nom_plo_fi'

        '''
        elements_avec_troncon = jointure_inverse[jointure_inverse['nom_plo_fi'].notna()].index.nunique()
        nb_elements_affilies = elements_avec_troncon
        '''

        if 'index_right' in jointure.columns:
            nb_elements_affilies = jointure['index_right'].nunique()
        else:
            nb_elements_affilies = 0
        
        # CALCUL 4 : Nombre d'éléments qui ne touchent AUCUN tronçon
        # Ce sont les lignes où 'nom_plo_fi' est NaN (pas d'intersection trouvée)
        
        '''nb_elements_non_affilies = jointure_inverse[jointure_inverse['nom_plo_fi'].isna()].index.nunique()'''
        nb_elements_non_affilies = nb_total - nb_elements_affilies
        
        # CALCUL 5 : Pourcentage d'éléments affiliés
        pct_elements_affilies = round(nb_elements_affilies / nb_total * 100, 1) if nb_total > 0 else 0
        
        # CALCUL 6 : Nombre moyen de tronçons par élément affilié
        # = nb_affiliations / nb_elements_affilies
        moyenne_troncons_par_element = round(nb_affiliations / nb_elements_affilies, 1) if nb_elements_affilies > 0 else 0
        
        # CALCUL 7 : Nombre de tronçons avec au moins un élément de ce type
        '''nb_troncons_avec_elements = len(troncons_avec_elements)'''
        troncons_avec_elements = jointure.index.unique()
        nb_troncons_avec_elements = len(troncons_avec_elements)
        
        # CALCUL 8 : Nombre de tronçons sans élément de ce type
        nb_troncons_sans_elements = len(gdf_PR) - nb_troncons_avec_elements
        
        # ------------------------------------------------------------------------
        # STOCKAGE DES STATISTIQUES
        # ------------------------------------------------------------------------
        stats[nom_colonne] = {
            # Statistiques sur les éléments
            'nb_total': nb_total,
            'nb_elements_affilies': nb_elements_affilies,
            'nb_elements_non_affilies': nb_elements_non_affilies,
            'pct_elements_affilies': pct_elements_affilies,
            
            # Statistiques sur les affiliations
            'nb_affiliations_totales': nb_affiliations,
            'moyenne_troncons_par_element': moyenne_troncons_par_element,
            
            # Statistiques sur les tronçons
            'nb_troncons_avec_elements': nb_troncons_avec_elements,
            'nb_troncons_sans_elements': nb_troncons_sans_elements,
            'nb_troncons_total': len(gdf_PR),
            'pct_troncons_avec_elements': round(nb_troncons_avec_elements / len(gdf_PR) * 100, 1) if len(gdf_PR) > 0 else 0
        }
        
        # ------------------------------------------------------------------------
        # AFFICHAGE DES STATISTIQUES
        # ------------------------------------------------------------------------
        print(f"\n📊 Statistiques pour '{nom_colonne}' :")
        print(f"\n  Éléments de {nom_categorie} :")
        print(f"    • Total d'éléments dans la couche : {nb_total}")
        print(f"    • Éléments affiliés (touchent ≥1 tronçon) : {nb_elements_affilies} ({pct_elements_affilies}%)")
        print(f"    • Éléments non affiliés (aucun tronçon) : {nb_elements_non_affilies}")
        
        print(f"\n  Affiliations :")
        print(f"    • Nombre total d'affiliations : {nb_affiliations}")
        print(f"    • Moyenne de tronçons par élément : {moyenne_troncons_par_element}")
        
        print(f"\n  Tronçons :")
        print(f"    • Avec {nom_categorie} : {nb_troncons_avec_elements} ({stats[nom_colonne]['pct_troncons_avec_elements']}%)")
        print(f"    • Sans {nom_categorie} : {nb_troncons_sans_elements}")
    
# ============================================================================
    # ÉTAPE 3 : RÉSUMÉ FINAL
    # ============================================================================
    print(f"\n{'='*70}")
    print(f"RÉSUMÉ : {nom_categorie.upper()}")
    print(f"{'='*70}")
    print(f"✅ {len(dict_couches)} couche(s) traitée(s)")
    print(f"✅ {len(dict_couches)} nouvelle(s) colonne(s) ajoutée(s) au GeoDataFrame")
    print(f"✅ Statistiques disponibles dans le dictionnaire retourné")
    print(f"{'='*70}\n")
    
    # Retourner le GeoDataFrame enrichi et les statistiques
    return gdf_PR, stats