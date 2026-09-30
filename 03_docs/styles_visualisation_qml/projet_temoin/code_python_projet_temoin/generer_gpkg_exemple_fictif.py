# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
generer_gpkg_exemple_fictif.py
Objectif : produire un GeoPackage SPRINGE 26.9.0 ENTIÈREMENT FICTIF, destiné
           au projet QGIS témoin publié sur GitHub (démonstration des styles).
═══════════════════════════════════════════════════════════════════════════

PRINCIPE
--------
1. On dessine un petit réseau routier inventé (3 routes × 5 tronçons × 2 sens
   = 30 tronçons), dans le département fictif « 99 », sans rapport avec un
   réseau réel.
2. On attribue à chaque tronçon des valeurs d'indicateurs choisies à la main,
   de façon à ce que CHAQUE classe de CHAQUE style .qml soit représentée
   (scores bas / moyens / hauts pour chaque enjeu, 1 à 8 populations,
   1 à 5 espèces, relevés récents ou anciens, etc.).
3. On invente des points de populations d'EEE (valeurs du protocole national :
   largeur, longueur, compacité…) placés à l'intérieur des tronçons.
4. Pour la caractérisation, on N'ÉCRIT RIEN À LA MAIN : on appelle les vrais
   modules de SPRINGE (join_num_troncon_a_gdf_EEE, caracteriser_populations_EEE,
   ecrire_table_caracterisation, ecrire_couche_populations). La table, les
   champs de synthèse et la couche de points sont donc strictement identiques
   à ce que produit l'outil.

Les scores, eux, ne sont PAS calculés par l'algorithme (il faudrait des
couches INPN, IGN, SNCF réelles) : ils sont fixés à la main, dans les plages
de la version 26.9.0 (MS ≤ 16, N ≤ 10, P ≤ 12, total ≤ 38), et les scores
d'enjeu et le total sont bien les sommes des indicateurs (coefficients = 1).

UTILISATION
-----------
    python generer_gpkg_exemple_fictif.py
