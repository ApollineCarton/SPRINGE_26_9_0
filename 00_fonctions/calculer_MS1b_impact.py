# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_MS1b_impact"
Date : 2026-02-17 | Mise à jour : 2026-09-28 (seuil TMJA commun, mode Q3)
Objectif : calcul de MS1b pour point bonus
═══════════════════════════════════════════════════════════════════

Bonus MS1b : zone de visibilité critique + fort trafic

Logique :
- MS1_vulnerabilite = 'oui' ET TMJA du tronçon > seuil_trafic → +1
- Jointure spatiale entre tronçons et gdf_tmja (lignes de trafic)
- Si plusieurs sections TMJA touchent un tronçon, on retient la valeur MAX
  (le tronçon est exposé au trafic le plus fort qui le traverse)
- Si pas de TMJA ou valeur non numérique pour un tronçon : pas de bonus

MODIFICATION 2026-09-28 :
- Le seuil n'est plus une valeur fixe écrite en dur dans le lanceur
  (22 650 véh/j). Il est désormais calculé UNE SEULE FOIS par
  calculer_seuil_tmja.calculer_seuil_tmja_q3 (troisième quartile des
  valeurs TMJA de la zone), puis transmis ici ET à P2 : les deux
  indicateurs partagent donc strictement le même « fort trafic ».
