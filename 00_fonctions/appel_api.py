# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Module "appel_api"
Objectif : centraliser TOUS les appels aux services WFS (BD TOPO, IGN
           BDCarto, INPN…) dans une fonction unique, avec un filtrage
           spatial réellement effectif sur l'emprise de travail.
═══════════════════════════════════════════════════════════════════

CE QUE CE MODULE CORRIGE PAR RAPPORT À L'ANCIEN CODE
─────────────────────────────────────────────────────────────────
1. BBOX INOPÉRANTE
   Ancien : "...&bbox{minx},{miny},{maxx},{maxy}"
   Il manquait le signe « = » après « bbox », et le paramètre était
   collé à une chaîne de connexion OGR qui ne l'interprète pas.
   Résultat : AUCUN filtre spatial → téléchargement de la France entière
   pour chaque couche (d'où la lenteur et les timeouts).

2. REQUEST=GetCapabilities AU LIEU DE GetFeature
   Ancien (bloc IGN) : REQUEST=GetCapabilities
   GetCapabilities retourne les MÉTADONNÉES du service, pas les données.

3. BBOX DANS LE MAUVAIS SYSTÈME DE COORDONNÉES
   Les bornes étaient en Lambert 93 (mètres) alors que l'URL annonçait
   parfois EPSG:4326 (degrés).

4. ORDRE DES AXES EN EPSG:4326
   En WFS 2.0.0, EPSG:4326 est officiellement en ordre latitude/longitude,
   alors que total_bounds fournit longitude/latitude. Selon la tolérance
   du serveur, la bbox peut être silencieusement inversée.
   → On interroge par défaut en EPSG:2154 (Lambert 93), qui est en
     easting/northing : aucune ambiguïté possible, et aucune reprojection.

5. PAGINATION ABSENTE
   Les serveurs WFS limitent le nombre d'entités par requête (souvent
   1000 ou 5000). Sans pagination, on récupère un résultat TRONQUÉ sans
   aucun avertissement. On boucle donc sur STARTINDEX.

6. ERREUR D'ENCODAGE ('charmap' codec can't decode byte 0x8f)
   Elle vient de GDAL lisant le flux avec l'encodage système Windows
   (cp1252). On télécharge donc via requests, et on passe les octets
   bruts à geopandas en demandant du GeoJSON (UTF-8 par spécification).
