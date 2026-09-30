# -*- coding: utf-8 -*-
"""
Adaptation du projet QGIS témoin au GeoPackage fictif.

PRINCIPE
--------
Un .qgz est une archive zip contenant le projet (.qgs, du XML) et ses pièces
jointes (ici la base de styles ERnCYG_styles.db). On modifie le .qgs :
  1. sources des couches → GeoPackage fictif posé dans le MÊME dossier que le
     projet (chemin relatif « ./ »), au lieu de ../../02_outputs/… ;
  2. suppression des mentions personnelles (chemins C:/Users/…, noms) ;
  3. noms de couches lisibles (« 01_score_total_seuils » au lieu de
     « SPRINGE_…_copie copie ») ;
  4. table renommée exactement « caracterisation_EEE_par_troncon_espece »,
     nom que cherchent les styles 09 et 10 via aggregate(layer:=…) ;
  5. emprises (vue de la carte, couches, mises en page) recalées sur les
     données fictives, pour que le projet s'ouvre directement dessus.
Puis on reconstruit le .qgz avec les mêmes pièces jointes.
"""

import re
import zipfile
from pathlib import Path

import geopandas as gpd
from lxml import etree
from pyproj import Transformer

DOSSIER = Path("/home/claude/pt")
QGS = DOSSIER / "projet_témoin.qgs"
GPKG = Path("/mnt/user-data/outputs/SPRINGE_version202609_exemple_fictif_20260929.gpkg")
SORTIE = Path("/mnt/user-data/outputs/projet_témoin.qgz")

ANCIEN = "SPRINGE_version202609_apolline_dernier_test_CBNB_20260929"
NOUVEAU = "SPRINGE_version202609_exemple_fictif_20260929"
TABLE = "caracterisation_EEE_par_troncon_espece"

# ─────────────────────────────────────────────────────────────────────
# 1 et 2. REMPLACEMENTS TEXTUELS (avant analyse XML)
# ─────────────────────────────────────────────────────────────────────
txt = QGS.read_text(encoding="utf-8")

# Chemin du GeoPackage : relatif au dossier du projet. Le projet est déjà
# réglé en chemins relatifs (<Absolute>false</Absolute>) : « ./fichier.gpkg »
# signifie « à côté du .qgz ».
txt = txt.replace(f"../../02_outputs/{ANCIEN}.gpkg", f"./{NOUVEAU}.gpkg")

# Chemin ABSOLU résiduel (réglages GPS du projet) : même traitement.
txt = re.sub(r"C:/Users/Apolline/Documents/[^|\"]*?/" + ANCIEN + r"\.gpkg",
             f"./{NOUVEAU}.gpkg", txt)

# Dernier dossier d'export des mises en page : chemin personnel, on le vide.
txt = re.sub(r'(<lastLayoutExportDir type="QString">)[^<]*(</lastLayoutExportDir>)',
             r"\1\2", txt)

# Toutes les autres occurrences du nom (noms de couches, identifiants
# internes, ordre des couches…). Le remplacement étant global, les
# identifiants restent cohérents entre eux dans tout le fichier.
txt = txt.replace(ANCIEN, NOUVEAU)

# Couche orpheline citée dans la légende d'une mise en page (sortie du 13/09,
# absente du projet) : on neutralise simplement son nom.
txt = txt.replace("Apolline_Carton_CBNB_20260913", "exemple_20260913")
txt = txt.replace("Apolline-Carton_CBNB_20260913", "exemple_20260913")

# Auteur du projet (métadonnées) : crédit institutionnel.
txt = txt.replace("<author>Apolline</author>", "<author>OFB – SPRINGE</author>")

# Utilisateur du dernier enregistrement (attributs de la balise <qgis>) :
# QGIS les réécrit à chaque sauvegarde, on les vide pour la version publiée.
txt = txt.replace('saveUser="Apolline"', 'saveUser=""')
txt = txt.replace('saveUserFull="Apolline"', 'saveUserFull=""')

assert "Apolline" not in txt and "C:/Users" not in txt, "mention personnelle restante"

# ─────────────────────────────────────────────────────────────────────
# ANALYSE XML
# ─────────────────────────────────────────────────────────────────────
# resolve_entities=False et strip_cdata=False : on ne touche pas au contenu
# (expressions, CDATA des scripts). Le DOCTYPE « qgis » est conservé.
parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, huge_tree=True)
racine = etree.fromstring(txt.encode("utf-8"), parser)

