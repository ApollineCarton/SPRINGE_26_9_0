# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_MS2_impact"
Date : 2026-02-17
Objectif : calcul de l'indicateur MS2 impact'
═══════════════════════════════════════════════════════════════════

Calcul de l'impact des EEE sur les troncons pour l'indicateur MS2 - risque sanitaire
 Logique : attribuer des points dans df_scoring<MS1_impact selon les conditions dans le troncon

 Paramètres de la fonction :

     - gdf_EEE : Gdf des points de présence EEE, avec une colonne de jointure "nom_plo_fi" et "plante" pour avoir le nom de l'espèce EEE
     - EEE_SHEET : Xl des caractéristiques biologiques de chaque EEE
     - df_scoring : DF créé pour contenir les points et scores des indicateurs

La fonction sort : une nouvelle colonne 'MS2_impact' dans df_scoring, avec des valeurs numérique entier de 5 à 0 compris.

--------
# dans EEE_caracterisques_excel : 
    # -> variable allergenicity_score -> Score allergénicité (0=nul, 1=faible, 2=modéré, 3=fort)
    # -> variable contact_toxicity_score -> Score toxicité contact (0=nul, 1=faible, 2=modéré, 3=fort)

# si plusieurs EEE sur un troncon (nom_plo_fi), garder la valeur allergenicity_score & contact_toxicity_score maximale (3 > 2 > 1 > 0)

# jointure : df_scoring & gdf_EEE ont variable 'nom_plot_fi'
# jointure : gdf_EEE a variable 'plante' avec nom de la plante <-> EEE_SHEET a variable 'nom' avec la même chose

# dans df_scoring on a la colonne MS2_vulnerabilité (oui/non) : est ce que le tronçon est vulnérable face à un risque sanitiaire ? (un tronçon vulnérable 'oui' ossède des zones d'exposition prolongées des usagers, comme aires de repos, habitations etc)
# creer colonne MS2_impact dans df_scoring
# conditions du scoring :
    # commencer par définir le risque_sanitaire (allergenicity_score & contact_toxicity_score)
    # on additionne allergenicity_score et contact_toxicity_score (donc on a une échelle de valeurs de 0 à 6)
    # risque_sanitaire : fort (= 5-6) > modéré (= 3-4) > faible (= 1-2) > nul (=0)

    # df_scoring<MS2_vulnerabilité='oui' + risque_sanitaire = 'fort' -> mettre dans MS2_impact '5' (en numérique)
    # df_scoring<MS2_vulnerabilité='oui' + risque_sanitaire ='modéré' -> mettre dans MS2_impact '4' (en numérique)
    # df_scoring<MS2_vulnerabilité='oui' + risque_sanitaire ='faible' OU df_scoring<MS1_vulnerabilité='non' + risque_sanitaire ='fort' -> mettre dans MS2_impact '3' (en numérique)
    # df_scoring<MS2_vulnerabilité='non' + risque_sanitaire ='moyenne' -> mettre dans MS2_impact '2' (en numérique)
    # df_scoring<MS2_vulnerabilité='non' + risque_sanitaire ='modéré' OU df_scoring<MS1_vulnerabilité='non' + fable -> mettre dans MS2_impact '1' (en numérique)
    # df_scoring<MS2_vulnerabilité='non' + risque_sanitaire = 'nul' -> mettre dans MS2_impact '0' (en numérique)

