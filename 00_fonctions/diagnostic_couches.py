# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Module "diagnostic_couches"
Objectif : vérifier, sans rien modifier au pipeline SPRINGE :
    (1) que les couches attendues par DATA existent bien en mémoire ;
    (2) qu'elles ne sont pas vides (0 entité = symptôme de bbox mal posée) ;
    (3) que les couches issues des API sont bien restreintes à l'emprise.
═══════════════════════════════════════════════════════════════════

Ce module est PUREMENT DESCRIPTIF : il lit, il compare, il affiche.
Il ne charge rien, ne reprojette rien, ne corrige rien. On peut donc
l'appeler à plusieurs endroits du script sans risque d'effet de bord.

Il contient aussi `charger_couche()`, la version corrigée du chargement
d'une couche locale filtrée par l'emprise (voir le commentaire détaillé
dans la fonction : c'est là que se situait le bug de bbox).
"""

import geopandas as gpd


# ═══════════════════════════════════════════════════════════════════
# 0. RETIRER DE DATA LES COUCHES ABSENTES
# ═══════════════════════════════════════════════════════════════════

def nettoyer_data(DATA, warnings_liste=None):
    """
    Retire de DATA toutes les entrées dont le GeoDataFrame est absent.

    ─────────────────────────────────────────────────────────────────
    POURQUOI
    ─────────────────────────────────────────────────────────────────
    detecter_elements_sur_troncon() lève un ValueError dès qu'une couche
    du dictionnaire n'est pas un GeoDataFrame :

        if not isinstance(gdf_elements, gpd.GeoDataFrame):
            raise ValueError(f"La couche '{nom_colonne}' n'est pas ...")

    Or l'utilisateur peut légitimement ne pas disposer d'une couche
    (une DIR qui ne suit pas ses murs, par exemple). Dans ce cas, le
    calcul doit se poursuivre SANS cet élément, pas s'arrêter.

    Comme les fonctions consommatrices itèrent sur dict_couches.items()
    et dict_couches.keys(), retirer une clé revient exactement à « cet
    élément n'est pas pris en compte » — ce qui est le comportement
    voulu. On nettoie donc DATA une fois pour toutes, juste après sa
    construction, plutôt que de modifier chaque indicateur.
    ─────────────────────────────────────────────────────────────────

    Paramètres
    ----------
    DATA : dict
        Le catalogue {enjeu: {indicateur: {nom_couche: {"gdf": ...}}}}.
    warnings_liste : list ou None
        Si fournie, chaque retrait y est tracé (_WARNINGS_SPRINGE),
        pour apparaître dans le rapport d'exécution.

    Retour
    ------
    dict : le DATA nettoyé (nouveau dictionnaire, l'original est intact).
    """

    data_propre = {}
    retirees = []

    for enjeu, indicateurs in DATA.items():
        data_propre[enjeu] = {}

        for indicateur, couches in indicateurs.items():

            # Certains niveaux peuvent ne pas être des dicts de couches
            # (structures imbriquées comme P2 : Hydrochorie / Anthropochorie).
            # On les recopie tels quels sans chercher à les nettoyer.
            if not isinstance(couches, dict):
                data_propre[enjeu][indicateur] = couches
                continue

            couches_propres = {}
            for nom_couche, spec in couches.items():

                # Une entrée valide est un dict contenant une clé "gdf".
                # Tout le reste est recopié sans jugement.
                if not isinstance(spec, dict) or "gdf" not in spec:
                    couches_propres[nom_couche] = spec
                    continue

                gdf = spec["gdf"]

                # C'est ici qu'on écarte les couches non fournies.
                if not isinstance(gdf, gpd.GeoDataFrame):
                    retirees.append(f"{enjeu}/{indicateur}/{nom_couche}")
                    continue

                couches_propres[nom_couche] = spec

            data_propre[enjeu][indicateur] = couches_propres

    # Trace explicite : l'utilisateur doit savoir ce qui n'a PAS été
    # pris en compte dans son scoring. Le silence serait pire que l'absence.
    if retirees:
        print(f"\n⚠️  {len(retirees)} couche(s) absente(s), retirée(s) du calcul :")
        for r in retirees:
            print(f"     – {r}")
        print("   Les indicateurs concernés seront calculés sans ces éléments.\n")
        if warnings_liste is not None:
            warnings_liste.append(
                f"Couches absentes non prises en compte : {', '.join(retirees)}"
            )
    else:
        print("\n✔️  Toutes les couches de DATA sont disponibles.\n")

    return data_propre


def indicateur_calculable(DATA, enjeu, indicateur, warnings_liste=None):
    """
    Dit si un indicateur dispose encore d'au moins une couche après nettoyage.

    ─────────────────────────────────────────────────────────────────
    POURQUOI
    ─────────────────────────────────────────────────────────────────
    nettoyer_data() retire les couches absentes. Si l'utilisateur n'a
    fourni AUCUNE des couches d'un indicateur, le dictionnaire de cet
    indicateur devient vide.

    Or detecter_elements_sur_troncon() itère sur ce dictionnaire : avec
    un dict vide, il ne crée aucune colonne, puis
    calculer_vulnerabilite_facon1() cherche des colonnes inexistantes
    → KeyError, ou pire, un score calculé sur du vide.

    On vérifie donc AVANT de lancer le calcul, et on saute proprement
    l'indicateur en le traçant dans le rapport.
    ─────────────────────────────────────────────────────────────────

    Retour
    ------
    bool : True si au moins une couche est disponible.
    """
    couches = DATA.get(enjeu, {}).get(indicateur, {})

    # Les indicateurs à structure imbriquée (N1, P3 : niveaux de
    # protection) contiennent des sous-dictionnaires. On descend d'un
    # cran pour compter les couches réellement présentes.
    if couches and all(
        isinstance(v, dict) and "gdf" not in v for v in couches.values()
    ):
        nb = sum(len(sous) for sous in couches.values()
                 if isinstance(sous, dict))
    else:
        nb = len(couches)

    if nb == 0:
        message = (f"Indicateur {indicateur} non calculé : "
                   f"aucune des couches nécessaires n'a été fournie")
        print(f"⚠️  {message}")
        if warnings_liste is not None:
            warnings_liste.append(message)
        return False

    return True


# ═══════════════════════════════════════════════════════════════════
# 1. VÉRIFIER QUE LES VARIABLES ATTENDUES EXISTENT ET SONT REMPLIES
# ═══════════════════════════════════════════════════════════════════

def diagnostic_variables(noms_attendus, espace_noms, titre="DIAGNOSTIC DES COUCHES"):
    """
    Compare la liste des noms de variables attendus (ceux qu'appelle get_gdf)
    avec ce qui existe réellement dans l'espace de noms du script.

    Paramètres
    ----------
    noms_attendus : list[str]
        Les noms de variables que DATA va réclamer, ex. ["gdf_carrefours", ...].
    espace_noms : dict
        Le dictionnaire des variables globales du script appelant.
        On l'appelle simplement avec globals() depuis le script principal.
        On passe `globals()` en argument plutôt que de l'appeler ici, car
        `globals()` retournerait l'espace de noms DE CE MODULE, pas celui
        du script — piège classique en Python.
    titre : str
        Titre affiché en tête du rapport console.

    Retour
    ------
    dict avec trois listes : "absentes", "vides", "ok"
        Permet au script appelant de décider d'un arrêt (fail-fast)
        plutôt que de crasher 13 minutes plus tard dans un indicateur.
    """

    absentes = []   # la variable n'existe pas du tout → get_gdf renverra None
    vides = []      # la variable existe mais contient 0 entité → indicateur silencieusement faux
    ok = []         # tout va bien

    print("\n" + "=" * 72)
    print(f" {titre}")
    print("=" * 72)

    for nom in noms_attendus:
        # .get() renvoie None si la clé n'existe pas, au lieu de lever KeyError
        objet = espace_noms.get(nom)

        # Cas 1 : la variable n'a jamais été créée (ou vaut explicitement None)
        if objet is None:
            absentes.append(nom)
            print(f"  ❌ {nom:45s} ABSENTE (None)")
            continue

        # Cas 2 : la variable existe mais n'est pas un GeoDataFrame
        # (typiquement une erreur de type en amont)
        if not isinstance(objet, gpd.GeoDataFrame):
            absentes.append(nom)
            print(f"  ❌ {nom:45s} TYPE INVALIDE ({type(objet).__name__})")
            continue

        # Cas 3 : GeoDataFrame valide mais vide → LE symptôme d'une bbox
        # exprimée dans un CRS différent de celui du fichier source.
        # Le code "tourne" sans erreur, mais l'indicateur ne trouve rien.
        if len(objet) == 0:
            vides.append(nom)
            print(f"  ⚠️  {nom:45s} VIDE (0 entité) — bbox suspecte ?")
            continue

        # Cas 4 : tout est correct
        # .crs.to_epsg() peut renvoyer None si le CRS n'est pas un code EPSG standard
        code_epsg = objet.crs.to_epsg() if objet.crs else "aucun CRS"
        ok.append(nom)
        print(f"  ✔️  {nom:45s} {len(objet):>7d} entités | EPSG:{code_epsg}")

    # Synthèse chiffrée en fin de rapport
    print("-" * 72)
    print(f"  OK : {len(ok)}   |   Vides : {len(vides)}   |   Absentes : {len(absentes)}")
    print("=" * 72 + "\n")

    return {"absentes": absentes, "vides": vides, "ok": ok}


# ═══════════════════════════════════════════════════════════════════
# 2. VÉRIFIER QUE LES COUCHES SONT BIEN RESTREINTES À L'EMPRISE
# ═══════════════════════════════════════════════════════════════════

def diagnostic_emprise(noms_couches, espace_noms, emprise, seuil_alerte=3.0):
    """
    Compare l'étendue (bounding box) de chaque couche à celle de l'emprise.

    Principe : si une couche a été correctement filtrée côté serveur (ou côté
    fichier), son étendue ne peut pas dépasser significativement celle de
    l'emprise. Si elle la dépasse d'un facteur important, c'est que le filtre
    spatial n'a PAS fonctionné et qu'on a téléchargé bien plus que la zone
    d'étude (au pire : toute la France).

    C'est la façon empirique de répondre à « est-ce que mes API ne chargent
    que l'emprise ? » — on ne fait pas confiance à l'URL, on mesure le résultat.

    Paramètres
    ----------
    noms_couches : list[str]
        Noms des variables de couches à contrôler.
    espace_noms : dict
        globals() du script appelant (voir remarque dans diagnostic_variables).
    emprise : GeoDataFrame
        L'emprise de travail, tampon déjà appliqué, en Lambert 93.
    seuil_alerte : float
        Facteur au-delà duquel on alerte. 3.0 = l'étendue de la couche fait
        plus de 3× la surface de l'étendue de l'emprise.

    Retour
    ------
    list[str] : noms des couches jugées "hors emprise" (filtre inopérant).
    """

    # total_bounds renvoie un array numpy [minx, miny, maxx, maxy]
    e_minx, e_miny, e_maxx, e_maxy = emprise.total_bounds

    # Surface du rectangle englobant l'emprise, en m² (on est en Lambert 93)
    aire_emprise = (e_maxx - e_minx) * (e_maxy - e_miny)

    print("\n" + "=" * 72)
    print(" DIAGNOSTIC — RESPECT DE L'EMPRISE")
    print("=" * 72)
    print(f"  Emprise (Lambert 93) : X [{e_minx:.0f} ; {e_maxx:.0f}]  "
          f"Y [{e_miny:.0f} ; {e_maxy:.0f}]")
    print(f"  Étendue emprise      : {(e_maxx - e_minx)/1000:.1f} km x "
          f"{(e_maxy - e_miny)/1000:.1f} km")
    print("-" * 72)

    hors_emprise = []

    for nom in noms_couches:
        gdf = espace_noms.get(nom)

        # On ignore silencieusement ce qui n'est pas exploitable :
        # diagnostic_variables() a déjà signalé ces cas.
        if gdf is None or not isinstance(gdf, gpd.GeoDataFrame) or len(gdf) == 0:
            continue

        # On ramène tout en Lambert 93 pour comparer des choses comparables.
        # .to_crs() ne modifie pas l'original : il renvoie une copie.
        gdf_l93 = gdf.to_crs(epsg=2154) if gdf.crs and gdf.crs.to_epsg() != 2154 else gdf

        c_minx, c_miny, c_maxx, c_maxy = gdf_l93.total_bounds
        aire_couche = (c_maxx - c_minx) * (c_maxy - c_miny)

        # Ratio des surfaces des rectangles englobants.
        # ~1 (ou moins) = couche bien contenue dans l'emprise.
        # >> 1          = la couche s'étend bien au-delà → filtre inopérant.
        ratio = aire_couche / aire_emprise if aire_emprise > 0 else float("inf")

        if ratio > seuil_alerte:
            hors_emprise.append(nom)
            statut = "❌ HORS EMPRISE"
        else:
            statut = "✔️  dans l'emprise"

        print(f"  {statut}  {nom:42s} ratio={ratio:6.1f}  "
              f"({(c_maxx - c_minx)/1000:.0f} x {(c_maxy - c_miny)/1000:.0f} km)")

    print("-" * 72)
    if hors_emprise:
        print(f"  ⚠️  {len(hors_emprise)} couche(s) dépassent l'emprise : "
              f"le filtre spatial n'a pas fonctionné pour celles-ci.")
    else:
        print("  ✔️  Toutes les couches contrôlées sont contenues dans l'emprise.")
    print("=" * 72 + "\n")

    return hors_emprise


# ═══════════════════════════════════════════════════════════════════
# 3. CHARGEMENT CORRIGÉ D'UNE COUCHE LOCALE FILTRÉE PAR L'EMPRISE
# ═══════════════════════════════════════════════════════════════════

def charger_couche(chemin, emprise, nom_couche, warnings_liste=None):
    """
    Charge une couche SIG locale en la filtrant par l'emprise, avec gestion
    correcte des CRS.

    ─────────────────────────────────────────────────────────────────
    LE BUG QUE CETTE FONCTION CORRIGE
    ─────────────────────────────────────────────────────────────────
    Le code précédent faisait :

        gdf = gpd.read_file(chemin, bbox=(minx, miny, maxx, maxy))

    où (minx…maxy) sont des coordonnées Lambert 93, en mètres.

    Or, quand `bbox` est un TUPLE, geopandas/pyogrio suppose que ces
    coordonnées sont exprimées dans le CRS DU FICHIER LU — il ne fait
    aucune conversion. Si le fichier est en WGS84 (degrés), on lui
    demande alors de filtrer sur un rectangle situé vers X≈650000,
    Y≈6860000 degrés : une zone qui n'existe pas.

    Résultat : 0 entité retournée, AUCUNE exception levée.
    Le script tourne normalement, la couche est "chargée", mais vide —
    d'où des indicateurs silencieusement faux.

    LA CORRECTION : passer l'emprise comme GeoSeries/GeoDataFrame porteuse
    de son CRS. Dans ce cas, geopandas reprojette lui-même le filtre vers
    le CRS du fichier avant de l'appliquer. Vérifié en test :
        - bbox tuple L93 sur fichier 4326  → 0 entité
        - bbox GeoSeries L93 sur fichier 4326 → toutes les entités
    ─────────────────────────────────────────────────────────────────

    Paramètres
    ----------
    chemin : str ou Path
        Chemin du fichier SIG (.shp, .gpkg, .geojson…).
    emprise : GeoDataFrame
        Emprise de travail (tampon déjà appliqué), avec un CRS défini.
    nom_couche : str
        Nom lisible pour les messages console et les avertissements.
    warnings_liste : list ou None
        Si fournie, les avertissements y sont ajoutés (_WARNINGS_SPRINGE).

    Retour
    ------
    GeoDataFrame en Lambert 93, ou None si le chargement échoue.
    """

    # Si aucun chemin n'a été renseigné par l'utilisateur, on sort proprement.
    if not chemin:
        return None

    try:
        # On construit le filtre spatial comme une GeoSeries PORTEUSE DE SON CRS.
        # C'est ce qui permet à geopandas de reprojeter le filtre automatiquement.
        # .geometry récupère la colonne géométrique ; on garde le CRS de l'emprise.
        filtre = emprise.geometry

        gdf = gpd.read_file(chemin, bbox=filtre)

        # Reprojection en Lambert 93 APRÈS le filtrage.
        # (l'ordre n'a plus d'importance ici puisque le filtre gère le CRS,
        #  mais on garde Lambert 93 comme CRS de travail unique du projet)
        if gdf.crs and gdf.crs.to_epsg() != 2154:
            gdf = gdf.to_crs(epsg=2154)

        # Alerte explicite si le filtrage renvoie un résultat vide :
        # ce n'est pas forcément un bug (la couche peut réellement ne rien
        # avoir dans la zone), mais l'utilisateur doit le savoir.
        if len(gdf) == 0:
            message = (f"{nom_couche} : 0 entité dans l'emprise — "
                       f"vérifier que la couche couvre bien la zone d'étude")
            print(f"⚠️  {message}")
            if warnings_liste is not None:
                warnings_liste.append(message)
        else:
            print(f"✔️  {nom_couche} chargé : {len(gdf)} entités")

        return gdf

    except Exception as e:
        # On n'interrompt pas le programme : on signale et on renvoie None.
        # C'est get_gdf() / le diagnostic qui décideront de la suite.
        message = f"{nom_couche} : chargement échoué — {str(e)[:100]}"
        print(f"⚠️  {message}")
        if warnings_liste is not None:
            warnings_liste.append(message)
        return None
