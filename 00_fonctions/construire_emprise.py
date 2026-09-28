# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Module "construire_emprise"
Objectif : construire la zone de travail (emprise + tampon) de façon
           robuste, et VALIDER qu'elle est exploitable avant de s'en
           servir comme filtre spatial.
═══════════════════════════════════════════════════════════════════

CONTEXTE — LE BUG CORRIGÉ ICI
─────────────────────────────────────────────────────────────────
L'option B (« les tronçons définissent eux-mêmes la zone ») faisait :

    emprise = gdf_troncons.copy()
    emprise["geometry"] = emprise.buffer(0)   # "nettoyage géométrique"
    emprise = emprise.dissolve()
    emprise["geometry"] = emprise.convex_hull

`buffer(0)` est une astuce classique pour RÉPARER DES POLYGONES
invalides (auto-intersections). Mais appliquée à des LIGNES, elle
renvoie une géométrie VIDE : une ligne n'a pas de surface, donc son
tampon de rayon 0 est l'ensemble vide.

Or les tronçons routiers sont des LineString. Résultat en chaîne :
    buffer(0)    → 3 géométries vides
    dissolve()   → géométrie vide
    convex_hull  → géométrie vide
    total_bounds → [nan, nan, nan, nan]

et donc bbox = (nan, nan, nan, nan), transmise ensuite à TOUS les
gpd.read_file(chemin, bbox=...) des couches utilisateur. La lecture
lève alors une exception, rattrapée par le try/except, qui met la
variable à None → get_gdf() renvoie None → « Couche non trouvée »
→ crash tardif dans MS1 (« type reçu : NoneType »).

C'est pour cela que la version précédente fonctionnait : elle chargeait
les couches locales SANS bbox, donc une emprise cassée passait inaperçue.
─────────────────────────────────────────────────────────────────
"""

import geopandas as gpd


def construire_emprise(gdf_source, taille_tampon_km=2, nom="emprise",
                       enveloppe_convexe=True):
    """
    Construit une emprise polygonale valide à partir d'une couche source
    (tronçons linéaires OU polygone d'emprise fourni par l'utilisateur).

    Paramètres
    ----------
    gdf_source : GeoDataFrame
        Soit les tronçons (option B), soit le fichier d'emprise (option A).
        Peut contenir des lignes, des points ou des polygones.
    taille_tampon_km : float
        Rayon du tampon appliqué autour de l'enveloppe, en kilomètres.
    nom : str
        Nom lisible pour les messages console.
    enveloppe_convexe : bool
        True  → on prend l'enveloppe convexe de la fusion (option B :
                des tronçons linéaires ne délimitent pas une surface,
                il faut donc en dériver une).
        False → on garde la forme fusionnée telle quelle (option A :
                l'utilisateur a fourni un polygone d'emprise réfléchi ;
                le passer en enveloppe convexe l'élargirait à tort,
                par exemple pour un département de forme concave).

    Retour
    ------
    GeoDataFrame à une seule entité polygonale, en Lambert 93.
    """

    # ── 1. Harmoniser le CRS AVANT toute opération métrique ──────────────
    # Le tampon s'exprime en mètres : il faut impérativement un CRS projeté.
    # Lambert 93 (EPSG:2154) est le CRS de travail du projet.
    if gdf_source.crs is None:
        raise ValueError(
            f"{nom} : la couche source n'a aucun CRS défini. "
            "Impossible de construire une emprise fiable."
        )
    gdf = gdf_source.to_crs(epsg=2154) if gdf_source.crs.to_epsg() != 2154 else gdf_source.copy()

    # ── 2. Écarter les géométries nulles ou vides ────────────────────────
    # .notna()   : élimine les lignes sans géométrie (None)
    # .is_empty  : élimine les géométries vides (GEOMETRYCOLLECTION EMPTY…)
    # Sans ce filtre, union_all() peut produire un résultat vide.
    avant = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    if len(gdf) < avant:
        print(f"⚠️  {nom} : {avant - len(gdf)} géométrie(s) vide(s) écartée(s)")

    if len(gdf) == 0:
        raise ValueError(f"{nom} : aucune géométrie exploitable dans la couche source.")

    # ── 3. Fusionner puis prendre l'enveloppe convexe ────────────────────
    # union_all() fusionne toutes les entités en une seule géométrie.
    # (remplace unary_union, déprécié depuis geopandas 1.0)
    # convex_hull donne le plus petit polygone convexe contenant le tout.
    #
    # ⚠️ On NE FAIT PAS buffer(0) ici : sur des lignes, cela viderait
    #    la géométrie (voir l'explication en tête de module).
    #    Pour réparer d'éventuels polygones invalides, on utilise
    #    make_valid(), qui préserve les lignes et les points.
    geom_fusionnee = gdf.geometry.make_valid().union_all()
    enveloppe = geom_fusionnee.convex_hull if enveloppe_convexe else geom_fusionnee

    # ── 4. Appliquer le tampon ───────────────────────────────────────────
    # Sur un polygone, buffer(rayon>0) dilate ; sur une ligne ou un point,
    # il crée une zone de largeur 2*rayon. Dans tous les cas on obtient
    # une surface exploitable — contrairement à buffer(0).
    tampon_m = taille_tampon_km * 1000
    if tampon_m > 0:
        enveloppe = enveloppe.buffer(tampon_m)

    # ── 5. Reconstituer un GeoDataFrame à une entité ─────────────────────
    emprise = gpd.GeoDataFrame(geometry=[enveloppe], crs="EPSG:2154")

    # ── 6. Validation immédiate (fail-fast) ──────────────────────────────
    # On vérifie tout de suite que l'emprise est utilisable comme filtre.
    # Mieux vaut s'arrêter ici, avec un message clair, que de propager
    # une bbox NaN dans tout le pipeline.
    valider_emprise(emprise, nom)

    minx, miny, maxx, maxy = emprise.total_bounds
    print(f"✔️  {nom} construite : {(maxx - minx)/1000:.1f} km x "
          f"{(maxy - miny)/1000:.1f} km (tampon {taille_tampon_km} km)")

    return emprise


def valider_emprise(emprise, nom="emprise"):
    """
    Vérifie qu'une emprise est utilisable comme filtre spatial.

    Lève une ValueError explicite en cas de problème, plutôt que de
    laisser une bbox NaN se propager silencieusement dans tous les
    gpd.read_file() en aval.

    Retour
    ------
    tuple (minx, miny, maxx, maxy) validée.
    """

    if emprise is None or len(emprise) == 0:
        raise ValueError(f"{nom} : emprise vide (aucune entité).")

    if emprise.geometry.is_empty.all():
        raise ValueError(
            f"{nom} : toutes les géométries sont vides.\n"
            "Cause fréquente : buffer(0) appliqué à des lignes ou des points."
        )

    minx, miny, maxx, maxy = emprise.total_bounds

    # NaN != NaN est vrai en Python : c'est le test standard pour détecter
    # une valeur non numérique sans importer math ou numpy.
    if any(v != v for v in (minx, miny, maxx, maxy)):
        raise ValueError(
            f"{nom} : étendue non calculable (bornes NaN).\n"
            "L'emprise est géométriquement vide — vérifier sa construction."
        )

    # Une emprise d'étendue nulle (point unique sans tampon) ne filtre rien
    # d'utile et produirait 0 entité partout.
    if maxx <= minx or maxy <= miny:
        raise ValueError(
            f"{nom} : étendue dégénérée ({minx}, {miny}, {maxx}, {maxy}).\n"
            "Vérifier qu'un tampon non nul a bien été appliqué."
        )

    return (minx, miny, maxx, maxy)