- seuil_trafic n'a plus de valeur par défaut : l'appelant DOIT le fournir.
  Une valeur par défaut silencieuse (l'ancienne était 1 000) réintroduirait
  le risque de deux seuils différents entre MS1b et P2.
- Nouveau paramètre col_tmja : nom de la colonne de trafic, détecté par le
  même module. Avant, MS1b exigeait une colonne nommée exactement 'tmja',
  alors que P2 acceptait 'TMJA', 'trafic'... : les deux lisent maintenant
  la même colonne.
"""
import pandas as pd
import geopandas as gpd


def calculer_MS1b_impact(gdf_troncons, gdf_tmja, df_scoring, seuil_trafic, col_tmja='tmja'):
    """
    Paramètres :
        gdf_troncons : GeoDataFrame des tronçons (colonnes 'nom_plo_fi', 'geometry')
        gdf_tmja     : GeoDataFrame TMJA (lignes de trafic)
        df_scoring   : DataFrame de scoring, doit déjà contenir MS1_vulnerabilite
        seuil_trafic : seuil de fort trafic en véh/j (Q3 de la zone, calculé
                       par calculer_seuil_tmja) — OBLIGATOIRE
        col_tmja     : nom de la colonne de trafic dans gdf_tmja
                       (détecté par calculer_seuil_tmja ; 'tmja' par défaut)

    Sortie :
        df_scoring enrichi de la colonne 'MS1b_impact' (0 ou 1)
    """

    print(f"\n{'='*70}")
    print("CALCUL MS1b_IMPACT - BONUS TRAFIC")
    print(f"{'='*70}\n")

    # ── Vérifications d'entrée ─────────────────────────────────────────
    # MS1b est un sous-indicateur de MS1 : il réutilise la vulnérabilité
    # calculée par MS1. Sans elle, le calcul n'a pas de sens.
    if 'MS1_vulnerabilite' not in df_scoring.columns:
        raise ValueError("❌ MS1_vulnerabilite n'existe pas. Calculer MS1 d'abord.")

    # La colonne de trafic doit exister sous le nom transmis par le lanceur.
    if col_tmja not in gdf_tmja.columns:
        raise ValueError(f"❌ Colonne '{col_tmja}' introuvable dans gdf_tmja")

    print(f"📊 Jointure spatiale avec données TMJA...")
    print(f"   • Nombre de tronçons      : {len(gdf_troncons)}")
    print(f"   • Nombre de lignes TMJA   : {len(gdf_tmja)}")
    print(f"   • Colonne TMJA utilisée   : '{col_tmja}'")
    # :.0f → affichage sans décimale (le Q3 peut être un nombre à virgule)
    print(f"   • Seuil fort trafic (Q3)  : {seuil_trafic:.0f} véh/j\n")

    # ========================================================================
    # NETTOYAGE : convertir la colonne de trafic en numérique
    # ========================================================================
    # On travaille sur une copie pour ne jamais modifier la couche d'origine,
    # qui est aussi utilisée par P2.
    gdf_tmja_clean = gdf_tmja.copy()

    # errors='coerce' : toute valeur non numérique ('NA', 'ND', '') devient
    # NaN au lieu de faire planter la conversion.
    gdf_tmja_clean['tmja_numeric'] = pd.to_numeric(
        gdf_tmja_clean[col_tmja],
        errors='coerce'
    )

    # On liste les valeurs problématiques pour que l'utilisateur les voie :
    # ce sont celles devenues NaN alors qu'elles n'étaient pas vides.
    valeurs_non_numeriques = gdf_tmja_clean[
        gdf_tmja_clean['tmja_numeric'].isna() &
        gdf_tmja_clean[col_tmja].notna()
    ][col_tmja].unique()

    if len(valeurs_non_numeriques) > 0:
        print(f"⚠️  Valeurs non-numériques détectées dans '{col_tmja}' :")
        print(f"   {valeurs_non_numeriques}")
        print(f"   → Converties en NaN\n")

    # ========================================================================
    # JOINTURE SPATIALE
    # ========================================================================
    # how='left' : on garde TOUS les tronçons, même ceux qu'aucune section
    # TMJA ne croise (ils auront NaN, donc pas de bonus).
    # predicate='intersects' : une section TMJA est rattachée à un tronçon
    # dès que leurs géométries se touchent ou se chevauchent.
    jointure = gpd.sjoin(
        gdf_troncons[['nom_plo_fi', 'geometry']],
        gdf_tmja_clean[['tmja_numeric', 'geometry']],
        how='left',
        predicate='intersects'
    )

    # Si plusieurs sections TMJA touchent un même tronçon, on retient le MAX.
    # C'est cohérent avec P2, qui attribue son bonus dès qu'UNE section au
    # moins dépasse le seuil : « max > seuil » équivaut à « au moins une
    # section > seuil ». Les deux indicateurs jugent donc le trafic de la
    # même manière.
    trafic_max_par_troncon = (
        jointure
        .groupby('nom_plo_fi')['tmja_numeric']
        .max()  # max() ignore automatiquement les NaN
        .reset_index()
    )

    # Dictionnaire nom_plo_fi → trafic max, pour un report rapide par .map()
    dict_trafic = dict(zip(
        trafic_max_par_troncon['nom_plo_fi'],
        trafic_max_par_troncon['tmja_numeric']
    ))

    # Colonne temporaire (supprimée en fin de fonction)
    df_scoring['_trafic_temp'] = df_scoring['nom_plo_fi'].map(dict_trafic)

    # Par défaut : pas de bonus
    df_scoring['MS1b_impact'] = 0

    # Condition du bonus : tronçon vulnérable MS1, trafic connu, et trafic
    # STRICTEMENT supérieur au seuil (même règle que P2).
    condition = (
        (df_scoring['MS1_vulnerabilite'] == 'oui') &
        (df_scoring['_trafic_temp'].notna()) &
        (df_scoring['_trafic_temp'] > seuil_trafic)
    )

    df_scoring.loc[condition, 'MS1b_impact'] = 1

    # ========================================================================
    # STATISTIQUES
    # ========================================================================
    nb_vulnerables = (df_scoring['MS1_vulnerabilite'] == 'oui').sum()
    nb_avec_tmja = df_scoring['_trafic_temp'].notna().sum()
    nb_sans_tmja = df_scoring['_trafic_temp'].isna().sum()
    # Tronçons au-dessus du seuil, vulnérables ou non (pour info)
    nb_fort_trafic = (df_scoring['_trafic_temp'] > seuil_trafic).sum()
    nb_bonus = (df_scoring['MS1b_impact'] == 1).sum()

    if nb_avec_tmja > 0:
        print(f"📈 Distribution du trafic (tronçons avec TMJA) :")
        print(f"   • Min : {df_scoring['_trafic_temp'].min():.0f} véh/j")
        print(f"   • Médiane : {df_scoring['_trafic_temp'].median():.0f} véh/j")
        print(f"   • Max : {df_scoring['_trafic_temp'].max():.0f} véh/j\n")

    print(f"📊 Résultats :")
    print(f"   • Tronçons vulnérables MS1           : {nb_vulnerables}")
    print(f"   • Tronçons avec TMJA détecté         : {nb_avec_tmja}")
    print(f"   • Tronçons sans TMJA (NA)            : {nb_sans_tmja}")
    print(f"   • Tronçons au-dessus de {seuil_trafic:.0f} véh/j : {nb_fort_trafic}")
    print(f"   • ✅ Bonus MS1b attribués (vulnérables ET fort trafic) : {nb_bonus}")

    # Nettoyage de la colonne temporaire
    df_scoring.drop('_trafic_temp', axis=1, inplace=True)

    print(f"\n{'='*70}\n")

    return df_scoring
