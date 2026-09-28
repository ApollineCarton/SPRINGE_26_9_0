# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

'''def analyser_attribution_elements_sur_troncon(gdf_PR, dict_couches, nom_categorie, seuil_tampon_suggestion=30):
    """
    Analyse la qualité de l'attribution des éléments géographiques aux tronçons.
    
    Cette fonction analyse les éléments NON AFFILIÉS pour déterminer s'ils sont de vrais négatifs
    ou s'ils nécessitent un tampon spatial pour améliorer la détection.
    Elle utilise un arbre spatial (KDTree) pour calculer rapidement les distances.
    
    Paramètres de la fonction :
    ---------------------------
    gdf_PR : GeoDataFrame
        GeoDataFrame des tronçons routiers. Doit contenir au minimum une colonne 'nom_plo_fi' et 'geometry'
    
    dict_couches : dict
        Dictionnaire au format {nom_colonne : gdf_elements}
        - nom_colonne (str) : nom de la couche analysée
        - gdf_elements (GDF) : geodataframe des éléments à analyser (points, lignes, polygones)
    
    nom_categorie : str
        Nom de la catégorie d'éléments analysés (ex : 'patrimoine', 'zone_critique')
        Ce nom est utilisé pour l'affichage et la documentation
    
    seuil_tampon_suggestion : float, optionnel (default=30)
        Seuil en pourcentage pour déclencher une recommandation de tampon
        Si > seuil_tampon_suggestion% des non-affiliés sont à < 10m, un tampon est suggéré
    
    La fonction retourne :
    ----------------------
    stats : dict
        Dictionnaire contenant les analyses pour chaque couche
        Structure : {
            nom_colonne: {
                'distances': array des distances en mètres,
                'stats_distances': dict des statistiques (min, max, médiane, etc.),
                'repartition_tranches': dict du nombre d'éléments par tranche de distance,
                'tampon_suggere': int (0, 5, ou 10 mètres),
                'pct_moins_5m': float,
                'pct_moins_10m': float,
                'nb_non_affilies': int,
                'recommandation': str (message de recommandation)
            }
        }
    
    Exemple d'utilisation :
    -----------------------
    # Analyser l'attribution du patrimoine
    dict_patrimoine = {
        'ecransAcoustiques': gdf_ecransAcoustiques,
        'mursConsedes': gdf_mursConsedes,
        'pontsConsedes': gdf_pontsConsedes
    }
    
    stats_analyse = analyser_attribution_elements_sur_troncon(
        gdf_troncons_copy,
        dict_patrimoine,
        'patrimoine',
        seuil_tampon_suggestion=30
    )
    
    # Afficher la recommandation pour une couche spécifique
    print(stats_analyse['ecransAcoustiques']['recommandation'])
    """
    
    # ============================================================================
    # ÉTAPE 1 : PRÉPARATION
    # ============================================================================
    
    # Initialiser le dictionnaire pour stocker toutes les analyses
    stats = {}
    
    print(f"\n{'='*70}")
    print(f"ANALYSE D'ATTRIBUTION : {nom_categorie.upper()}")
    print(f"{'='*70}")
    print(f"Nombre de tronçons de référence : {len(gdf_PR)}")
    print(f"Nombre de couches à analyser : {len(dict_couches)}")
    print(f"Seuil de suggestion de tampon : {seuil_tampon_suggestion}% d'éléments à < 10m")

    """
    # ============================================================================
    # ÉTAPE 2 : HARMONISATION DES SYSTÈMES DE PROJECTION
    # ============================================================================
    
    # Vérifier si les tronçons sont en système géographique
    # Si oui, reprojeter en Lambert 93 (EPSG:2154) pour avoir des distances en mètres
    if gdf_troncons_copy.crs.is_geographic:
        print("\n⚠️  Conversion en Lambert 93 (EPSG:2154) pour calcul des distances en mètres...")
        gdf_troncons_copy = gdf_troncons_copy.to_crs('EPSG:2154')
    """
    
    # ============================================================================
    # ÉTAPE 3 : CONSTRUCTION DE L'ARBRE SPATIAL (une seule fois pour tous)
    # ============================================================================
    
    print(f"\n📍 Construction de l'arbre spatial des tronçons...")
    
    # Extraire les coordonnées 2D des contours des tronçons
    points_troncons = []
    
    for geom in gdf_PR.geometry:
        # Extraire les coordonnées selon le type de géométrie
        if geom.geom_type == 'Polygon':
            coords = list(geom.exterior.coords)
        elif geom.geom_type == 'MultiPolygon':
            coords = []
            for poly in geom.geoms:
                coords.extend(list(poly.exterior.coords))
        else:
            coords = list(geom.coords)
        
        # Prendre seulement X et Y (ignorer Z si présent)
        coords_2d = [(c[0], c[1]) for c in coords]
        
        # Échantillonner tous les 10 points pour accélérer
        # (suffisant pour une bonne estimation de distance)
        coords_echantillon = coords_2d[::10] if len(coords_2d) > 10 else coords_2d
        points_troncons.extend(coords_echantillon)
    
    points_troncons = np.array(points_troncons)
    print(f"   ✓ Arbre spatial construit avec {len(points_troncons):,} points")
    
    # Construire l'arbre spatial (KDTree) pour recherche rapide de voisins
    tree = cKDTree(points_troncons)
    
    # ============================================================================
    # ÉTAPE 4 : TRAITEMENT DE CHAQUE COUCHE
    # ============================================================================
    
    for nom_colonne, gdf_elements in dict_couches.items():
        print(f"\n{'-'*70}")
        print(f"Traitement de la couche : {nom_colonne}")
        print(f"{'-'*70}")
        """
        # ------------------------------------------------------------------------
        # HARMONISATION DU CRS
        # ------------------------------------------------------------------------
        if gdf_elements.crs != gdf_PR.crs:
            print(f"   Reprojection de {nom_colonne} vers {gdf_PR.crs}...")
            gdf_elements = gdf_elements.to_crs(gdf_PR.crs)
        """
        # ------------------------------------------------------------------------
        # IDENTIFICATION DES ÉLÉMENTS NON AFFILIÉS
        # ------------------------------------------------------------------------
        print(f"   Identification des éléments non affiliés...")
        
        # Jointure spatiale pour identifier les affiliations
        jointure = gpd.sjoin(
            gdf_elements,
            gdf_PR[['nom_plo_fi', 'geometry']],
            how='left',
            predicate='intersects'
        )
        
        # Les éléments non affiliés sont ceux où nom_plo_fi est NaN
        non_affilies = gdf_elements.loc[jointure[jointure['nom_plo_fi'].isna()].index]
        
        # Cas particulier : aucun élément non affilié
        if len(non_affilies) == 0:
            print(f"   ✅ Aucun élément non affilié pour {nom_colonne} !")
            
            stats[nom_colonne] = {
                'distances': np.array([]),
                'stats_distances': {},
                'repartition_tranches': {},
                'tampon_suggere': 0,
                'pct_moins_5m': 0.0,
                'pct_moins_10m': 0.0,
                'nb_non_affilies': 0,
                'recommandation': "✅ Tous les éléments sont affiliés. Aucune action nécessaire."
            }
            continue
        
        nb_non_affilies = len(non_affilies)
        nb_total = len(gdf_elements)
        pct_non_affilies = round(nb_non_affilies / nb_total * 100, 1)
        
        print(f"   • Nombre d'éléments non affiliés : {nb_non_affilies} / {nb_total} ({pct_non_affilies}%)")
        
        # ------------------------------------------------------------------------
        # CALCUL DES DISTANCES (méthode optimisée avec KDTree)
        # ------------------------------------------------------------------------
        print(f"   Calcul des distances au tronçon le plus proche...")
        
        distances = []
        
        for idx, element in non_affilies.iterrows():
            # Extraire les coordonnées de l'élément selon son type
            if element.geometry.geom_type == 'Point':
                coords = [(element.geometry.x, element.geometry.y)]
            
            elif element.geometry.geom_type in ['LineString', 'MultiLineString']:
                if element.geometry.geom_type == 'LineString':
                    coords_raw = list(element.geometry.coords)
                else:
                    coords_raw = []
                    for line in element.geometry.geoms:
                        coords_raw.extend(list(line.coords))
                # Prendre seulement X et Y
                coords = [(c[0], c[1]) for c in coords_raw]
            
            else:  # Polygon, MultiPolygon, ou autre
                # Utiliser le centroid pour les géométries complexes
                coords = [(element.geometry.centroid.x, element.geometry.centroid.y)]
            
            # Trouver la distance minimale à un point de tronçon
            dist_min = float('inf')
            for coord in coords:
                dist, _ = tree.query(coord)
                dist_min = min(dist_min, dist)
            
            distances.append(dist_min)
        
        distances = np.array(distances)
        
        # ------------------------------------------------------------------------
        # CALCUL DES STATISTIQUES
        # ------------------------------------------------------------------------
        
        stats_distances = {
            'min': round(distances.min(), 2),
            'percentile_25': round(np.percentile(distances, 25), 2),
            'mediane': round(np.median(distances), 2),
            'percentile_75': round(np.percentile(distances, 75), 2),
            'percentile_95': round(np.percentile(distances, 95), 2),
            'max': round(distances.max(), 2),
            'moyenne': round(distances.mean(), 2)
        }
        
        print(f"\n   📊 Statistiques des distances (en mètres) :")
        print(f"      • Distance minimale     : {stats_distances['min']:.2f} m")
        print(f"      • 25e percentile        : {stats_distances['percentile_25']:.2f} m")
        print(f"      • Distance médiane      : {stats_distances['mediane']:.2f} m")
        print(f"      • 75e percentile        : {stats_distances['percentile_75']:.2f} m")
        print(f"      • 95e percentile        : {stats_distances['percentile_95']:.2f} m")
        print(f"      • Distance maximale     : {stats_distances['max']:.2f} m")
        print(f"      • Distance moyenne      : {stats_distances['moyenne']:.2f} m")
        
        # ------------------------------------------------------------------------
        # RÉPARTITION PAR TRANCHES DE DISTANCE
        # ------------------------------------------------------------------------
        
        tranches = [
            (0, 1, "0-1 m (très proche, prob. erreur de digitalisation)"),
            (1, 5, "1-5 m (proche, imprécision GPS/carto possible)"),
            (5, 10, "5-10 m (assez proche)"),
            (10, 50, "10-50 m (éloigné)"),
            (50, float('inf'), "> 50 m (très éloigné, vraiment hors tronçon)")
        ]
        
        repartition_tranches = {}
        
        print(f"\n   📏 Répartition par tranches de distance :")
        
        for min_d, max_d, label in tranches:
            count = ((distances >= min_d) & (distances < max_d)).sum()
            pct = round(count / len(distances) * 100, 1)
            repartition_tranches[label] = {'count': int(count), 'pct': pct}
            print(f"      {label:50s} : {count:5d} ({pct:5.1f}%)")
        
        # ------------------------------------------------------------------------
        # RECOMMANDATION DE TAMPON
        # ------------------------------------------------------------------------
        
        pct_moins_5m = round((distances < 5).sum() / len(distances) * 100, 1)
        pct_moins_10m = round((distances < 10).sum() / len(distances) * 100, 1)
        
        print(f"\n   💡 RECOMMANDATION :")
        
        if pct_moins_5m > 50:
            print(f"      ⚠️  {pct_moins_5m:.1f}% des non-affiliés sont à < 5 m")
            print(f"      → Recommandation : TAMPON de 5 m fortement conseillé")
            tampon_suggere = 5
            recommandation = (
                f"⚠️ TAMPON FORTEMENT CONSEILLÉ : {pct_moins_5m:.1f}% des éléments non affiliés "
                f"sont à moins de 5 m d'un tronçon. Un tampon de 5 m améliorerait significativement "
                f"la détection."
            )
        
        elif pct_moins_10m > seuil_tampon_suggestion:
            print(f"      ⚠️  {pct_moins_10m:.1f}% des non-affiliés sont à < 10 m")
            print(f"      → Recommandation : TAMPON de 10 m à considérer")
            tampon_suggere = 10
            recommandation = (
                f"⚠️ TAMPON À CONSIDÉRER : {pct_moins_10m:.1f}% des éléments non affiliés "
                f"sont à moins de 10 m d'un tronçon. Un tampon de 10 m pourrait améliorer "
                f"la détection."
            )
        
        else:
            print(f"      ✅ Seulement {pct_moins_10m:.1f}% des non-affiliés sont à < 10 m")
            print(f"      → Recommandation : PAS de tampon nécessaire")
            print(f"         Les non-affiliations semblent légitimes (éléments réellement éloignés)")
            tampon_suggere = 0
            recommandation = (
                f"✅ PAS DE TAMPON NÉCESSAIRE : Seulement {pct_moins_10m:.1f}% des éléments "
                f"non affiliés sont à moins de 10 m d'un tronçon. Les non-affiliations "
                f"semblent légitimes (éléments réellement hors tronçons)."
            )
        
        # ------------------------------------------------------------------------
        # STOCKAGE DES STATISTIQUES
        # ------------------------------------------------------------------------
        
        stats[nom_colonne] = {
            # Données brutes
            'distances': distances,
            
            # Statistiques descriptives
            'stats_distances': stats_distances,
            'repartition_tranches': repartition_tranches,
            
            # Métriques de décision
            'tampon_suggere': tampon_suggere,
            'pct_moins_5m': pct_moins_5m,
            'pct_moins_10m': pct_moins_10m,
            
            # Contexte
            'nb_non_affilies': nb_non_affilies,
            'nb_total_elements': nb_total,
            'pct_non_affilies': pct_non_affilies,
            
            # Recommandation textuelle
            'recommandation': recommandation
        }
    
    # ============================================================================
    # ÉTAPE 5 : RÉSUMÉ FINAL
    # ============================================================================
    
    print(f"\n{'='*70}")
    print(f"RÉSUMÉ : {nom_categorie.upper()}")
    print(f"{'='*70}")
    print(f"✅ {len(dict_couches)} couche(s) analysée(s)")
    print(f"✅ Statistiques d'attribution disponibles dans le dictionnaire retourné")
    
    # Afficher un résumé des recommandations
    print(f"\n📋 Synthèse des recommandations :")
    for nom_colonne, stat in stats.items():
        tampon = stat['tampon_suggere']
        if tampon > 0:
            print(f"   • {nom_colonne:30s} : Tampon de {tampon} m suggéré")
        else:
            print(f"   • {nom_colonne:30s} : Pas de tampon nécessaire")
    
    print(f"{'='*70}\n")
    
    return stats


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================
# stats_attribution_zones_critiques = analyser_attribution_elements_sur_troncon(gdf_troncons, dict_zones_critiques, 'zones_critiques', seuil_tampon_suggestion=30)
'''