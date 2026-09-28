# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_P4_impact"
Date : 2026-02-17
Objectif : calculer l'indicateur P4 impact'
═══════════════════════════════════════════════════════════════════

Calcul de l'indicateur P4 - Risque de colonisation des tronçons adjacents à enjeux.
    Logique : un tronçon colonisé par EEE est prioritaire si ses voisins directs dans le
              réseau routier sont non colonisés ET vulnérables sur plusieurs indicateurs.

    Paramètres :
        - gdf_EEE : Gdf des points de présence EEE, colonnes 'nom_plo_fi' et géométrie
        - gdf_troncons_copy : Gdf des tronçons (LineString), colonne 'nom_plo_fi'
        - df_scoring : DF contenant les tronçons, colonnes *_vulnerabilite

    Sortie : nouvelle colonne 'P4_impact' dans df_scoring, valeurs entières de 0 à 4.
    """
import pandas as pd
import geopandas as gpd
import networkx as nx   
    
def calculer_P4_impact(gdf_EEE, gdf_troncons_copy, df_scoring):

    print(f"\n{'='*70}")
    print("CALCUL P4_IMPACT - Risque de colonisation des tronçons adjacents à enjeux")
    print(f"{'='*70}\n")

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1 — Vérification des colonnes nécessaires
    # ──────────────────────────────────────────────────────────────────────────
    if 'nom_plo_fi' not in gdf_EEE.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_EEE")
    if 'nom_plo_fi' not in gdf_troncons_copy.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_troncons_copy")
    if 'nom_plo_fi' not in df_scoring.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans df_scoring")

    # Détection dynamique de toutes les colonnes *_vulnerabilite
    cols_vulnerabilite = [col for col in df_scoring.columns if col.endswith('_vulnerabilite')]
    if len(cols_vulnerabilite) == 0:
        raise ValueError("❌ Aucune colonne '*_vulnerabilite' trouvée dans df_scoring")
    print(f"Colonnes de vulnérabilité détectées : {cols_vulnerabilite}")


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 — Identifier les tronçons colonisés par EEE
    # On éclate les nom_plo_fi multi-valeurs (même logique que MS1/MS2/MS3)
    # puis on liste les tronçons avec au moins 1 point EEE.
    # ──────────────────────────────────────────────────────────────────────────
    gdf_EEE_explode = gdf_EEE.copy()
    gdf_EEE_explode = gdf_EEE_explode.assign(
        nom_plo_fi=gdf_EEE_explode['nom_plo_fi'].str.split(',')
    ).explode('nom_plo_fi')
    gdf_EEE_explode['nom_plo_fi'] = gdf_EEE_explode['nom_plo_fi'].str.strip()

    troncons_colonises = set(gdf_EEE_explode['nom_plo_fi'].dropna().unique())
    print(f"Tronçons colonisés par EEE : {len(troncons_colonises)}")

    # Diagnostic rapide à lancer :
    print("Type dans troncons_colonises :", type(list(troncons_colonises)[0]))
    print("Type dans df_scoring :", type(df_scoring['nom_plo_fi'].iloc[0]))
    print("Exemple troncons_colonises :", list(troncons_colonises)[:5])
    print("Exemple df_scoring :", df_scoring['nom_plo_fi'].head().tolist())
    print("Intersection :", len(set(df_scoring['nom_plo_fi']) & troncons_colonises))


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Construction du graphe réseau (Option C — networkx)
    # Deux tronçons sont adjacents si leurs géométries se touchent ou s'intersectent.
    # On construit un graphe où chaque nœud = nom_plo_fi, chaque arête = adjacence.
    # ──────────────────────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Construction du graphe réseau
    # predicate='intersects' est trop permissif (capure les ponts/croisements)
    # predicate='touches' est trop strict (micro-gaps topologiques dans les données)
    # Solution : buffer de 1m autour de chaque tronçon avant sjoin
    # → capture les quasi-contacts sans relier des routes superposées (ponts etc.)
    # ──────────────────────────────────────────────────────────────────────────
    import networkx as nx

    G = nx.Graph()
    for _, row in gdf_troncons_copy.iterrows():
        G.add_node(row['nom_plo_fi'])

    # Créer une version avec micro-buffer pour pallier les micro-gaps topologiques
    # 1m est suffisant pour combler les imprecisions sans relier des routes non connectées
    gdf_troncons_buffer = gdf_troncons_copy.copy()
    gdf_troncons_buffer['geometry'] = gdf_troncons_buffer['geometry'].buffer(1)

    adjacences = gpd.sjoin(
        gdf_troncons_copy[['nom_plo_fi', 'geometry']],   # lignes originales
        gdf_troncons_buffer[['nom_plo_fi', 'geometry']], # lignes bufferisées
        how='inner',
        predicate='intersects'
    )

    # Renommer les colonnes après sjoin (suffixes _left/_right automatiques)
    adjacences = adjacences.rename(columns={
        'nom_plo_fi_left':  'nom_plo_fi_left',
        'nom_plo_fi_right': 'nom_plo_fi_right'
    })

    for _, row in adjacences.iterrows():
        if row['nom_plo_fi_left'] != row['nom_plo_fi_right']:
            G.add_edge(row['nom_plo_fi_left'], row['nom_plo_fi_right'])

    print(f"Graphe réseau : {G.number_of_nodes()} nœuds, {G.number_of_edges()} arêtes")

    # Diagnostic : vérifier le nb de voisins sur le tronçon test
    troncon_test = '35PR16D'
    voisins = list(G.neighbors(troncon_test))
    print(f"Voisins de {troncon_test} : {len(voisins)} → {voisins[:10]}")

    '''
    # ──────────────────────────────────────────────────────────────────────────
    # OPTION B — Adjacence par buffer (alternative si pas de géométrie réseau)
    # On crée un buffer autour de chaque tronçon colonisé et on identifie
    # quels tronçons non colonisés intersectent ce buffer.
    # Buffer = 50m par défaut (ordre de grandeur dispersion locale EEE routières)
    # ──────────────────────────────────────────────────────────────────────────
    BUFFER_M = 50  # à ajuster selon contexte

    voisins_buffer = {}
    troncons_colonises_gdf = gdf_troncons_copy[
        gdf_troncons_copy['nom_plo_fi'].isin(troncons_colonises)
    ].copy()

    for _, row in troncons_colonises_gdf.iterrows():
        buffer = row['geometry'].buffer(BUFFER_M)
        intersectes = gdf_troncons_copy[
            gdf_troncons_copy['geometry'].intersects(buffer) &
            (gdf_troncons_copy['nom_plo_fi'] != row['nom_plo_fi'])
        ]['nom_plo_fi'].tolist()
        voisins_buffer[row['nom_plo_fi']] = intersectes
    '''


    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 4 — Calcul du score de vulnérabilité des voisins non colonisés
    # Pour chaque tronçon colonisé :
    #   1. Trouver ses voisins directs (degré 1 dans le graphe)
    #   2. Garder ceux non colonisés
    #   3. Pour chacun, compter le nb de colonnes *_vulnerabilite = 'oui'
    #   4. Score de risque = max(nb_vulnerabilites_voisin) × nb_voisins_concernes
    #
    # Tableau de décision :
    #   score_exposition = 0                    → P4 = 1 (colonisé mais aucun voisin vulnérable)
    #   score_exposition > 0, 1 indicateur      → P4 = 2
    #   score_exposition > 0, 2 indicateurs     → P4 = 3
    #   score_exposition > 0, 3+ indicateurs    → P4 = 4
    #   OU ≥2 voisins vulnérables sur 1+ indic  → P4 = 4
    # ──────────────────────────────────────────────────────────────────────────

    # Créer un dict troncon → nb de vulnérabilités 'oui'
    df_vuln = df_scoring[['nom_plo_fi'] + cols_vulnerabilite].copy()
    df_vuln['nb_vulns'] = df_vuln[cols_vulnerabilite].apply(
        lambda row: (row == 'oui').sum(), axis=1
    )
    vuln_par_troncon = df_vuln.set_index('nom_plo_fi')['nb_vulns'].to_dict()

    scores_P4 = {}

    for troncon in df_scoring['nom_plo_fi']:

        # Tronçon non colonisé → score 0
        if troncon not in troncons_colonises:
            scores_P4[troncon] = 0
            continue

        # Voisins directs dans le graphe
        if troncon not in G.nodes:
            scores_P4[troncon] = 1  # colonisé mais isolé dans le graphe
            continue

        voisins = list(G.neighbors(troncon))

        # Voisins non colonisés ET avec au moins 1 vulnérabilité
        voisins_a_risque = [
            v for v in voisins
            if v not in troncons_colonises
            and vuln_par_troncon.get(v, 0) > 0
        ]

        if len(voisins_a_risque) == 0:
            scores_P4[troncon] = 1  # colonisé mais aucun voisin vulnérable non colonisé
            continue

        # Score d'exposition : nb_vulns max parmi les voisins à risque
        max_vulns  = max(vuln_par_troncon.get(v, 0) for v in voisins_a_risque)
        nb_voisins = len(voisins_a_risque)

        # Tableau de décision
        if nb_voisins >= 2 or max_vulns >= 3:
            scores_P4[troncon] = 4
        elif max_vulns == 2:
            scores_P4[troncon] = 3
        elif max_vulns == 1:
            scores_P4[troncon] = 2
        else:
            scores_P4[troncon] = 1

    df_scoring['P4_impact'] = df_scoring['nom_plo_fi'].map(scores_P4).fillna(0).astype(int)

    # Diagnostic 2 — inspecter ce qui se passe pour UN tronçon colonisé
    troncon_test = list(troncons_colonises)[0]
    print(f"Tronçon test : {troncon_test}")
    print(f"Dans le graphe : {troncon_test in G.nodes}")

    voisins = list(G.neighbors(troncon_test))
    print(f"Nb voisins directs : {len(voisins)}")
    print(f"Voisins : {voisins[:10]}")

    voisins_non_colonises = [v for v in voisins if v not in troncons_colonises]
    print(f"Voisins non colonisés : {len(voisins_non_colonises)}")

    voisins_a_risque = [v for v in voisins_non_colonises if vuln_par_troncon.get(v, 0) > 0]
    print(f"Voisins non colonisés ET vulnérables : {len(voisins_a_risque)}")

    # Inspecter les vulnérabilités des voisins
    print("\nDétail vulnérabilités voisins à risque :")
    for v in voisins_a_risque[:5]:
        print(f"  {v} : nb_vulns={vuln_par_troncon.get(v, 0)}")

    # Vérifier aussi vuln_par_troncon — est-ce que des tronçons ont nb_vulns > 0 ?
    print(f"\nDistribution nb_vulns dans df_scoring :")
    print(df_vuln['nb_vulns'].value_counts().sort_index())
    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 5 — Statistiques de contrôle
    # ──────────────────────────────────────────────────────────────────────────
    print(f"\nRésultats :")
    print(f"  Tronçons colonisés : {len(troncons_colonises)}")
    print(f"  Tronçons score max (4) : {(df_scoring['P4_impact'] == 4).sum()}")
    print(f"  Distribution des scores :")
    for score, count in df_scoring['P4_impact'].value_counts().sort_index().items():
        print(f"    Score {score} : {count} tronçons")
    print(f"\n{'='*70}\n")

    return df_scoring
