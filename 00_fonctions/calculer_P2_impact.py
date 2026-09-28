# -*- coding: utf-8 -*-
"""
Fonction "calculer_P2_impact"
Date : 2026-04 | Mise à jour : 2026-09-21
Auteur : Apolline CARTON — Office Français de la Biodiversité (OFB)

═══════════════════════════════════════════════════════════════════
INDICATEUR P2 : Proximité des vecteurs de dispersion des EEE
═══════════════════════════════════════════════════════════════════

QUESTION POSÉE :
    Le tronçon est-il situé à proximité de vecteurs favorisant
    la dispersion des EEE en présence ?

LOGIQUE GÉNÉRALE :
    La route est le vecteur de dispersion PRINCIPAL pour toutes les EEE
    (véhicules, engins de chantier, flux humains). Elle est présente par
    définition sur tous les tronçons du réseau DIR → elle n'est donc PAS
    discriminante entre les tronçons.

    P2 cherche donc à identifier les vecteurs AGGRAVANTS, c'est-à-dire
    les éléments supplémentaires qui augmentent encore le risque de
    dispersion au-delà du vecteur routier de base.

VECTEURS AGGRAVANTS RETENUS :
    1. Cours d'eau (hydrochorie) — BD TOPO / API IGN
    2. Carrefours + échangeurs (anthropochorie véhiculaire) — SI Route
    3. Voies ferrées (anthropochorie ferroviaire) — BD TOPO
    4. Fort trafic TMJA (anthropochorie à haute fréquence) — SI Route [OPTIONNEL]

CHOIX DE NE PAS SPÉCIALISER PAR ESPÈCE :
    Idéalement, on croiserait le vecteur aggravant détecté avec le mode
    de dispersion dominant de chaque EEE (colonne 'dispersal_dominant_vector'
    dans EEE_sheet : wind / water / animals / human / gravity).
    Ce croisement a été écarté pour deux raisons :
        a) Les données disponibles ne couvrent pas tous les modes
           (pas de données vent ni corridors zoochores à l'échelle DIR).
        b) La dispersion est rarement exclusive : une espèce
           "anthropochore" peut aussi se disperser par l'eau lors de crues.
    → L'indicateur est donc générique (non espèce-dépendant), ce qui
      simplifie le calcul sans trop sacrifier l'exactitude écologique.
    PERSPECTIVE D'AMÉLIORATION : intégrer la compatibilité vecteur/espèce
    dès que des données de corridors anémochores et zoochores seront
    disponibles à l'échelle du réseau DIR.

STRUCTURE DU SCORE (0 à 5) :
    Le score P2 est un score BONUS s'ajoutant à la présence d'EEE.
    Un tronçon sans EEE obtient forcément 0 (rien à disperser).

    Score = (présence EEE) + (vecteurs aggravants détectés)

    Détail des points :
        +0  → aucune EEE sur le tronçon
        +1  → EEE présente (score de base, vecteur routier seul)
        +2  → cours d'eau à proximité (hydrochorie, vecteur très efficace)
        +1  → carrefour OU échangeur OU voie ferrée à proximité (anthropochorie +)
        +1  → TMJA fort (quartile Q3) [OPTIONNEL — uniquement si données dispo]

    Score max théorique sans TMJA : 4
    Score max théorique avec TMJA : 5

PARAMÈTRES :
    - gdf_EEE         : GeoDataFrame des points de présence EEE
                        (doit contenir 'nom_plo_fi')
    - gdf_troncons    : GeoDataFrame des tronçons
                        (doit contenir 'nom_plo_fi' et 'geometry')
    - df_scoring      : DataFrame de scoring (une ligne par tronçon)
    - DATA_P2         : Dictionnaire DATA["P"]["P2"] structuré dans lancer_SPRINGE
    - gdf_tmja        : GeoDataFrame TMJA [OPTIONNEL, None par défaut]
    - seuil_tmja      : seuil de fort trafic (Q3 des TMJA de la zone), calculé
                        une seule fois par calculer_seuil_tmja et partagé avec MS1b
    - col_tmja        : nom de la colonne de trafic (même détection que MS1b)
    - tampon_cours_eau: int, distance tampon en mètres autour des tronçons
                        pour détecter les cours d'eau [défaut : 50]

SORTIE :
    - df_scoring enrichi d'une colonne 'P2_impact' (entier, 0 à 5)

MODIFICATIONS SEPT 2026 :
    ✅ Seuil TMJA adaptatif (Q3 = 75e percentile) au lieu de fixe 10000
    ✅ (2026-09-28) Seuil calculé une seule fois dans calculer_seuil_tmja et
       partagé avec MS1b : un seul « fort trafic » pour tout SPRINGE
    → S'adapte à la distribution réelle du réseau (DIR rurale vs périurbaine)
    → DIR rurale (max 8K) : Q3 = 6000 → bonus donné, pas 0
    → DIR périurbaine (max 30K) : Q3 = 22000 → bonus non redondant

═══════════════════════════════════════════════════════════════════
"""