─────────────────────────────────────────────────────────────────
"""

import io
import re
import geopandas as gpd
import requests


# ═══════════════════════════════════════════════════════════════════
# 0. LECTURE DES ERREURS RENVOYÉES PAR UN SERVEUR WFS
# ═══════════════════════════════════════════════════════════════════

def _extraire_erreur_wfs(contenu):
    """
    Extrait le message d'erreur lisible d'une réponse WFS en erreur.

    Un serveur WFS qui refuse une requête répond par un document XML
    <ows:ExceptionReport> — souvent avec un code HTTP 200, ce qui fait
    que requests ne lève rien. Le message utile est dans la balise
    <ows:ExceptionText> et/ou l'attribut exceptionCode.

    Sans cette extraction, on ne voyait que les 200 premiers octets bruts
    (« b'<?xml version="1.0" encoding="UTF-8"?>... »), c'est-à-dire
    l'en-tête XML — strictement aucune information utile.

    Retour
    ------
    str ou None : le message d'erreur, ou None si ce n'est pas une exception.
    """
    # On ne décode que le début, en tolérant les octets invalides.
    texte = contenu[:4000].decode("utf-8", errors="replace")

    if "ExceptionReport" not in texte and "ServiceException" not in texte:
        return None

    morceaux = []

    # Code d'exception : InvalidParameterValue, OperationNotSupported…
    code = re.search(r'exceptionCode="([^"]+)"', texte)
    if code:
        morceaux.append(f"code={code.group(1)}")

    # Paramètre fautif (locator) : outputFormat, srsName, typeName…
    locator = re.search(r'locator="([^"]+)"', texte)
    if locator:
        morceaux.append(f"paramètre={locator.group(1)}")

    # Message en clair. Deux dialectes selon la version du protocole.
    txt = re.search(r"<(?:ows:)?ExceptionText>(.*?)</(?:ows:)?ExceptionText>",
                    texte, re.DOTALL)
    if not txt:
        txt = re.search(r"<(?:ogc:)?ServiceException[^>]*>(.*?)</(?:ogc:)?ServiceException>",
                        texte, re.DOTALL)
    if txt:
        # On compacte les espaces et retours à la ligne du XML.
        morceaux.append(" ".join(txt.group(1).split())[:250])

    return " | ".join(morceaux) if morceaux else "exception WFS non détaillée"


# ═══════════════════════════════════════════════════════════════════
# 1. CALCUL DE LA BBOX À TRANSMETTRE AU SERVEUR
# ═══════════════════════════════════════════════════════════════════

def bbox_pour_api(emprise, code_epsg=2154):
    """
    Calcule la bounding box de l'emprise dans le CRS attendu par l'API.

    Paramètres
    ----------
    emprise : GeoDataFrame
        Emprise de travail (tampon déjà appliqué).
    code_epsg : int
        Code EPSG dans lequel le serveur doit recevoir la bbox.
        2154 (Lambert 93) par défaut : axes easting/northing, non ambigus.

    Retour
    ------
    tuple (minx, miny, maxx, maxy) dans le CRS demandé.
    """
    if emprise is None or len(emprise) == 0:
        raise ValueError("bbox_pour_api : emprise vide ou absente.")

    # to_crs renvoie une copie : l'emprise d'origine n'est pas modifiée.
    emprise_cible = emprise.to_crs(epsg=code_epsg)
    minx, miny, maxx, maxy = emprise_cible.total_bounds

    # Garde-fou : des bornes NaN signifient une emprise géométriquement
    # vide. Mieux vaut lever ici que d'envoyer "BBOX=nan,nan,nan,nan".
    if any(v != v for v in (minx, miny, maxx, maxy)):
        raise ValueError(
            "bbox_pour_api : bornes NaN — l'emprise est vide.\n"
            "Vérifier sa construction (buffer(0) sur des lignes ?)."
        )

    return (minx, miny, maxx, maxy)


# ═══════════════════════════════════════════════════════════════════
# 2. CHARGEMENT D'UNE COUCHE WFS (avec pagination)
# ═══════════════════════════════════════════════════════════════════

def charger_couche_wfs(endpoint, type_name, bbox, code_epsg=2154,
                       version="2.0.0", format_sortie="application/json",
                       taille_page=1000, max_pages=50, timeout=120,
                       avec_srsname=True, bbox_avec_crs=True):
    """
    Télécharge UNE couche WFS filtrée par bbox, en gérant la pagination.

    Principe de la pagination WFS 2.0.0 :
      - COUNT       = nombre maximum d'entités par requête
      - STARTINDEX  = index de la première entité à retourner
    On boucle en incrémentant STARTINDEX jusqu'à recevoir une page
    incomplète (ou vide), signe qu'on a tout récupéré.

    Paramètres
    ----------
    endpoint : str
        URL de base du service, ex. "https://data.geopf.fr/wfs/ows".
    type_name : str
        Nom technique de la couche, ex. "BDTOPO_V3:troncon_de_route".
    bbox : tuple
        (minx, miny, maxx, maxy) dans le CRS `code_epsg`.
    code_epsg : int
        CRS de la bbox ET de la réponse demandée.
    version : str
        Version du protocole WFS. "2.0.0" pour la Géoplateforme,
        "1.1.0" ou "1.0.0" pour certains services plus anciens (INPN).
    format_sortie : str
        Format demandé. GeoJSON ("application/json") est préférable :
        encodage UTF-8 garanti, parsing fiable par geopandas.
    taille_page : int
        Entités par requête. Au-delà de ~5000 les serveurs refusent.
    max_pages : int
        Garde-fou anti-boucle infinie.
    timeout : int
        Délai maximum par requête, en secondes.

    Retour
    ------
    GeoDataFrame concaténé, ou GeoDataFrame vide si aucune entité.
    """

    # WFS 1.x utilise "maxFeatures", WFS 2.x utilise "count".
    # On adapte le nom du paramètre selon la version annoncée.
    cle_nb = "count" if version.startswith("2") else "maxFeatures"

    morceaux = []          # liste des GeoDataFrames de chaque page
    index_depart = 0

    for _ in range(max_pages):

        # On construit les paramètres sous forme de DICTIONNAIRE plutôt
        # que par concaténation de chaîne : requests se charge alors de
        # l'encodage URL correct (c'est ce qui manquait avec "&bbox...").
        params = {
            "SERVICE": "WFS",
            "VERSION": version,
            "REQUEST": "GetFeature",          # ← et non GetCapabilities
            "TYPENAME": type_name,
            cle_nb: taille_page,
        }

        # SRSNAME : tous les serveurs ne l'acceptent pas. Quand il est
        # omis, le serveur répond dans son CRS natif et on reprojette
        # nous-mêmes ensuite — c'est moins efficace mais toujours correct.
        if avec_srsname:
            params["SRSNAME"] = f"EPSG:{code_epsg}"

        # BBOX : le 5e élément (le CRS) est requis par WFS 2.0.0 mais
        # rejeté par certaines implémentations 1.x plus anciennes.
        if bbox_avec_crs:
            params["BBOX"] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:{code_epsg}"
        else:
            params["BBOX"] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

        # OUTPUTFORMAT : GeoJSON est préférable, mais les serveurs anciens
        # (MapServer / Carmen) ne servent que du GML. format_sortie=None
        # laisse le serveur répondre dans son format par défaut.
        if format_sortie:
            params["OUTPUTFORMAT"] = format_sortie
        # STARTINDEX n'existe qu'en WFS 2.x.
        if version.startswith("2"):
            params["STARTINDEX"] = index_depart

        reponse = requests.get(endpoint, params=params, timeout=timeout)

        # raise_for_status() lève une exception explicite sur un code
        # HTTP 4xx/5xx, au lieu de laisser geopandas échouer sur du HTML.
        reponse.raise_for_status()

        # Certains serveurs renvoient une erreur XML avec un code HTTP 200.
        # On la détecte, et surtout on en EXTRAIT le message lisible.
        message_erreur = _extraire_erreur_wfs(reponse.content)
        if message_erreur:
            raise RuntimeError(f"[{type_name}] {message_erreur}")

        # On passe les OCTETS BRUTS à geopandas via un tampon mémoire.
        # C'est ce qui évite l'erreur 'charmap' : aucun décodage n'est
        # tenté avec l'encodage système Windows.
        gdf_page = gpd.read_file(io.BytesIO(reponse.content))

        # Page vide → on a tout récupéré.
        if len(gdf_page) == 0:
            break

        morceaux.append(gdf_page)

        # Page incomplète → c'était la dernière.
        if len(gdf_page) < taille_page:
            break

        index_depart += taille_page

        # WFS 1.x ne sait pas paginer : on s'arrête après la 1re page
        # pour ne pas retélécharger la même chose indéfiniment.
        if not version.startswith("2"):
            break

    # Aucune entité trouvée dans l'emprise : ce n'est pas une erreur.
    # On renvoie un GeoDataFrame vide mais correctement typé, pour que
    # le code aval puisse faire len() dessus sans planter.
    if not morceaux:
        return gpd.GeoDataFrame(geometry=[], crs=f"EPSG:{code_epsg}")

    # pd.concat via geopandas : on reconstruit un GeoDataFrame unique.
    gdf = gpd.GeoDataFrame(
        gpd.pd.concat(morceaux, ignore_index=True),
        crs=morceaux[0].crs
    )
    return gdf


# ═══════════════════════════════════════════════════════════════════
# 2bis. STRATÉGIES DE REPLI
# ═══════════════════════════════════════════════════════════════════

# Tous les serveurs WFS ne parlent pas le même dialecte. Un service
# ancien (MapServer, Carmen…) rejette des paramètres qu'un service
# récent (Géoplateforme) exige. Plutôt que de deviner, on essaie
# plusieurs combinaisons du plus riche au plus rustique, et on garde
# la première qui répond.
#
# Chaque stratégie est un dict passé tel quel à charger_couche_wfs().
# L'ordre va du plus efficace (GeoJSON, CRS imposé) au plus permissif
# (format natif du serveur, aucun paramètre optionnel).

STRATEGIES_WFS = [
    {"nom": "GeoJSON + SRSNAME + BBOX/CRS",
     "format_sortie": "application/json", "avec_srsname": True,  "bbox_avec_crs": True},

    {"nom": "GeoJSON + SRSNAME, BBOX sans CRS",
     "format_sortie": "application/json", "avec_srsname": True,  "bbox_avec_crs": False},

    {"nom": "format natif + SRSNAME + BBOX/CRS",
     "format_sortie": None,               "avec_srsname": True,  "bbox_avec_crs": True},

    {"nom": "format natif, BBOX sans CRS",
     "format_sortie": None,               "avec_srsname": False, "bbox_avec_crs": False},
]


def trouver_strategie(endpoint, type_name, bbox, code_epsg, version, timeout=60):
    """
    Détermine, en testant, quelle combinaison de paramètres ce serveur accepte.

    On ne teste qu'UNE SEULE couche : une fois la stratégie trouvée, elle
    vaut pour toutes les autres couches du même service. Cela évite de
    répéter quatre tentatives infructueuses sur chacune des 14 couches INPN.

    Retour
    ------
    tuple (strategie|None, liste_des_erreurs)
        strategie = None si aucune combinaison ne fonctionne ; la liste
        des erreurs permet alors d'afficher POURQUOI.
    """
    erreurs = []

    for strategie in STRATEGIES_WFS:
        try:
            charger_couche_wfs(
                endpoint=endpoint, type_name=type_name, bbox=bbox,
                code_epsg=code_epsg, version=version, timeout=timeout,
                taille_page=1, max_pages=1,          # 1 entité suffit pour tester
                format_sortie=strategie["format_sortie"],
                avec_srsname=strategie["avec_srsname"],
                bbox_avec_crs=strategie["bbox_avec_crs"],
            )
            print(f"   ↳ dialecte retenu : {strategie['nom']}")
            return strategie, erreurs

        except Exception as e:
            erreurs.append(f"{strategie['nom']} → {str(e)[:150]}")

    return None, erreurs


def diagnostiquer_wfs(endpoint, timeout=60):
    """
    Interroge le GetCapabilities d'un service et résume ce qu'il propose.

    À lancer manuellement quand un service refuse toutes les stratégies :
    affiche les versions supportées, les formats de sortie disponibles et
    les premiers noms de couches — de quoi corriger un catalogue erroné.
    """
    print(f"\n── Diagnostic du service {endpoint} ──")
    try:
        r = requests.get(endpoint,
                         params={"SERVICE": "WFS", "REQUEST": "GetCapabilities"},
                         timeout=timeout)
        r.raise_for_status()
        texte = r.content.decode("utf-8", errors="replace")

        versions = sorted(set(re.findall(r'version="([\d.]+)"', texte)))
        print(f"   Versions annoncées : {versions or 'non détectées'}")

        formats = sorted(set(re.findall(
            r"<(?:ows:)?Value>(application/[^<]+|GML\d?|[a-zA-Z]*GML[^<]*)</(?:ows:)?Value>",
            texte)))
        print(f"   Formats de sortie  : {formats[:10] or 'non détectés'}")

        noms = re.findall(r"<(?:wfs:)?Name>([^<]+)</(?:wfs:)?Name>", texte)
        print(f"   Couches ({len(noms)} au total), 15 premières :")
        for n in noms[:15]:
            print(f"      – {n}")

    except Exception as e:
        print(f"   ⚠️  Diagnostic impossible : {e}")


# ═══════════════════════════════════════════════════════════════════
# 3. FONCTION PRINCIPALE : CHARGER UN LOT DE COUCHES D'UNE API
# ═══════════════════════════════════════════════════════════════════

def appel_api(nom_api, endpoint, couches, emprise,
              code_epsg=2154, version="2.0.0",
              format_sortie="application/json",
              on_progress=None, warnings_liste=None):
    """
    Charge une liste de couches depuis un service WFS, filtrées sur l'emprise.

    C'est la fonction à appeler depuis le script principal. Elle remplace
    les trois blocs BD TOPO / INPN / IGN, qui faisaient la même chose de
    trois façons différentes (dont deux cassées).

    Paramètres
    ----------
    nom_api : str
        Nom lisible du service, ex. "API BD TOPO". Sert aux messages
        et à la clé du dictionnaire de statuts.
    endpoint : str
        URL de base du service WFS.
    couches : list[tuple]
        Liste de tuples à 3 éléments :
            (nom_technique_wfs, nom_variable_python, label_metier)
        ex. ("BDTOPO_V3:cours_d_eau", "gdf_API_BDTOPO_cours_eau", "Cours d'eau")
    emprise : GeoDataFrame
        Emprise de travail (tampon appliqué). Sert à calculer la bbox.
    code_epsg : int
        CRS d'interrogation. 2154 par défaut (pas d'ambiguïté d'axes).
    version, format_sortie :
        Voir charger_couche_wfs().
    on_progress : callable ou None
        Fonction appelée après chaque couche, avec le label en argument.
        Permet de brancher la barre de progression Tkinter sans que ce
        module dépende de Tkinter.
    warnings_liste : list ou None
        Si fournie, les avertissements y sont ajoutés (_WARNINGS_SPRINGE).

    Retour
    ------
    tuple (resultats, statut)
        resultats : dict {nom_variable_python: GeoDataFrame}
                    Seules les couches chargées avec succès y figurent.
        statut    : dict au format attendu par generer_rapport, soit
                    {"ok": bool, "couches": {label: bool}, "erreur": str|None}
    """

    print(f"\n── {nom_api} : chargement de {len(couches)} couche(s) ──")

    resultats = {}
    statut_couches = {}
    erreur_globale = None

    # La bbox est calculée UNE SEULE FOIS pour toutes les couches.
    # Si elle échoue (emprise vide), inutile d'appeler le serveur.
    try:
        bbox = bbox_pour_api(emprise, code_epsg)
        print(f"   Emprise transmise (EPSG:{code_epsg}) : "
              f"{bbox[0]:.0f}, {bbox[1]:.0f} → {bbox[2]:.0f}, {bbox[3]:.0f}")
    except Exception as e:
        erreur_globale = str(e)
        print(f"   ❌ {nom_api} : bbox incalculable — {e}")
        if warnings_liste is not None:
            warnings_liste.append(f"{nom_api} : bbox incalculable — {str(e)[:100]}")
        return {}, {"ok": False, "couches": {}, "erreur": erreur_globale}

    # ── Détection du dialecte accepté par ce serveur ────────────────
    # On teste les combinaisons de paramètres sur la PREMIÈRE couche
    # seulement, puis on applique le résultat à toutes les autres.
    strategie, erreurs_test = trouver_strategie(
        endpoint, couches[0][0], bbox, code_epsg, version
    )

    if strategie is None:
        # Aucune combinaison ne passe : inutile de tenter les 14 couches.
        # On affiche les vraies erreurs du serveur, pas des octets bruts.
        print(f"   ❌ {nom_api} : le serveur refuse toutes les combinaisons testées.")
        for err in erreurs_test:
            print(f"      – {err}")
        print(f"   ↳ lancer appel_api.diagnostiquer_wfs('{endpoint}') "
              f"pour voir ce que le service propose réellement.")
        if warnings_liste is not None:
            warnings_liste.append(
                f"{nom_api} : service injoignable ou incompatible — {erreurs_test[0][:150]}"
            )
        return {}, {"ok": False,
                    "couches": {lab: False for _, _, lab in couches},
                    "erreur": erreurs_test[0][:200] if erreurs_test else "inconnu"}

    # Boucle sur les couches. Chaque échec est isolé : une couche
    # indisponible ne doit pas empêcher les autres de se charger.
    for type_name, var_name, label in couches:
        try:
            gdf = charger_couche_wfs(
                endpoint=endpoint,
                type_name=type_name,
                bbox=bbox,
                code_epsg=code_epsg,
                version=version,
                format_sortie=strategie["format_sortie"],
                avec_srsname=strategie["avec_srsname"],
                bbox_avec_crs=strategie["bbox_avec_crs"],
            )

            # Reprojection en Lambert 93 si le serveur a répondu autrement.
            if gdf.crs and gdf.crs.to_epsg() != 2154:
                gdf = gdf.to_crs(epsg=2154)

            resultats[var_name] = gdf
            statut_couches[label] = True
            print(f"   ✔️  {label:35s} {len(gdf):>6d} entités")

            # Une couche vide n'est pas une erreur, mais mérite d'être
            # signalée : soit la zone n'en contient pas, soit le filtre
            # spatial est trop restrictif.
            if len(gdf) == 0 and warnings_liste is not None:
                warnings_liste.append(
                    f"{nom_api} — {label} : 0 entité dans l'emprise"
                )

        except Exception as e:
            statut_couches[label] = False
            message = f"{nom_api} — {label} : échec — {str(e)[:120]}"
            print(f"   ⚠️  {message}")
            if warnings_liste is not None:
                warnings_liste.append(message)

        # Avancement de la barre de progression, si branchée.
        if on_progress is not None:
            on_progress(label)

    # Le service est considéré « ok » si au moins une couche est passée.
    nb_ok = sum(statut_couches.values())
    statut = {
        "ok": nb_ok > 0,
        "couches": statut_couches,
        "erreur": None if nb_ok > 0 else "aucune couche chargée",
    }
    print(f"   → {nb_ok}/{len(couches)} couche(s) chargée(s)")

    return resultats, statut


# ═══════════════════════════════════════════════════════════════════
# 4. CAS PARTICULIER : API REST NON-WFS (ponts SNCF)
# ═══════════════════════════════════════════════════════════════════

def appel_api_geojson(nom_api, url, emprise, warnings_liste=None):
    """
    Charge une API REST renvoyant directement du GeoJSON (pas un WFS),
    puis DÉCOUPE le résultat sur l'emprise.

    Cas d'usage : data.sncf.com, qui n'expose qu'un export national
    complet, sans paramètre de filtrage spatial. On ne peut donc pas
    alléger le téléchargement — mais on peut au moins éviter de traîner
    la France entière dans la suite des calculs.

    Retour
    ------
    tuple (GeoDataFrame|None, statut)
    """
    print(f"\n── {nom_api} : téléchargement ──")

    try:
        reponse = requests.get(url, timeout=180)
        reponse.raise_for_status()
        gdf = gpd.read_file(io.BytesIO(reponse.content))

        if gdf.crs and gdf.crs.to_epsg() != 2154:
            gdf = gdf.to_crs(epsg=2154)

        nb_avant = len(gdf)

        # Découpage sur l'emprise. On utilise l'intersection des index
        # spatiaux (sjoin "within"/"intersects") plutôt que clip(), plus
        # rapide et suffisant pour des points.
        gdf = gdf[gdf.intersects(emprise.union_all())]

        print(f"   ✔️  {nom_api} : {nb_avant} entités → {len(gdf)} dans l'emprise")
        return gdf, {"ok": True, "couches": {nom_api: True}, "erreur": None}

    except Exception as e:
        message = f"{nom_api} : chargement échoué — {str(e)[:120]}"
        print(f"   ⚠️  {message}")
        if warnings_liste is not None:
            warnings_liste.append(message)
        return None, {"ok": False, "couches": {nom_api: False}, "erreur": str(e)}
