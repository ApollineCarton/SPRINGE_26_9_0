# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_MS3_impact"
Date : 2026-09-09
Objectif : calculer l'indicateur MS3 impact'
═══════════════════════════════════════════════════════════════════

Calcul de l'impact des EEE sur les troncons pour l'indicateur MS3 - risque patrimoine routier
Logique : croiser l'agressivité racinaire des EEE présentes sur le tronçon
          avec la vulnérabilité du tronçon (présence d'ouvrages).

Paramètres :
    - gdf_EEE : Gdf des points de présence EEE, colonnes 'nom_plo_fi' et ''species_name_sci''
    - EEE_caracterisques_excel : Xl des caractéristiques biologiques de chaque EEE
    - df_scoring : DF contenant les tronçons et leur MS3_vulnerabilite (oui/non)

Sortie : nouvelle colonne 'MS3_impact' dans df_scoring, valeurs entières de 0 à 5.

----------
# dans EEE_caracterisques_excel : 
    # -> variable root_system_type -> root_system_type
C'est le type morphologique du système racinaire. Dans tes données tu as :

drageon (Ailante) → racines traçantes horizontales très agressives, colonisent latéralement sur des dizaines de mètres
pivotant (Ambroisie, Berce) → racine centrale verticale profonde, pression localisée mais forte en pénétration
rhizomateux (Renouée) → réseau horizontal dense et très ramifié, extrêmement infiltrant dans les fissures
fasciculé (EEE autre) → racines superficielles en faisceau, moins agressives mécaniquement

C'est une variable qualitative très discriminante pour le type de dommage (soulèvement vs fissuration vs infiltration).

    # -> variable root_penetration_force -> 
C'est la force mécanique exercée par la croissance racinaire sur les matériaux. 
Forte / moyenne / faible. C'est la variable la plus directement liée aux dégâts sur ouvrages.

    # -> variable root_depth_cm ->
C'est la profondeur maximale d'enracinement. Elle conditionne quels types d'infrastructures sont menacés :

Peu profond (< 40 cm) → chaussée, trottoir
Moyen (40–100 cm) → réseaux enterrés superficiels, fondations légères
Profond (> 100 cm) → fondations, ouvrages d'art, murs de soutènement


# si plusieurs EEE sur un troncon (nom_plo_fi), garder la valeur maximale (3 > 2 > 1 > 0)

# jointure : df_scoring & gdf_EEE ont variable 'nom_plot_fi'
# jointure : gdf_EEE a variable ''species_name_sci'' avec nom de la plante <-> EEE_SHEET a variable 'nom' avec la même chose

# dans df_scoring on a la colonne MS2_vulnerabilité (oui/non) : est ce que le tronçon est vulnérable - présence patrimoine routier ? (un tronçon vulnérable 'oui' ossède des zones d'exposition prolongées des usagers, comme aires de repos, habitations etc)
# creer colonne MS2_impact dans df_scoring
# conditions du scoring :
    # commencer par définir le risque_sanitaire (allergenicity_score & contact_toxicity_score)
    # on additionne allergenicity_score et contact_toxicity_score (donc on a une échelle de valeurs de 0 à 6)
    # risque_sanitaire : fort (= 5-6) > modéré (= 3-4) > faible (= 1-2) > nul (=0)

Niveau 1 : score de base avec root_penetration_force
'forte'=3 ; 'moyenne'=2 ; 'faible' = 1

Niveau 2 : modificateurs root_depth_cm & root_system_type
'delta(depth)' -> root_depth_cm : module l'exposition aux ouvrages enterrés
    - +100cm : +1, atteinte fondations et réseaux profonds
    - 40-100cm : +0, neutre
    - <40cm : -1, impact limité à la surface
'delta(type)' -> root_system_type : module le mode de propagation, donc la surface de dégâts
    - rhizomateux ou drageaon ! +1 (expansion latérale, infiltrations diffuses sur toute l'emprise)
    - pivotant : +0 (impact localisé mais concentré)
    - fasciculé : -1 (peu aggressif pour la structure)

# agressivite_racinaire = score_base(penetration) + delta(depth) + delta(type) --> calcul effectué directement dans l'excel dans la variable 'root_aggresivity'

    # df_scoring<MS3_vulnerabilité='oui' + root_aggresivity = 'fort' -> mettre dans MS3_impact '5' (en numérique)
    # df_scoring<MS3_vulnerabilité='oui' + root_aggresivity ='modéré' -> mettre dans MS3_impact '4' (en numérique)
    # df_scoring<MS3_vulnerabilité='oui' + root_aggresivity ='faible' OU df_scoring<MS3_vulnerabilité='non' + root_aggresivity ='fort' -> mettre dans MS3_impact '3' (en numérique)
    # df_scoring<MS3_vulnerabilité='non' + root_aggresivity ='moyenne' -> mettre dans MS3_impact '2' (en numérique)
    # df_scoring<MS3_vulnerabilité='non' + root_aggresivity ='modéré' OU df_scoring<MS3_vulnerabilité='non' + root_aggresivity 'faible' -> mettre dans MS3_impact '1' (en numérique)
    # df_scoring<MS3_vulnerabilité='non' + root_aggresivity = 'nul' -> mettre dans MS3_impact '0' (en numérique)
---------
"""
import pandas as pd

def calculer_MS3_impact(gdf_EEE, EEE_caracterisques_excel, df_scoring):
  

    print(f"\n{'='*70}")
    print("CALCUL MS3_IMPACT - Imapct des EEE sur le patrimoine routier dans le tronçon (système racinaire)")
    print(f"{'='*70}\n")

    #____________________________________________________________
    # ETAPE 1 : Vérifier l'existance des colonnes d'intêret
    # on s'assure que toutes les colonnes attendues sont bien présentes
    # dans chaque dataframe avant de commencer les calculs, pour éviter
    # les erreurs silencieuses plus après dans le code
    #____________________________________________________________

    # Vérifier colonnes
    if 'nom_plo_fi' not in gdf_EEE.columns:
        raise ValueError("❌ 'nom_plo_fi' introuvable dans gdf_EEE")
    
    if 'species_name_sci' not in gdf_EEE.columns:
        raise ValueError(
            "❌ 'species_name_sci' introuvable dans gdf_EEE. "
            "fenetre_mapping_especes.mapping_interactif_especes() doit être "
            "appelée avant ce module."
        )

    if 'species_name_sci' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'species_name_sci' introuvable dans EEE_caracterisques_excel")

    if 'root_penetration_force' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'height_max_cm' introuvable dans EEE_caracterisques_excel")

    if 'root_depth_cm' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'height_max_cm' introuvable dans EEE_caracterisques_excel")

    if 'root_system_type' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'height_max_cm' introuvable dans EEE_caracterisques_excel")

    if 'root_aggressivity' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'root_aggressivity' introuvable dans EEE_caracterisques_excel")

    if 'MS3_vulnerabilite' not in df_scoring.columns:
        raise ValueError("❌ 'MS1_vulnerabilite' introuvable dans df_scoring")

    # ──────────────────────────────────────────────────────────────────────────
    # Espèces : on consomme le mapping déjà fait, on ne le refait pas
    # ──────────────────────────────────────────────────────────────────────────
    # MODIFICATION DU 2026-09-08 — suppression du dictionnaire local.
    #
    # Ce module embarquait sa propre table {'Renouees': 'Reynoutria sp', ...}
    # figée sur la colonne ''species_name_sci''. Cinq modules en avaient chacun une copie,
    # ce qui neutralisait purement et simplement le travail de
    # fenetre_mapping_especes : le gestionnaire pouvait déclarer que sa colonne
    # d'espèces s'appelle 'ESPECE' et contient 'REYNOUTRIA JAPONICA', le module
    # cherchait quand même ''species_name_sci'' et 'Renouees', et sortait des NaN partout.
    #
    # On consomme désormais 'species_name_sci', produit une seule fois en amont
    # par la fenêtre de mapping et déjà utilisé comme clé de jointure ici.
    gdf_EEE_mapped = gdf_EEE.copy()

    # Un point sans espèce reconnue n'est pas une erreur : le gestionnaire a pu
    # choisir « aucune correspondance » pour une espèce hors référentiel SPRINGE.
    # Ces points seront écartés par la jointure ci-dessous, on le signale.
    non_mappes = int(gdf_EEE_mapped['species_name_sci'].isna().sum())
    if non_mappes > 0:
        print(f"ℹ️  {non_mappes} point(s) sans espèce de référence (écartés du calcul)")

    #____________________________________________________________
    # ETAPE 2 : Jointure de gdf_EEE avec EEE_caracteriques_excel
    # on enrichi gdf_EEE (qui contient les points de présence EEE sur les troncons)
    # avec les scores sanitaires (allergicity_score et contact_toxicity_score) issus du fichier de caractérisques
    # la jointure se fait via 'species_name_sci', déjà mappé plus haut dans le script (mapping Rennouees -> Reynoutria sp, ETC.)
    # on ne récupère que les 2 colonnes utiles pour le calcul de MS2
    #____________________________________________________________

    
    #jointure avec EEE_caracterisques_excel pour récupérer 'hauteur_EEE'
    gdf_EEE_enrichi = gdf_EEE_mapped.merge(
        EEE_caracterisques_excel[['species_name_sci', 'root_penetration_force', 'root_depth_cm', 'root_system_type', 'root_aggressivity']],
        on= 'species_name_sci',
        how='left'
    )


    # Version 1 : calcul de roor_aggressivity dans le code
    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 — Calcul du score d'agressivité racinaire
    # Score = base(penetration_force) + delta(root_depth_cm) + delta(root_system_type)
    #
    # Score de base — root_penetration_force (variable la plus causale) :
    #   forte   → 3
    #   moyenne → 2
    #   faible  → 1
    #
    # Modificateur — root_depth_cm (exposition aux ouvrages enterrés) :
    #   > 100 cm  → +1  (atteint fondations et réseaux profonds)
    #   40-100 cm → +0  (zone intermédiaire, neutre)
    #   < 40 cm   → -1  (impact limité aux surfaces)
    #
    # Modificateur — root_system_type (mode de propagation et surface de dégât) :
    #   rhizomateux ou drageon → +1  (expansion latérale diffuse sur toute l'emprise)
    #   pivotant               → +0  (impact localisé mais concentré)
    #   fasciculé              → -1  (peu agressif structurellement)
    # ──────────────────────────────────────────────────────────────────────────
    score_penetration = {
        'forte':   3,
        'moyenne': 2,
        'faible':  1
    } # frote moyenne faible c'est ce qu'on retrouve dans le excel

    def delta_depth(depth_cm):
        try:
            # Si la valeur est une fourchette "50-100", on prend le max (100)
            if '-' in str(depth_cm):
                depth = float(str(depth_cm).split('-')[-1])
            else:
                depth = float(depth_cm)

            if depth > 100:   return  1
            elif depth >= 40: return  0
            else:             return -1
        except:
            return 0  # valeur manquante ou non parseable → neutre

    delta_type = {
        'rhizomateux': +1,
        'drageon':     +1,
        'pivotant':     0,
        'fasciculé':   -1
    }

    # Application des trois composantes
        #.astype(int) : erreur type +d : format pour les entiers (int) mais c'était des floats d'après .map() et .apply(), on force en int au moment du calcul
    gdf_EEE_enrichi['score_penetration'] = gdf_EEE_enrichi['root_penetration_force'].map(score_penetration).fillna(0).astype(int)
    gdf_EEE_enrichi['delta_depth']       = gdf_EEE_enrichi['root_depth_cm'].apply(delta_depth).astype(int)
    gdf_EEE_enrichi['delta_type']        = gdf_EEE_enrichi['root_system_type'].map(delta_type).fillna(0).astype(int)

    gdf_EEE_enrichi['agressivite_score'] = (
        gdf_EEE_enrichi['score_penetration'] +
        gdf_EEE_enrichi['delta_depth'] +
        gdf_EEE_enrichi['delta_type']
    )

    # Affichage de contrôle par espèce
    print("Agressivité racinaire par espèce EEE :")
    agressivite_eee = (
        gdf_EEE_enrichi[['species_name_sci', 'score_penetration', 'delta_depth', 'delta_type', 'agressivite_score']]
        .drop_duplicates()
        .sort_values('agressivite_score', ascending=False)
    )
    for _, row in agressivite_eee.iterrows():
        print(f"  {row['species_name_sci']}: pénétration={row['score_penetration']}, "
              f"profondeur={row['delta_depth']:+d}, "
              f"type={row['delta_type']:+d} "
              f"→ score={row['agressivite_score']}")

    # VERSION 2 : calcul préalable dans excel de root_aggressivity

    #____________________________________________________________
    # ÉTAPE 4 — Catégorisation de l'agressivité racinaire
    # On convertit le score numérique en catégorie textuelle.
    # Échelle : ≥4 → forte | 2-3 → modérée | 1 → faible | ≤0 → nulle
    #____________________________________________________________

    def categoriser_agressivite(valeur):
        try:
            if valeur >= 4:   return 'fort'
            elif valeur >= 2: return 'modéré'
            elif valeur >= 1: return 'faible'
            else:             return 'nul'
        except:
            return None
            # les lables forts modéré faible nul doivent être identiques ici et dans 'ordre_agressivite_racinaire'

    gdf_EEE_enrichi['agressivite_racinaire'] = gdf_EEE_enrichi['agressivite_score'].apply(categoriser_agressivite)


    
    #____________________________________________________________
    #ETAPE 5 : Agrégation par tronçon : garder l'agressivité MAX
    # Même logique que MS2 : on convertit en rang, on trie, on prend le premier
    # par tronçon via groupby.first().
    # — Éclatement des nom_plo_fi multi-valeurs
    # Dans gdf_EEE, nom_plo_fi peut contenir plusieurs tronçons séparés par des
    # virgules ex: "35PR12D, 35PR12G". On éclate chaque ligne en autant de lignes
    # que de tronçons, pour que la jointure avec df_scoring fonctionne correctement.
    #____________________________________________________________
    '''
    nb_avant = len(gdf_EEE_enrichi)  # ← on sauvegarde la taille AVANT
    gdf_EEE_enrichi = gdf_EEE_enrichi.assign(
        nom_plo_fi = gdf_EEE_enrichi['nom_plo_fi'].str.split(',')
    ).explode('nom_plo_fi')

    # Nettoyer les espaces résiduels après le split ("35PR12D, 35PR12G" → " 35PR12G")
    gdf_EEE_enrichi['nom_plo_fi'] = gdf_EEE_enrichi['nom_plo_fi'].str.strip()

    print("Vérification après éclatement :")
    print(f"  Lignes avant : {nb_avant} → après explode : {len(gdf_EEE_enrichi)}")
    print(f"  Exemple nom_plo_fi uniques : {gdf_EEE_enrichi['nom_plo_fi'].unique()[:5]}")
    '''    
    # hauteur maximale par troncon
    ordre_agressivite_racinaire = {'fort':3, 'modéré':2, 'faible':1, 'nul':0}
  
    agressivite_eee_par_troncon = (
        gdf_EEE_enrichi[['nom_plo_fi', 'agressivite_racinaire']]
        .dropna(subset=['agressivite_racinaire'])
        .assign(agressivite_rank=lambda x: x['agressivite_racinaire'].map(ordre_agressivite_racinaire))
        .sort_values('agressivite_rank', ascending=False)
        .groupby('nom_plo_fi')
        .first()
        .reset_index()
        [['nom_plo_fi', 'agressivite_racinaire']]
    )

    
    #____________________________________________________________
    #ETAPE 6 : jointure dans df_scoring
    # on rattache les riques sanitiares max par troncon à df_scoring
    #les troncons sans aucune EEE auront risque_sanitaire = NaN -> 'aucune'
    #____________________________________________________________

    #jointure avec df_scoring
    df_scoring = df_scoring.merge(
        agressivite_eee_par_troncon,
        on='nom_plo_fi',
        how='left'
    )

    #les troncons sans EEE ont hauteur_EEE = NaN
    df_scoring['agressivite_racinaire'] = df_scoring['agressivite_racinaire'].fillna('aucune')

    #____________________________________________________________
    #ETAPE 7 : — Scoring MS3_impact
    # Croisement MS3_vulnerabilite (oui/non) × agressivité (forte/modérée/faible/nulle)
    #____________________________________________________________

    # Scoring MS3 imapct
    def attribuer_points_MS3(row):
        vuln       = row['MS3_vulnerabilite']
        agressivite = row['agressivite_racinaire']

        if vuln == 'oui':
            if agressivite == 'fort':   return 5
            if agressivite == 'modéré': return 4
            if agressivite == 'faible':  return 3
        else:  # vuln == 'non'
            if agressivite == 'fort':   return 3
            if agressivite == 'modéré': return 2
            if agressivite == 'faible':  return 1
        return 0  # nulle ou aucune EEE

    df_scoring.loc[:, 'MS3_impact'] = df_scoring.apply(attribuer_points_MS3, axis=1)

    # vérifications
    # --------------------------------
    
    # 1. Est-ce que gdf_EEE_mapped a bien la colonne species_name_sci ?
    print("=== 1. Mapping EEE ===")
    print(gdf_EEE_mapped[['species_name_sci']].value_counts())

    # 2. Est-ce que la jointure a ramené les variables racinaires ?
    print("\n=== 2. Après jointure — variables racinaires ===")
    print(gdf_EEE_enrichi[['species_name_sci', 'species_name_sci', 'root_penetration_force', 'root_depth_cm', 'root_system_type']].drop_duplicates())

    # 3. Est-ce que les scores intermédiaires sont calculés ?
    print("\n=== 3. Scores intermédiaires ===")
    print(gdf_EEE_enrichi[['species_name_sci', 'score_penetration', 'delta_depth', 'delta_type', 'agressivite_score']].drop_duplicates())

    # 4. Est-ce que la catégorisation donne autre chose que None ?
    print("\n=== 4. Catégorie agressivite_racinaire ===")
    print(gdf_EEE_enrichi[['species_name_sci', 'agressivite_score', 'agressivite_racinaire']].drop_duplicates())

    # 5. Est-ce que l'agrégation par troncon a des résultats ?
    print("\n=== 5. Agressivité max par tronçon (5 premiers) ===")
    print(agressivite_eee_par_troncon.head())

    # 6. Après jointure avec df_scoring, est-ce que agressivite_racinaire est bien remplie ?
    print("\n=== 6. df_scoring après jointure (avant scoring) ===")
    print(df_scoring[['nom_plo_fi', 'MS3_vulnerabilite', 'agressivite_racinaire']].head(20))

    #____________________________________________________________
    # Nettoyage : supprimer la colonne temporaire hauteur_EEE de df_scoring
    # la colonne est temporaire pour le calcul intermédiaire, on supprime pour une sortie propre
    #____________________________________________________________

    df_scoring.drop(columns=['agressivite_racinaire'], inplace=True)

    #____________________________________________________________
    # ETAPE 9 : statistiques de controle
    #____________________________________________________________

    # ── Statistiques ─────────────────────────────────────────────────────────
    nb_troncons_eee = gdf_EEE['nom_plo_fi'].nunique()
    nb_score_max    = (df_scoring['MS3_impact'] == 5).sum()

    print(f"\nRésultats :")
    print(f"  Tronçons avec EEE : {nb_troncons_eee}")
    print(f"  Tronçons score max (5) : {nb_score_max}")
    print(f"  Distribution des scores :\n{df_scoring['MS3_impact'].value_counts().sort_index()}")
    print(f"\n{'='*70}\n")

    return df_scoring