import pandas as pd
import geopandas as gpd


def calculer_P2_impact(
    gdf_EEE,
    gdf_troncons,
    df_scoring,
    DATA_P2,
    gdf_tmja=None,
    seuil_tmja=None,   # seuil fort trafic (Q3 de la zone), calculé par calculer_seuil_tmja
    col_tmja=None,     # colonne de trafic, détectée par calculer_seuil_tmja
    tampon_cours_eau=50
):
    """
    Calcule l'indicateur P2 (proximité des vecteurs de dispersion).
    
    Paramètres:
    -----------
    gdf_EEE : GeoDataFrame
        Points de présence EEE avec colonne 'nom_plo_fi'
    gdf_troncons : GeoDataFrame
        Tronçons routiers avec 'nom_plo_fi' et 'geometry'
    df_scoring : DataFrame
        Table de scoring (une ligne par tronçon)
    DATA_P2 : dict
        Dictionnaire structuré contenant les couches SIG (cours_eau, carrefours, etc.)
        Structure attendue : DATA_P2 = {
            'cours_eau': gdf_cours_eau,
            'carrefours': gdf_carrefours,
            'echangeurs': gdf_echangeurs,
            'voies_ferrees': gdf_voies_ferrees
        }
    gdf_tmja : GeoDataFrame, optional
        Entités TMJA avec colonne de valeurs de trafic
    seuil_tmja : float, optional
        Seuil de fort trafic en véh/j = Q3 des valeurs TMJA de la zone,
        calculé UNE fois par calculer_seuil_tmja et partagé avec MS1b.
        Si None alors que gdf_tmja est fourni, il est recalculé ici avec
        la même fonction (filet de sécurité).
    col_tmja : str, optional
        Nom de la colonne de trafic dans gdf_tmja (même règle de détection
        que MS1b). Si None, détecté par calculer_seuil_tmja.
    tampon_cours_eau : int
        Distance en mètres pour tampon autour tronçons
    
    Returns:
    --------
    DataFrame : df_scoring enrichi de la colonne 'P2_impact' (0-5)
    """
    
    # ════════════════════════════════════════════════════════════════════
    # SECTION 0 — EN-TÊTE ET VÉRIFICATIONS
    # ════════════════════════════════════════════════════════════════════

    print(f"\n{'='*70}")
    print("CALCUL P2_IMPACT — Vecteurs de dispersion des EEE")
    print(f"{'='*70}\n")

    # ── Vérification des colonnes obligatoires ───────────────────────────
    # On s'assure que les colonnes indispensables existent avant de commencer
    # pour éviter des erreurs cryptiques au milieu du calcul.
    for col in ['nom_plo_fi']:
        if col not in gdf_EEE.columns:
            raise ValueError(f"❌ Colonne '{col}' introuvable dans gdf_EEE")
        if col not in gdf_troncons.columns:
            raise ValueError(f"❌ Colonne '{col}' introuvable dans gdf_troncons")
        if col not in df_scoring.columns:
            raise ValueError(f"❌ Colonne '{col}' introuvable dans df_scoring")

    if 'geometry' not in gdf_troncons.columns:
        raise ValueError("❌ Colonne 'geometry' introuvable dans gdf_troncons")

    print(f"📋 Paramètres de calcul :")
    print(f"   • Tronçons à analyser : {len(df_scoring)}")
    print(f"   • Points EEE          : {len(gdf_EEE)}")
    print(f"   • Tampon cours d'eau  : {tampon_cours_eau} m")
    print(f"   • TMJA disponible     : {'oui' if gdf_tmja is not None else 'non'}")
    if gdf_tmja is None:
        print(f"   • Seuil TMJA          : non applicable (pas de données TMJA)")
    elif seuil_tmja is not None:
        print(f"   • Seuil TMJA          : {seuil_tmja:.0f} véh/j (Q3 de la zone, commun avec MS1b)")
    else:
        print(f"   • Seuil TMJA          : Q3 de la zone, calculé à l'étape 3.3")

    # ════════════════════════════════════════════════════════════════════
    # SECTION 1 — IDENTIFICATION DES TRONÇONS AVEC EEE
    # ════════════════════════════════════════════════════════════════════
    # Un tronçon sans EEE obtient 0 directement (rien à disperser).
    # On identifie ici la liste des tronçons "actifs" pour P2.

    print(f"\n{'─'*60}")
    print("ÉTAPE 1 — Tronçons avec EEE présente")
    print(f"{'─'*60}")

    # ── Éclatement des points à cheval sur plusieurs tronçons ────────────
    # Certains points EEE peuvent être situés à la bordure entre deux
    # tronçons. Dans ce cas, join_num_troncon_a_gdf_EEE écrit "A, B" dans
    # la colonne nom_plo_fi. On explose cette colonne pour traiter
    # correctement ces cas (un point compte pour les deux tronçons).
    gdf_EEE_explode = gdf_EEE.copy()
    gdf_EEE_explode = gdf_EEE_explode.assign(
        nom_plo_fi=gdf_EEE_explode['nom_plo_fi'].str.split(',')
    ).explode('nom_plo_fi')
    # Nettoyer les espaces éventuels laissés par le split ("A, B" → ["A", " B"] → ["A", "B"])
    gdf_EEE_explode['nom_plo_fi'] = gdf_EEE_explode['nom_plo_fi'].str.strip()

    # Liste unique des tronçons qui ont au moins 1 point EEE
    troncons_avec_eee = gdf_EEE_explode['nom_plo_fi'].unique()

    print(f"   • Tronçons avec EEE : {len(troncons_avec_eee)}")
    print(f"   • Tronçons sans EEE : {len(df_scoring) - len(troncons_avec_eee)}")

    # ════════════════════════════════════════════════════════════════════
    # SECTION 2 — INITIALISATION DU SCORE
    # ════════════════════════════════════════════════════════════════════
    # On initialise tout à 0, puis on ajoute les points bonus au fur et
    # à mesure des détections. C'est le principe de scoring additif.

    df_scoring['P2_impact'] = 0

    # ── Point de base : EEE présente (+1) ───────────────────────────────
    # Ce +1 représente le risque minimal : la route seule suffit à disperser
    # les EEE, donc tout tronçon colonisé a déjà un risque non nul.
    df_scoring.loc[
        df_scoring['nom_plo_fi'].isin(troncons_avec_eee),
        'P2_impact'
    ] += 1

    print(f"\n   → +1 (EEE présente) attribué à {(df_scoring['P2_impact'] == 1).sum()} tronçons")

    # ════════════════════════════════════════════════════════════════════
    # SECTION 3 — DÉTECTION DES VECTEURS AGGRAVANTS
    # ════════════════════════════════════════════════════════════════════
    # Pour chaque vecteur, on réalise une jointure spatiale (avec tampon si
    # nécessaire) pour savoir quels tronçons sont à proximité du vecteur.
    # Seuls les tronçons déjà avec EEE (+1) peuvent accumuler des bonus.

    # ── Travailler sur une copie géométrique des tronçons ────────────────
    # On extrait uniquement les colonnes utiles pour alléger les jointures.
    gdf_troncons_geo = gdf_troncons[['nom_plo_fi', 'geometry']].copy()

    # ──────────────────────────────────────────────────────────────────────
    # 3.1 — COURS D'EAU (hydrochorie, +2)
    # ──────────────────────────────────────────────────────────────────────
    # L'hydrochorie est le vecteur le plus efficace pour la dispersion
    # (graine/fragment transporté par l'eau). On donne +2 pour ce vecteur.

    print(f"\n{'─'*60}")
    print("ÉTAPE 3.1 — Cours d'eau à proximité (hydrochorie, +2)")
    print(f"{'─'*60}")

    gdf_cours_eau = DATA_P2.get('cours_eau', None)

    if gdf_cours_eau is None or len(gdf_cours_eau) == 0:
        print("   ⚠️  Cours d'eau absent ou vide → étape ignorée")
        troncons_cours_eau = set()
    else:
        # Créer un tampon autour des tronçons pour détecter les cours d'eau à proximité
        # (dans un rayon tampon_cours_eau mètres).
        # On utilise buffer() sur la géométrie, pas sur toute la GeoDataFrame.
        gdf_troncons_buffer = gdf_troncons_geo.copy()
        gdf_troncons_buffer['geometry'] = gdf_troncons_buffer['geometry'].buffer(tampon_cours_eau)

        try:
            # Jointure spatiale : quels tronçons (tampon) intersectent un cours d'eau ?
            jointure_eau = gpd.sjoin(
                gdf_troncons_buffer[['nom_plo_fi', 'geometry']],
                gdf_cours_eau[['geometry']],
                how='inner',
                predicate='intersects'
            )

            troncons_cours_eau = set(jointure_eau['nom_plo_fi'].unique())
            print(f"   • Cours d'eau : {len(gdf_cours_eau)} entités")
            print(f"   • Tronçons à proximité (< {tampon_cours_eau}m) : {len(troncons_cours_eau)}")

        except Exception as e:
            print(f"   ⚠️  Erreur jointure cours d'eau : {e} → ignoré")
            troncons_cours_eau = set()

    # Attribuer le +2 aux tronçons à proximité d'un cours d'eau ET qui ont des EEE
    masque_eau_avec_eee = (
        df_scoring['nom_plo_fi'].isin(troncons_cours_eau) &
        (df_scoring['P2_impact'] > 0)
    )
    df_scoring.loc[masque_eau_avec_eee, 'P2_impact'] += 2

    nb_bonus_eau = masque_eau_avec_eee.sum()
    print(f"   → +2 (hydrochorie) attribué à {nb_bonus_eau} tronçons avec EEE")

    # ──────────────────────────────────────────────────────────────────────
    # 3.2 — ANTHROPOCHORIE AGGRAVANTE : Carrefours, Échangeurs, Voies ferrées (+1)
    # ──────────────────────────────────────────────────────────────────────
    # Carrefours et échangeurs = points de concentration du trafic
    # → forte probabilité de transport d'EEE via véhicules.
    # Voies ferrées = corridor anthropique alternatif (engins, ballast, etc.)
    # On donne +1 si AU MOINS UN de ces trois éléments est touchant/intersectant.

    print(f"\n{'─'*60}")
    print("ÉTAPE 3.2 — Carrefours / Échangeurs / Voies ferrées (+1)")
    print(f"{'─'*60}")

    troncons_anthropochorie = set()

    # ── Sous-étape : parcourir chaque couche disponible ──────────────────
    couches_anthropo = {
        "carrefours"   : DATA_P2.get('carrefours', None),
        "échangeurs"   : DATA_P2.get('echangeurs', None),
        "voies ferrées": DATA_P2.get('voies_ferrees', None)
    }

    for nom_couche, gdf_couche in couches_anthropo.items():

        if gdf_couche is None or len(gdf_couche) == 0:
            print(f"   ⚠️  '{nom_couche}' absent ou vide → ignoré")
            continue

        try:
            # Jointure directe sans tampon (intersection stricte avec le tronçon).
            # C'est cohérent avec MS1 : carrefours et échangeurs sont des éléments
            # qui se trouvent physiquement sur ou au croisement du tronçon.
            # On ne buffere pas ici : on cherche une intersection réelle.
            jointure_anthropo = gpd.sjoin(
                gdf_troncons_geo[['nom_plo_fi', 'geometry']],
                gdf_couche[['geometry']],
                how='inner',
                predicate='intersects'
            )

            # Ajouter les tronçons touchés dans le set commun
            troncons_touches = set(jointure_anthropo['nom_plo_fi'].unique())
            nb_avant = len(troncons_anthropochorie)
            troncons_anthropochorie.update(troncons_touches)
            nb_nouveaux = len(troncons_anthropochorie) - nb_avant

            print(f"   • '{nom_couche}' : {len(gdf_couche)} entités → "
                  f"{len(troncons_touches)} tronçons touchés "
                  f"(dont {nb_nouveaux} nouveaux)")

        except Exception as e:
            print(f"   ⚠️  Erreur jointure '{nom_couche}' : {e} → ignoré")

    # Attribuer le +1 aux tronçons touchés par au moins un vecteur anthropochore
    # ET qui ont des EEE (P2 > 0)
    masque_anthropo_avec_eee = (
        df_scoring['nom_plo_fi'].isin(troncons_anthropochorie) &
        (df_scoring['P2_impact'] > 0)
    )
    df_scoring.loc[masque_anthropo_avec_eee, 'P2_impact'] += 1

    nb_bonus_anthropo = masque_anthropo_avec_eee.sum()
    print(f"\n   → Total tronçons avec ≥1 vecteur anthropochore aggravant : {len(troncons_anthropochorie)}")
    print(f"   → +1 (anthropochorie +) attribué à {nb_bonus_anthropo} tronçons avec EEE")

    # ──────────────────────────────────────────────────────────────────────
    # 3.3 — TMJA FORT : seuil commun Q3 (+1) [OPTIONNEL]
    # ──────────────────────────────────────────────────────────────────────
    # MODIFICATION 2026-09-28 : le seuil n'est PLUS calculé ici.
    # Il est calculé une seule fois par calculer_seuil_tmja.calculer_seuil_tmja_q3
    # (troisième quartile des valeurs TMJA de la zone) et transmis par le
    # lanceur à MS1b ET à P2. Motif : garantir que les deux indicateurs
    # utilisent strictement le même seuil de « fort trafic ».
    #
    # Rappel du principe du Q3 (détaillé dans calculer_seuil_tmja.py) :
    #   - un seuil fixe (ex. 10 000 véh/j) ne discrimine rien en DIR rurale
    #     (jamais atteint) ni en DIR périurbaine (presque toujours dépassé) ;
    #   - « TMJA > Q3 » désigne ~25 % des sections les plus chargées de la
    #     zone traitée, quel que soit le niveau général de trafic.
    #
    # Filet de sécurité : si P2 est appelé seul (sans seuil transmis) avec
    # une couche TMJA, on calcule le seuil ici avec LA MÊME fonction, pour
    # que le résultat reste identique à celui d'un appel via le lanceur.

    print(f"\n{'─'*60}")
    print("ÉTAPE 3.3 — TMJA fort (anthropochorie haute fréquence, +1) [OPTIONNEL]")
    print(f"{'─'*60}")

    if gdf_tmja is None:
        print("   ℹ️  TMJA non fourni → étape ignorée (score max = 4)")

    else:
        # ── Récupérer seuil et colonne ────────────────────────────────
        if seuil_tmja is None or col_tmja is None:
            # Import local : calculer_seuil_tmja est dans 00_fonctions/,
            # dossier ajouté à sys.path par le lanceur.
            import calculer_seuil_tmja
            infos_tmja = calculer_seuil_tmja.calculer_seuil_tmja_q3(gdf_tmja)
            if infos_tmja is not None:
                seuil_tmja = infos_tmja['seuil']
                col_tmja = infos_tmja['colonne']

        if seuil_tmja is None or col_tmja is None or col_tmja not in gdf_tmja.columns:
            # Seuil non calculable (pas de colonne de trafic, aucune valeur
            # numérique...) : le bonus n'est pas attribué, sans planter.
            print("   ⚠️  Seuil TMJA indisponible → étape ignorée (score max = 4)")
        else:
            print(f"   • Colonne TMJA utilisée : '{col_tmja}'")
            print(f"   • Seuil fort trafic (Q3 de la zone) : {seuil_tmja:.0f} véh/j")

            # ── Convertir TMJA en numérique ─────────────────────────────
            # errors='coerce' : les valeurs non numériques deviennent NaN.
            # Une comparaison NaN > seuil vaut False : ces sections ne sont
            # donc jamais retenues comme « fort trafic ».
            gdf_tmja = gdf_tmja.copy()
            gdf_tmja[col_tmja] = pd.to_numeric(gdf_tmja[col_tmja], errors='coerce')

            # ── Sélectionner les sections de fort trafic ──────────────
            # Règle : TMJA STRICTEMENT supérieur au seuil (même règle que MS1b).
            gdf_tmja_fort = gdf_tmja[gdf_tmja[col_tmja] > seuil_tmja].copy()

            nb_total = len(gdf_tmja)
            nb_fort = len(gdf_tmja_fort)
            pct_fort = (nb_fort / nb_total * 100) if nb_total > 0 else 0

            print(f"   • Entités TMJA total       : {nb_total}")
            print(f"   • Entités TMJA > {seuil_tmja:.0f}     : {nb_fort} ({pct_fort:.1f}% de la couche)")

            if len(gdf_tmja_fort) == 0:
                print("   ⚠️  Aucune entité TMJA forte → bonus non attribué")
            else:
                try:
                    # ── Jointure spatiale TMJA fort ↔ tronçons ──────────
                    # Quels tronçons intersectent au moins une section de
                    # fort trafic ?
                    jointure_tmja = gpd.sjoin(
                        gdf_troncons_geo[['nom_plo_fi', 'geometry']],
                        gdf_tmja_fort[['geometry']],
                        how='inner',
                        predicate='intersects'
                    )

                    troncons_tmja_fort = jointure_tmja['nom_plo_fi'].unique()

                    # ── Attribuer +1 uniquement si EEE présente ──────────
                    # Un tronçon sans EEE (P2 = 0) ne peut pas recevoir ce
                    # bonus : sans EEE, il n'y a rien à disperser.
                    masque_tmja_avec_eee = (
                        df_scoring['nom_plo_fi'].isin(troncons_tmja_fort) &
                        (df_scoring['P2_impact'] > 0)
                    )
                    df_scoring.loc[masque_tmja_avec_eee, 'P2_impact'] += 1

                    nb_bonus_tmja = masque_tmja_avec_eee.sum()
                    print(f"   • Tronçons à fort trafic : {len(troncons_tmja_fort)}")
                    print(f"   → +1 (TMJA fort) attribué à {nb_bonus_tmja} tronçons avec EEE")

                except Exception as e:
                    print(f"   ⚠️  Erreur jointure TMJA : {e} → étape ignorée")

    # ════════════════════════════════════════════════════════════════════
    # SECTION 4 — PLAFONNEMENT DU SCORE À 5
    # ════════════════════════════════════════════════════════════════════
    # Par construction le score max est 1+2+1+1 = 5, mais si une couche
    # est dupliquée ou qu'il y a un bug, on applique un clip de sécurité.
    # clip(lower=0, upper=5) : remplace tout score < 0 par 0 et > 5 par 5.
    df_scoring['P2_impact'] = df_scoring['P2_impact'].clip(lower=0, upper=5)

    # ════════════════════════════════════════════════════════════════════
    # SECTION 5 — STATISTIQUES FINALES
    # ════════════════════════════════════════════════════════════════════

    print(f"\n{'─'*60}")
    print("RÉSULTATS — Distribution du score P2_impact")
    print(f"{'─'*60}")

    # ── Distribution complète des scores ─────────────────────────────────
    # On compte combien de tronçons ont chaque score (0, 1, 2, 3, 4, 5)
    distribution = df_scoring['P2_impact'].value_counts().sort_index()
    total = len(df_scoring)

    # ── Légende pour faciliter la lecture ────────────────────────────────
    # Chaque score correspond à une combinaison de vecteurs détectés
    # CORRIGÉ 2026-09-28 : l'ancienne légende ne correspondait pas aux
    # points réellement attribués (+1 EEE, +2 eau, +1 anthropo, +1 TMJA).
    # Chaque score est la somme de ces bonus ; plusieurs combinaisons
    # peuvent donner le même total, d'où les « OU ».
    legende = {
        0: "Aucune EEE",
        1: "EEE seule (route uniquement)",
        2: "EEE + anthropochorie OU EEE + TMJA fort",
        3: "EEE + cours d'eau OU EEE + anthropochorie + TMJA fort",
        4: "EEE + cours d'eau + (anthropochorie OU TMJA fort)",
        5: "EEE + cours d'eau + anthropochorie + TMJA fort"
    }

    for score, nb in distribution.items():
        pct = round(nb / total * 100, 1)
        label = legende.get(score, f"score {score}")
        print(f"   Score {score} — {label} : {nb} tronçons ({pct}%)")

    print(f"\n   📈 Statistiques générales :")
    print(f"      Score moyen P2       : {df_scoring['P2_impact'].mean():.2f}")
    print(f"      Score max P2         : {df_scoring['P2_impact'].max()}")
    print(f"      Tronçons risque élevé (score ≥ 3) : "
          f"{(df_scoring['P2_impact'] >= 3).sum()} "
          f"({round((df_scoring['P2_impact'] >= 3).sum() / total * 100, 1)}%)")

    print(f"\n{'='*70}")
    print("✅ P2_impact calculé avec succès")
    print(f"{'='*70}\n")

    return df_scoring