# ─────────────────────────────────────────────────────────────────────
# 3 et 4. NOMS DE COUCHES
# ─────────────────────────────────────────────────────────────────────
# Chaque couche placée dans un groupe de style prend le nom du groupe.
# Les couches à la racine prennent le nom de leur couche dans le GeoPackage.
noms = {}                                     # id de couche → nouveau nom
arbre = racine.find("layer-tree-group")
for groupe in arbre.findall("layer-tree-group"):
    for couche in groupe.findall("layer-tree-layer"):
        noms[couche.get("id")] = groupe.get("name")

for ml in racine.iter("maplayer"):
    ident = ml.findtext("id")
    source = ml.findtext("datasource") or ""
    if ident not in noms and "layername=" in source:
        noms[ident] = source.split("layername=")[1]   # nom réel dans le .gpkg

# Application : balise <layername> de la couche + attribut name de TOUS les
# nœuds d'arbre qui la citent (panneau Couches, légendes des mises en page).
for ml in racine.iter("maplayer"):
    ident = ml.findtext("id")
    if ident in noms:
        ml.find("layername").text = noms[ident]
for noeud in racine.iter("layer-tree-layer"):
    if noeud.get("id") in noms:
        noeud.set("name", noms[noeud.get("id")])

# ─────────────────────────────────────────────────────────────────────
# 5. EMPRISES
# ─────────────────────────────────────────────────────────────────────
# Emprise réelle de chaque couche du GeoPackage fictif, en Lambert-93 et en
# WGS84 (QGIS stocke les deux dans le projet).
vers_wgs = Transformer.from_crs(2154, 4326, always_xy=True)
emprises = {}
for couche in (NOUVEAU, "caracterisation_population"):
    xmin, ymin, xmax, ymax = gpd.read_file(GPKG, layer=couche).total_bounds
    lo1, la1 = vers_wgs.transform(xmin, ymin)
    lo2, la2 = vers_wgs.transform(xmax, ymax)
    emprises[couche] = ((xmin, ymin, xmax, ymax), (lo1, la1, lo2, la2))


def ecrire_emprise(elem, valeurs):
    """Écrit xmin, ymin, xmax, ymax dans un élément <extent> ou <wgs84extent>."""
    for nom, v in zip(("xmin", "ymin", "xmax", "ymax"), valeurs):
        enfant = elem.find(nom)
        if enfant is not None:
            enfant.text = repr(float(v))


for ml in racine.iter("maplayer"):
    source = ml.findtext("datasource") or ""
    nom_gpkg = source.split("layername=")[1] if "layername=" in source else None
    if nom_gpkg in emprises:
        l93, wgs = emprises[nom_gpkg]
        if ml.find("extent") is not None:
            ecrire_emprise(ml.find("extent"), l93)
        if ml.find("wgs84extent") is not None:
            ecrire_emprise(ml.find("wgs84extent"), wgs)

# Vue globale : emprise des tronçons + marge de 10 %.
xmin, ymin, xmax, ymax = emprises[NOUVEAU][0]
mx, my = (xmax - xmin) * 0.10, (ymax - ymin) * 0.10
vue = (xmin - mx, ymin - my, xmax + mx, ymax + my)
ecrire_emprise(racine.find("mapcanvas").find("extent"), vue)

# Cartes des mises en page : même centre, en respectant les proportions du
# cadre (largeur / hauteur de l'élément carte), sinon QGIS déformerait.
cx, cy = (vue[0] + vue[2]) / 2, (vue[1] + vue[3]) / 2
for item in racine.iter("LayoutItem"):
    ext = item.find("Extent")
    if ext is None:
        continue
    larg, haut = (float(v) for v in item.get("size").split(",")[:2])
    ratio = larg / haut
    w, h = vue[2] - vue[0], vue[3] - vue[1]
    if w / h < ratio:
        w = h * ratio
    else:
        h = w / ratio
    ext.set("xmin", repr(cx - w / 2)); ext.set("xmax", repr(cx + w / 2))
    ext.set("ymin", repr(cy - h / 2)); ext.set("ymax", repr(cy + h / 2))

# ─────────────────────────────────────────────────────────────────────
# ÉCRITURE ET RECONSTRUCTION DU .qgz
# ─────────────────────────────────────────────────────────────────────
doctype = re.match(r"(<!DOCTYPE[^>]*>)", txt.lstrip()).group(1)
corps = etree.tostring(racine, encoding="unicode")
QGS.write_text(doctype + "\n" + corps + "\n", encoding="utf-8")

with zipfile.ZipFile(SORTIE, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(QGS, QGS.name)
    z.write(DOSSIER / "ERnCYG_styles.db", "ERnCYG_styles.db")

print("Couches renommées :")
for ident, nom in sorted(noms.items(), key=lambda x: x[1]):
    print(f"   {nom}")
print(f"✔ {SORTIE}")