-------
"""
import pandas as pd #pour .merge et .apply

def calculer_MS2_impact(gdf_EEE, EEE_caracterisques_excel, df_scoring):
        

    print(f"\n{'='*70}")
    print("CALCUL MS2_IMPACT - Impact des EEE sur le risque sanitaire (allergies/toxicité) dans le tronçon")
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

    if 'allergenicity_score' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'height_max_cm' introuvable dans EEE_caracterisques_excel")

    if 'contact_toxicity_score' not in EEE_caracterisques_excel.columns:
        raise ValueError("❌ 'height_max_cm' introuvable dans EEE_caracterisques_excel")

    if 'MS2_vulnerabilite' not in df_scoring.columns:
        raise ValueError("❌ 'MS1_vulnerabilite' introuvable dans df_scoring")

    # ──────────────────────────────────────────────────────────────────────────
    # Espèces : on consomme le mapping déjà fait, on ne le refait pas
    # ──────────────────────────────────────────────────────────────────────────
    # MODIFICATION DU 2026-09-08 — suppression du dictionnaire local.
    #
    # Ce module embarquait sa propre table {'Renouees': 'Reynoutria sp', ...}
    # figée sur la colonne 'plante'. Cinq modules en avaient chacun une copie,
    # ce qui neutralisait purement et simplement le travail de
    # fenetre_mapping_especes : le gestionnaire pouvait déclarer que sa colonne
    # d'espèces s'appelle 'ESPECE' et contient 'REYNOUTRIA JAPONICA', le module
    # cherchait quand même 'plante' et 'Renouees', et sortait des NaN partout.
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
        EEE_caracterisques_excel[['species_name_sci', 'allergenicity_score', 'contact_toxicity_score']],
        on= 'species_name_sci',
        how='left'
    )

    #____________________________________________________________
    #ETAPE 3 : calcul du score sanitaire combiné par point EEE
    # addition de alergicity_score et contact_toxicity_score pour obtenir un score combiné sur une échelle de 0 à 6
    #c'est ce score combiné 'risque_sanitaire' qui sera ensuite catégorisé en fort/modéré/faible/nul
    #____________________________________________________________

    
    print("Calcul risque sanitaire par espèce EEE:")

    gdf_EEE_enrichi['risque_sanitaire_score'] = (
        gdf_EEE_enrichi['allergenicity_score'] + gdf_EEE_enrichi['contact_toxicity_score'])

    # affichage de contrôle : score sanitaire par espèce
    risque_sanitaire = (
        gdf_EEE_enrichi[['species_name_sci', 'allergenicity_score', 'contact_toxicity_score', 'risque_sanitaire_score']]
        .drop_duplicates()
        .sort_values( ['allergenicity_score', 'contact_toxicity_score'], ascending=False) #sort_values attend une liste [,] de plusieurs colonnes
    )
    
    for _, row in risque_sanitaire.iterrows():
        print(f"  {row['species_name_sci']}: allergenicité={row['allergenicity_score']}, "
              f"toxicité={row['contact_toxicity_score']}, "
              f"score combiné={row['risque_sanitaire_score']}")

    #____________________________________________________________
    # ETAPE 4 : Catégorisation du risque sanitaire
    # on convertit le score numérique combiné (0-6) en catégories textuelles
    # echelle : 5-6 = fort | 3-4 = modéré | 1-2 = faible | 0 = nul
    #____________________________________________________________


    # Les scores risque sanitaire EEE sont numériques, transformation en catégories
    def categoriser_risque_sanitaire(valeur):
        try:
            if valeur >= 5:    return 'fort'
            elif valeur >= 3:  return 'modéré'
            elif valeur >= 1:  return 'faible'
            else:                return 'nul'
        except:
            return None  # si valeur manquante ou non parseable

    gdf_EEE_enrichi['risque_sanitaire'] = gdf_EEE_enrichi['risque_sanitaire_score'].apply(categoriser_risque_sanitaire)

    
    #____________________________________________________________
    #ETAPE 5 : aggréger par troncon
    # un troncon peut contenir plusieurs points EEE, et des espèces différentes
    # on garde le risque le plus élevé par troncon
    # on convertit els catégories en rang numériques, on trie, on prend le premier (le plus élevé) pour chaque troncon avec groupbu.first()
    #____________________________________________________________
    
    # hauteur maximale par troncon
    ordre_risque_sanitaire = {'fort':3, 'modéré':2, 'faible':1, 'nul':0}
  
    # ── Éclatement des points de bordure (harmonisation du 2026-09-08) ──────
    # PROBLÈME CORRIGÉ : join_num_troncon_a_gdf_EEE écrit "A, B" dans
    # nom_plo_fi quand un point tombe à cheval sur deux tronçons. Sans
    # éclatement, le groupby ci-dessous crée un groupe pour la clé LITTÉRALE
    # "A, B", qui ne correspond à aucun tronçon de df_scoring : le merge de
    # l'étape 6 ne le rattache nulle part et le point DISPARAÎT silencieusement
    # du calcul, pour les DEUX tronçons concernés.
    #
    # L'enjeu est direct ici : une ambroisie ou une berce du Caucase en limite
    # de tronçon serait perdue, alors que MS2 mesure précisément un risque
    # sanitaire pour les usagers et les agents.
    #
    # CHOIX RETENU (CS-14 du cadrage) : le point est compté sur CHACUN des
    # tronçons qu'il intersecte. La plante existe physiquement sur les deux et
    # les deux gestionnaires sont concernés. L'alternative — arbitrer un
    # tronçon unique — attribuerait arbitrairement la charge à l'un des deux.
    #
    # Ce comportement est celui de MS3, N1, N2, P1, P3, P4 et de la
    # caractérisation des populations : MS1 et MS2 étaient les deux exceptions.
    #
    # Pourquoi éclater ICI et pas sur gdf_EEE en début de fonction :
    # gdf_EEE est un GeoDataFrame, dont .explode() vise la GÉOMÉTRIE et non
    # une colonne. En travaillant sur l'extraction à deux colonnes ci-dessous,
    # qui est un DataFrame pandas ordinaire, il n'y a aucune ambiguïté.
    #
    # Effet à connaître : un point de bordure porte le risque maximal sur les
    # deux tronçons. C'est voulu.

    risque_par_point = gdf_EEE_enrichi[['nom_plo_fi', 'risque_sanitaire']].copy()
    # "A, B" -> ["A", " B"], puis une ligne par élément de la liste
    risque_par_point['nom_plo_fi'] = (
        risque_par_point['nom_plo_fi'].astype(str).str.split(',')
    )
    risque_par_point = risque_par_point.explode('nom_plo_fi')
    # .strip() enlève l'espace laissé après la virgule par le split
    risque_par_point['nom_plo_fi'] = risque_par_point['nom_plo_fi'].str.strip()

    risque_sanitaire_eee_par_troncons = (
        risque_par_point
        .dropna(subset=['risque_sanitaire'])
        .assign(risque_sanitaire_rank=lambda x: x['risque_sanitaire'].map(ordre_risque_sanitaire))
        .sort_values('risque_sanitaire_rank', ascending=False)
        .groupby('nom_plo_fi')
        .first()
        .reset_index()
        [['nom_plo_fi', 'risque_sanitaire']]
    )

    
    #____________________________________________________________
    #ETAPE 6 : jointure dans df_scoring
    # on rattache les riques sanitiares max par troncon à df_scoring
    #les troncons sans aucune EEE auront risque_sanitaire = NaN -> 'aucune'
    #____________________________________________________________

    #jointure avec df_scoring
    df_scoring = df_scoring.merge(
        risque_sanitaire_eee_par_troncons,
        on='nom_plo_fi',
        how='left'
    )

    #les troncons sans EEE ont hauteur_EEE = NaN
    df_scoring['risque_sanitaire'] = df_scoring['risque_sanitaire'].fillna('aucune')

    #____________________________________________________________
    #ETAPE 7 : scring MS2_impact
    #croisement entre MS2_vulnerabilite (oui/non) et risque_sanitaire (fort, modéré, faible, nul) pour attribuer score de 0 à 5
    # tableau de décision : voir en commentaire au début de la cellule
    #____________________________________________________________

    # Scoring MS2 imapct
    def attribuer_points_MS2(row):
        vuln = row['MS2_vulnerabilite']
        risque_sanitaire= row['risque_sanitaire']
        if vuln == 'oui':
            if risque_sanitaire == 'fort':    return 5
            if risque_sanitaire == 'modéré':  return 4
            if risque_sanitaire == 'faible':    return 3
            if risque_sanitaire == 'nul' : return 1
            return 3
        else:  # 'non'
            if risque_sanitaire == 'fort':    return 3
            if risque_sanitaire == 'modéré':  return 2
            if risque_sanitaire == 'faible':    return 1
            return 0   # risque nul ou absence EEE

    df_scoring.loc[:, 'MS2_impact'] = df_scoring.apply(attribuer_points_MS2, axis=1)

    #____________________________________________________________
    # Nettoyage : supprimer la colonne temporaire hauteur_EEE de df_scoring
    # la colonne est temporaire pour le calcul intermédiaire, on supprime pour une sortie propre
    #____________________________________________________________

    df_scoring.drop(columns=['risque_sanitaire'], inplace=True)

    #____________________________________________________________
    # ETAPE 9 : statistiques de controle
    #____________________________________________________________

    # ── Statistiques ─────────────────────────────────────────────────────────
    # nunique() sur la colonne BRUTE compterait la clé littérale "A, B" comme
    # un tronçon à part entière, en plus de A et de B. On compte donc sur la
    # version éclatée, qui reflète les tronçons réellement concernés.
    nb_troncons_eee = risque_par_point['nom_plo_fi'].nunique()
    nb_score_max    = (df_scoring['MS2_impact'] == 5).sum()

    print(f"\nRésultats :")
    print(f"  Tronçons avec EEE : {nb_troncons_eee}")
    print(f"  Tronçons score max (5) : {nb_score_max}")
    print(f"  Distribution des scores :\n{df_scoring['MS2_impact'].value_counts().sort_index()}")
    print(f"\n{'='*70}\n")

    return df_scoring