Le dossier contenant les modules SPRINGE doit être indiqué dans DOSSIER_SPRINGE.
Le tirage aléatoire est « graine fixe » : deux exécutions donnent le même fichier.
"""

import sys
import random
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point, MultiPolygon, Polygon, box
from shapely.ops import substring

# ─────────────────────────────────────────────────────────────────────────
# PARAMÈTRES
# ─────────────────────────────────────────────────────────────────────────
DOSSIER_SPRINGE = "/mnt/project"          # où se trouvent les modules SPRINGE
DOSSIER_SORTIE = Path("/mnt/user-data/outputs")
NOM = "SPRINGE_version202609_exemple_fictif_20260929"   # fichier ET couche
CHEMIN_GPKG = DOSSIER_SORTIE / f"{NOM}.gpkg"
CRS = "EPSG:2154"                          # Lambert-93, comme les vraies sorties

LONGUEUR_TRONCON = 1000   # m, comme les tronçons PR réels (dist_fin - dist_deb)
DECALAGE_AXE = 110        # m, distance entre l'axe et le milieu de la bande G ou D
DEMI_LARGEUR = 100        # m, demi-largeur de la bande de chaque sens
# → bande G entre 10 et 210 m à gauche de l'axe, bande D symétrique à droite.
#   Dans les vraies sorties, les polygones G et D se superposent ; ici on les
#   sépare pour que les deux sens restent lisibles dans le projet témoin.

GRAINE = 2609             # graine fixe = résultat reproductible
random.seed(GRAINE)
np.random.seed(GRAINE)

# Les modules SPRINGE sont importés depuis leur dossier d'origine.
sys.path.insert(0, DOSSIER_SPRINGE)
import join_num_troncon_a_gdf_EEE as jn            # noqa: E402
import caracteriser_populations_EEE as cpe         # noqa: E402
import ecrire_table_caracterisation as etc         # noqa: E402
import ecrire_couche_populations as ecp            # noqa: E402


# ═════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 — LE RÉSEAU FICTIF
# ═════════════════════════════════════════════════════════════════════════
# Trois axes de 5 km, posés dans une zone vide de Lambert-93 (le projet témoin
# n'a pas de fond de carte : la position absolue n'a aucune importance).
#   - route A : droite est-ouest
#   - route B : sinueuse nord-sud (pour montrer des tronçons courbes)
#   - route C : diagonale
x0, y0 = 700000, 6700000
t = np.linspace(0, 1, 200)
ROUTES = {
    # code route (format SI Route « dépt + route »), libellé court, 1er PR, axe
    "A": ("99 N0901", "N901", 1,
          LineString([(x0, y0), (x0 + 5200, y0)])),
    "B": ("99 N0902", "N902", 11,
          LineString(list(zip(x0 + 6600 + 350 * np.sin(t * 2 * np.pi),
                              y0 - 3000 + 5600 * t)))),
    "C": ("99 N0903", "N903", 21,
          LineString([(x0 + 800, y0 + 2000), (x0 + 800 + 3700, y0 + 2000 + 3700)])),
}


def bande(ligne, cote):
    """
    Construit le polygone d'un sens de circulation autour d'un bout d'axe.
    offset_curve décale la ligne de DECALAGE_AXE mètres (positif = à gauche
    dans le sens de la ligne), puis buffer avec cap_style='flat' l'épaissit
    sans arrondir les extrémités : deux tronçons successifs se touchent
    alors bord à bord, comme des tronçons PR.
    """
    decale = ligne.offset_curve(DECALAGE_AXE if cote == "G" else -DECALAGE_AXE)
    return decale.buffer(DEMI_LARGEUR, cap_style="flat")


lignes = []
for cle, (route, lib, pr0, axe) in ROUTES.items():
    for k in range(5):
        # Bout d'axe du tronçon : de k km à (k+1) km le long de la route.
        morceau = substring(axe, k * LONGUEUR_TRONCON, (k + 1) * LONGUEUR_TRONCON)
        pr = pr0 + k
        for cote in ("D", "G"):
            lignes.append({
                "nom_plo_fi": f"99PR{pr}{cote}",        # identifiant du tronçon
                "route": route + ("  G" if cote == "G" else ""),  # format SI Route
                "lib_rte": lib,
                "dist_deb": k * LONGUEUR_TRONCON,
                "dist_fin": (k + 1) * LONGUEUR_TRONCON,
                "portee": cote,
                "gestionnai": "DIR FICTIVE",
                "nom_plo_in": f"99PR{pr - 1}{cote}",    # PR précédent
                "zone": "A",
                "tampon": "2",
                "_axe": morceau,        # conservé pour placer les populations
                "_cote": cote,
                "geometry": bande(morceau, cote),
            })

troncons = gpd.GeoDataFrame(lignes, crs=CRS)


def couper_en_deux(poly):
    """
    Retire une bande de 80 m au milieu du polygone → 2 morceaux. Sert à
    illustrer la règle « Tronçon en plusieurs portions dispersées »
    (num_geometries > 1) présente dans tous les styles.
    """
    c = poly.centroid
    trou = box(c.x - 40, c.y - 400, c.x + 40, c.y + 400)
    return poly.difference(trou)


for ident in ("99PR3G", "99PR22D"):
    i = troncons.index[troncons.nom_plo_fi == ident][0]
    troncons.at[i, "geometry"] = couper_en_deux(troncons.at[i, "geometry"])

# Les vraies sorties sont en MULTIPOLYGON : on convertit tout le monde.
troncons["geometry"] = troncons.geometry.apply(
    lambda g: g if isinstance(g, MultiPolygon) else MultiPolygon([g]))


# ═════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 — QUELS TRONÇONS ONT DES OBSERVATIONS, ET LESQUELLES
# ═════════════════════════════════════════════════════════════════════════
# 8 tronçons sans observation (dont un en plusieurs portions : 99PR22D),
# 22 avec. Pour chacun des 22, on fixe un « profil » qui garantit que chaque
# classe des styles 06 à 10 est représentée :
#   nb   : nombre de populations      (styles 06 : 1 / 2-3 / 4-5 / 6+)
#   esp  : espèces présentes          (style 07 : 1 / 2 / 3 / 4-5)
#   an   : classe d'ancienneté        (style 08 : NULL / ≤4 / 5-8 / 9-12 / >12 ans)
#   comp : compacité maximale         (style 09 : continue / taches / isolés / nr)
#   s20  : nb de populations > 20 m   (style 10 : 0 / 1 / 2-3 / 4+)
SANS_OBS = ["99PR1D", "99PR5G", "99PR12D", "99PR14G", "99PR15D",
            "99PR22D", "99PR24G", "99PR25D"]

R, A, AM, H, X = ("Reynoutria sp", "Ailanthus altissima",
                  "Ambrosia artemisiifolia", "Heracleum mantegazzianum", "EEE autre")
PROFILS = [
    dict(nb=1, esp=[R],             an="recent", comp="continue", s20=1),
    dict(nb=1, esp=[A],             an="null",   comp="taches",   s20=0),
    dict(nb=1, esp=[AM],            an="5-8",    comp="isoles",   s20=0),
    dict(nb=1, esp=[X],             an="vieux",  comp="nr",       s20=0),
    dict(nb=1, esp=[H],             an="9-12",   comp="continue", s20=1),
    dict(nb=2, esp=[R],             an="recent", comp="continue", s20=2),
    dict(nb=2, esp=[R, X],          an="5-8",    comp="taches",   s20=0),
    dict(nb=3, esp=[A],             an="9-12",   comp="isoles",   s20=0),
    dict(nb=3, esp=[R, AM],         an="recent", comp="taches",   s20=1),
    dict(nb=3, esp=[R, A, X],       an="vieux",  comp="continue", s20=2),
    dict(nb=2, esp=[H, R],          an="null",   comp="nr",       s20=0),
    dict(nb=3, esp=[AM],            an="recent", comp="continue", s20=3),
    dict(nb=4, esp=[R, A],          an="5-8",    comp="continue", s20=4),
    dict(nb=4, esp=[R, A, H],       an="recent", comp="taches",   s20=1),
    dict(nb=5, esp=[R, A, H, X],    an="9-12",   comp="continue", s20=2),
    dict(nb=4, esp=[AM, X],         an="vieux",  comp="isoles",   s20=0),
    dict(nb=5, esp=[R],             an="recent", comp="taches",   s20=0),
    dict(nb=5, esp=[R, A, AM, H, X], an="recent", comp="continue", s20=3),
    dict(nb=6, esp=[R, A],          an="5-8",    comp="continue", s20=5),
    dict(nb=7, esp=[R, A, H],       an="recent", comp="continue", s20=4),
    dict(nb=8, esp=[R, A, AM, H, X], an="9-12",  comp="taches",   s20=2),
    dict(nb=6, esp=[AM, X, R],      an="vieux",  comp="isoles",   s20=0),
]

AVEC_OBS = [i for i in troncons.nom_plo_fi if i not in SANS_OBS]
assert len(AVEC_OBS) == len(PROFILS) == 22

# Bornes d'années pour chaque classe d'ancienneté (année de référence 2026,
# comme year(now()) dans le style 08 au moment de la publication).
ANNEES = {"recent": (2022, 2026), "5-8": (2018, 2021),
          "9-12": (2014, 2017), "vieux": (1995, 2012)}


def tirer_compacites(n, classe):
    """
    Renvoie n valeurs de compacité respectant la classe « maximale » voulue :
      continue → au moins une 'Continue'
      taches   → au moins une 'Taches', aucune 'Continue'
      isoles   → uniquement 'Isoles'
      nr       → uniquement non renseigné (valeur vide dans la couche brute)
    """
    if classe == "isoles":
        return ["Isoles"] * n
    if classe == "nr":
        return [None] * n
    tete = "Continue" if classe == "continue" else "Taches"
    reste_possible = (["Continue", "Taches", "Isoles", None]
                      if classe == "continue" else ["Taches", "Isoles", None])
    return [tete] + random.choices(reste_possible, k=n - 1)


def point_dans_bande(axe, cote, abscisse):
    """
    Place un point à « abscisse » mètres du début du tronçon, du bon côté de
    l'axe, à une distance aléatoire restant dans la bande (entre 30 et 190 m).
    On calcule la normale à l'axe à partir de deux points très proches.
    """
    p1 = axe.interpolate(abscisse)
    p2 = axe.interpolate(min(abscisse + 1, axe.length))
    if p2.equals(p1):                               # fin de ligne
        p1 = axe.interpolate(abscisse - 1)
        p2 = axe.interpolate(abscisse)
    dx, dy = p2.x - p1.x, p2.y - p1.y
    norme = np.hypot(dx, dy)
    nx, ny = -dy / norme, dx / norme                # normale à gauche
    signe = 1 if cote == "G" else -1
    d = random.uniform(30, 190)
    base = axe.interpolate(abscisse)
    return Point(base.x + signe * d * nx, base.y + signe * d * ny)


pops = []
for ident, prof in zip(AVEC_OBS, PROFILS):
    ligne = troncons.loc[troncons.nom_plo_fi == ident].iloc[0]
    n = prof["nb"]

    # Espèces : chaque espèce du profil reçoit au moins une population,
    # les populations restantes sont réparties au hasard entre elles.
    especes = prof["esp"] + random.choices(prof["esp"], k=n - len(prof["esp"]))
    random.shuffle(especes)

    # Longueurs : exactement s20 populations 'Sup20m', les autres plus courtes
    # (ou non renseignées), pour maîtriser le style 10.
    longueurs = (["Sup20m"] * prof["s20"]
                 + random.choices(["Inf5m", "5a20m", "5a20m", None], k=n - prof["s20"]))
    random.shuffle(longueurs)

    compacites = tirer_compacites(n, prof["comp"])
    random.shuffle(compacites)

    # Abscisses espacées d'au moins 60 m : respecte la règle des 50 m du
    # protocole (deux individus à moins de 50 m = une seule population).
    abscisses = sorted(random.sample(range(40, 961, 60), n))

    # Dates : aucune si classe « null », sinon une année maximale dans la
    # classe, les autres populations pouvant être plus anciennes.
    if prof["an"] == "null":
        annees = [None] * n
    else:
        amin, amax = ANNEES[prof["an"]]
        an_max = random.randint(amin, amax)
        annees = [an_max] + [random.randint(max(1995, an_max - 6), an_max)
                             for _ in range(n - 1)]
        random.shuffle(annees)

    for esp, lon, comp, absc, an in zip(especes, longueurs, compacites, abscisses, annees):
        pops.append({
            "species_name_sci": esp,
            "largeur": random.choice(["Inf1m", "1a3m", "1a3m", "Sup3m", None]),
            "longueur": lon,
            "compacite": comp,
            "abscisse": float(absc),
            "localisation": random.choice(["Talus", "Accotement", "TPC", "Fosse", "Autre"]),
            "evaluation": random.choices(["Certain", "Incertain", None], [8, 1, 1])[0],
            "date": (pd.Timestamp(an, random.randint(5, 9), random.randint(1, 28))
                     if an else pd.NaT),
            "geometry": point_dans_bande(ligne["_axe"], ligne["_cote"], absc),
        })

gdf_EEE = gpd.GeoDataFrame(pops, crs=CRS)


# ═════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 — INDICATEURS ET SCORES (fixés à la main)
# ═════════════════════════════════════════════════════════════════════════
# Variantes par enjeu et par niveau. Chaque tuple donne les indicateurs dans
# l'ordre de l'enjeu ; les commentaires indiquent la somme obtenue.
# Les niveaux « bas / moyen / haut » correspondent aux 3 classes des styles.
MS_VAR = {  # (MS1, MS1b, MS2, MS3)         style 02 : ≤10 / 11-12 / 13-16
    "b": [(2, 0, 3, 0), (3, 1, 3, 2)],                    # 5, 9
    "m": [(4, 0, 3, 4), (5, 1, 3, 3)],                    # 11, 12
    "h": [(5, 0, 3, 5), (5, 1, 3, 5), (5, 1, 5, 5)],      # 13, 14, 16
}
N_VAR = {   # (N1, N2)                       style 03 : ≤6 / 7-8 / 9-10
    "b": [(1, 3), (0, 2), (2, 4)],                        # 4, 2, 6
    "m": [(3, 4), (3, 5)],                                # 7, 8
    "h": [(4, 5), (5, 5)],                                # 9, 10
}
P_VAR = {   # (P1, P2, P3, P4)               style 04 : ≤7 / 8-9 / 10-12
    "b": [(0, 1, 0, 1), (1, 3, 0, 2)],                    # 2, 6
    "m": [(1, 4, 1, 2), (0, 5, 1, 3)],                    # 8, 9
    "h": [(1, 5, 2, 2), (1, 5, 2, 4)],                    # 10, 12
}
# Un triplet de niveaux (MS, N, P) par tronçon observé, choisi pour couvrir
# aussi les 3 classes du score total (style 01 : ≤16 / 17-28 / 29-38).
NIVEAUX = ["bbb", "bbb", "bbm", "bmb", "mbb", "bbh", "mbm", "bmm", "mmb",
           "hbb", "bhb", "mmm", "hmb", "mhm", "hmh", "mhh", "hhm", "hhh",
           "hhh", "hmm", "bhh", "hbh"]
assert len(NIVEAUX) == 22

INDIC = ["MS1_impact", "MS1b_impact", "MS2_impact", "MS3_impact",
         "N1_impact", "N2_impact",
         "P1_impact", "P2_impact", "P3_impact", "P4_impact"]

valeurs = {}
compteur = {"MS": {}, "N": {}, "P": {}}   # pour faire tourner les variantes


def variante(enjeu, table, niveau):
    """Prend la variante suivante du niveau demandé (rotation), pour varier les valeurs."""
    k = compteur[enjeu].get(niveau, 0)
    compteur[enjeu][niveau] = k + 1
    return table[niveau][k % len(table[niveau])]


for ident, niv in zip(AVEC_OBS, NIVEAUX):
    valeurs[ident] = (variante("MS", MS_VAR, niv[0])
                      + variante("N", N_VAR, niv[1])
                      + variante("P", P_VAR, niv[2]))

# Tronçons sans observation : comme dans les vraies sorties, seuls les
# critères de vulnérabilité liés au contexte (trafic, riverains) sont non nuls.
for ident in SANS_OBS:
    valeurs[ident] = (0, random.choice([0, 1]), random.choice([0, 3]), 0,
                      0, 0, 0, 0, 0, 0)

scores = pd.DataFrame.from_dict(valeurs, orient="index", columns=INDIC)
scores.index.name = "nom_plo_fi"
scores = scores.reset_index()

# Scores d'enjeu = sommes (coefficients de pondération par défaut = 1).
scores["score_enjeu_MS"] = scores[INDIC[0:4]].sum(axis=1)
scores["score_enjeu_N"] = scores[INDIC[4:6]].sum(axis=1)
scores["score_enjeu_P"] = scores[INDIC[6:10]].sum(axis=1)
scores["score_troncon_final"] = scores[["score_enjeu_MS", "score_enjeu_N",
                                        "score_enjeu_P"]].sum(axis=1)

# Rangs indicatifs : même règle que preparer_couche_gpkg (ex æquo au même
# rang, puis saut : 1, 1, 3…), calculés sur tous les tronçons de la zone.
for src, dst in [("score_enjeu_MS", "rang_indicatif_MS"),
                 ("score_enjeu_N", "rang_indicatif_N"),
                 ("score_enjeu_P", "rang_indicatif_P"),
                 ("score_troncon_final", "rang_indicatif_final")]:
    scores[dst] = scores[src].rank(method="min", ascending=False).astype(int)


# ═════════════════════════════════════════════════════════════════════════
# ÉTAPE 4 — CHAMPS DE CONTEXTE (comptages d'objets à proximité)
# ═════════════════════════════════════════════════════════════════════════
# Ces champs existent dans les vraies sorties ; on les remplit avec des
# valeurs plausibles, cohérentes avec les indicateurs (ex. Niv1 à 1 si N1
# est élevé). Ils ne servent à aucun style.
def contexte(r):
    ms1, _, ms2, ms3, n1, _, _, _, p3, _ = (r[c] for c in INDIC)
    return pd.Series({
        "carrefours": random.randint(1, 8) if ms1 else random.randint(0, 2),
        "echangeurs": random.randint(0, 2) if ms1 >= 4 else 0,
        "passages à niveaux": 0,
        "habitations": random.randint(3, 30) if ms2 else 0,
        "zones_activites": random.randint(1, 20) if ms2 >= 5 else random.randint(0, 3),
        "écrans acoustiques": random.randint(1, 20) if ms3 >= 3 else 0,
        "murs consédés": 0,
        "ponts consédés": random.randint(1, 2) if ms3 >= 5 else 0,
        "passages_faune": 0,
        "ponts_sncf_api": 1 if ms3 >= 4 else 0,
        "ponts": random.randint(1, 2) if ms3 >= 5 else 0,
        "Niv1": int(n1 >= 4), "Niv2": int(n1 == 3), "Niv3": int(n1 in (1, 2)),
        "Niv4": 0,
        "Niv1_tamponP3": int(p3 == 2), "Niv2_tamponP3": 0,
        "Niv3_tamponP3": int(p3 == 1), "Niv4_tamponP3": 0,
    })


ctx = pd.concat([scores[["nom_plo_fi"]], scores.apply(contexte, axis=1)], axis=1)


# ═════════════════════════════════════════════════════════════════════════
# ÉTAPE 5 — CARACTÉRISATION PAR LES VRAIS MODULES SPRINGE
# ═════════════════════════════════════════════════════════════════════════
# 5a. Rattachement des points aux tronçons (colonne nom_plo_fi, avec
#     « A, B » si un point touche deux tronçons), comme dans le lanceur.
gdf_EEE = jn.join_num_troncon_a_gdf_EEE(
    gdf_EEE, troncons[["nom_plo_fi", "geometry"]], "nom_plo_fi")

# Correspondance « information → nom de colonne » : ici les colonnes brutes
# portent déjà le nom attendu (dans la vraie vie, fenetre_mapping_colonnes_EEE
# fait ce lien avec les noms propres à chaque DIR).
mapping = {"largeur": "largeur", "longueur": "longueur", "compacite": "compacite",
           "abscisse": "abscisse", "localisation": "localisation",
           "evaluation": "evaluation", "date": "date"}

# 5b. Caractérisation : renvoie les champs de synthèse (ajoutés à df_scoring),
#     la table tronçon × espèce et un diagnostic (non utilisé ici).
troncons_attr = troncons.drop(columns=["_axe", "_cote"])
df_scoring, df_caracterisation, _ = cpe.caracteriser_populations_EEE(
    gdf_EEE=gdf_EEE,
    df_scoring=scores.copy(),
    gdf_troncons=troncons_attr,
    mapping_colonnes=mapping,
    categories_retenues=list(cpe.CATEGORIES_SPRINGE.keys()),
    colonne_id="nom_plo_fi",
    source_pr="si_route",
    liste_avertissements=[],
)


# ═════════════════════════════════════════════════════════════════════════
# ÉTAPE 6 — ÉCRITURE DU GEOPACKAGE (même structure que les vraies sorties)
# ═════════════════════════════════════════════════════════════════════════
# Ordre des colonnes identique à une sortie réelle de SPRINGE 26.9.0.
COLONNES = (["nom_plo_fi", "route", "lib_rte", "dist_deb", "dist_fin", "portee",
             "gestionnai", "nom_plo_in", "zone", "tampon"]
            + list(ctx.columns[1:])
            + ["MS1_impact", "MS1b_impact", "MS2_impact", "MS3_impact",
               "score_enjeu_MS", "rang_indicatif_MS",
               "N1_impact", "N2_impact", "score_enjeu_N", "rang_indicatif_N",
               "P1_impact", "P2_impact", "P3_impact", "P4_impact",
               "score_enjeu_P", "rang_indicatif_P",
               "score_troncon_final", "rang_indicatif_final",
               "statut_donnee", "nb_populations_total", "nb_categories_presentes",
               "synthese_EEE", "annee_releve_max"])

couche = (troncons_attr
          .merge(ctx, on="nom_plo_fi")
          .merge(df_scoring, on="nom_plo_fi"))
couche = gpd.GeoDataFrame(couche[COLONNES + ["geometry"]], crs=CRS)

if CHEMIN_GPKG.exists():
    CHEMIN_GPKG.unlink()           # on repart d'un fichier neuf
couche.to_file(CHEMIN_GPKG, layer=NOM, driver="GPKG")

# Table et couche de points : écrites par les modules de l'outil (mode ajout).
etc.ecrire_table_caracterisation(df_caracterisation=df_caracterisation,
                                 chemin_gpkg=str(CHEMIN_GPKG),
                                 liste_avertissements=[])
ecp.ecrire_couche_populations(gdf_EEE=gdf_EEE, mapping_colonnes=mapping,
                              chemin_gpkg=str(CHEMIN_GPKG), crs_cible=couche.crs,
                              colonne_id="nom_plo_fi", liste_avertissements=[])

print(f"\n✔ GeoPackage fictif écrit : {CHEMIN_GPKG}")
