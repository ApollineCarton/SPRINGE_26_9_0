# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Module "charger_couches_sig"
Charge les couches SIG locales renseignées par l'utilisateur, en les
filtrant réellement sur l'emprise de travail.
═══════════════════════════════════════════════════════════════════════════

LE BUG CORRIGÉ ICI
─────────────────────────────────────────────────────────────────
L'ancien code faisait :

    gdf = gpd.read_file(chemin, bbox=(minx, miny, maxx, maxy))

où minx…maxy sont des coordonnées Lambert 93, en mètres.

Quand `bbox` est un TUPLE, geopandas/pyogrio suppose que ces coordonnées
sont déjà exprimées dans le CRS DU FICHIER LU — il ne fait aucune
conversion. Si le fichier est en WGS84 (degrés), on lui demande alors de
filtrer sur un rectangle situé vers X≈650000 DEGRÉS : une zone qui
n'existe pas.

Résultat : 0 entité retournée, et AUCUNE exception levée.
Le script tourne, la couche est « chargée », mais vide — donc
l'indicateur est silencieusement faux.

LA CORRECTION : passer l'emprise comme GeoSeries porteuse de son CRS.
geopandas reprojette alors lui-même le filtre vers le CRS du fichier.

    bbox tuple L93      sur fichier 4326  → 0 entité
    bbox GeoSeries L93  sur fichier 4326  → toutes les entités

Les couches déjà en Lambert 93 fonctionnaient par chance : c'est
précisément le genre de bug qui ne se révèle que chez l'utilisateur
final, avec ses propres données.
─────────────────────────────────────────────────────────────────
"""

import geopandas as gpd


def charger_couche(chemin, emprise, nom_couche, warnings_liste=None):
    """
    Charge UNE couche SIG locale, filtrée par l'emprise, en Lambert 93.

    Paramètres
    ----------
    chemin : str, Path ou None
        Chemin du fichier (.shp, .gpkg, .geojson…). None → renvoie None.
    emprise : GeoDataFrame
        Emprise de travail (tampon déjà appliqué), avec CRS défini.
    nom_couche : str
        Nom lisible, pour les messages et les avertissements.
    warnings_liste : list ou None
        Si fournie, les avertissements y sont ajoutés (_WARNINGS_SPRINGE).

    Retour
    ------
    GeoDataFrame en Lambert 93, ou None si absent / illisible.
    """

    # Couche non renseignée par l'utilisateur : ce n'est pas une erreur.
    if not chemin:
        return None

    try:
        # ── Le point clé ──────────────────────────────────────────────
        # emprise.geometry est une GeoSeries qui TRANSPORTE SON CRS.
        # geopandas reprojette donc le filtre vers le CRS du fichier
        # avant de l'appliquer. Avec un tuple, il ne le ferait pas.
        gdf = gpd.read_file(chemin, bbox=emprise.geometry)

        # Reprojection en Lambert 93, CRS de travail unique du projet.
        # to_epsg() peut renvoyer None sur un CRS non standard : dans ce
        # cas on tente quand même la reprojection.
        if gdf.crs is not None and gdf.crs.to_epsg() != 2154:
            gdf = gdf.to_crs(epsg=2154)

        # Une couche vide n'est pas forcément une erreur (la zone peut
        # réellement n'en contenir aucune), mais l'utilisateur doit le
        # savoir : l'indicateur concerné sera calculé « à blanc ».
        if len(gdf) == 0:
            message = (f"{nom_couche} : 0 entité dans l'emprise — "
                       f"vérifier que la couche couvre la zone d'étude")
            print(f"⚠️  {message}")
            if warnings_liste is not None:
                warnings_liste.append(message)
        else:
            print(f"✔️  {nom_couche:32s} {len(gdf):>7d} entités")

        return gdf

    except Exception as e:
        # On n'interrompt pas le programme : la couche sera simplement
        # retirée de DATA par nettoyer_data(), et l'indicateur tournera
        # sans elle.
        message = f"{nom_couche} : chargement échoué — {str(e)[:120]}"
        print(f"⚠️  {message}")
        if warnings_liste is not None:
            warnings_liste.append(message)
        return None


def charger_couches_utilisateur(chemins, emprise, espace_noms,
                                warnings_liste=None):
    """
    Charge toutes les couches principales déclarées dans la fenêtre.

    Paramètres
    ----------
    chemins : dict
        {nom_variable: chemin_ou_None}, tel que renvoyé par la fenêtre
        « données de calcul des indicateurs ».
    emprise : GeoDataFrame
        Emprise de travail.
    espace_noms : dict
        globals() du script principal. Les GeoDataFrames y sont injectés
        sous leur nom de variable, pour que construire_data les retrouve.
    warnings_liste : list ou None
        Trace des problèmes rencontrés.

    Retour
    ------
    dict {nom_variable: GeoDataFrame|None} — également injecté dans
    espace_noms au passage.
    """

    print(f"\n── Chargement de {len(chemins)} couche(s) utilisateur ──")

    resultats = {}
    for var_name, chemin in chemins.items():
        gdf = charger_couche(chemin, emprise, var_name, warnings_liste)
        resultats[var_name] = gdf
        # Injection dans l'espace de noms du script principal : c'est
        # ainsi que get_gdf("gdf_carrefours") retrouvera la couche.
        espace_noms[var_name] = gdf

    nb_ok = sum(1 for g in resultats.values() if g is not None)
    print(f"   → {nb_ok}/{len(chemins)} couche(s) disponible(s)\n")

    return resultats


def charger_couches_supplementaires(supp_par_bloc, emprise, espace_noms,
                                    warnings_liste=None):
    """
    Charge les couches ajoutées manuellement par l'utilisateur.

    Ces couches n'ont pas de nom prédéfini : on leur en fabrique un
    (gdf_supp_MS1_0, gdf_supp_MS1_1…) qui sera repris dans DATA.

    Paramètres
    ----------
    supp_par_bloc : dict
        {"MS1": [chemins], "MS2": [chemins], "MS3": [chemins]}
    emprise, espace_noms, warnings_liste : voir ci-dessus.

    Retour
    ------
    dict {"MS1": [noms_variables], "MS2": [...], "MS3": [...]}
    Seuls les noms des couches EFFECTIVEMENT chargées y figurent.
    """

    chargees = {bloc: [] for bloc in supp_par_bloc}

    for bloc, chemins in supp_par_bloc.items():
        for i, chemin in enumerate(chemins):
            var_name = f"gdf_supp_{bloc}_{i}"
            gdf = charger_couche(chemin, emprise, var_name, warnings_liste)

            # On n'enregistre que les couches réellement chargées : une
            # couche absente ne doit pas apparaître dans DATA.
            if gdf is not None:
                espace_noms[var_name] = gdf
                chargees[bloc].append(var_name)

    total = sum(len(v) for v in chargees.values())
    if total:
        print(f"✔️  {total} couche(s) supplémentaire(s) chargée(s)\n")

    return chargees
