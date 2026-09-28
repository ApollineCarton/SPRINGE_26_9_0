# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

"""
Fonction de chargement des chemins d'accès vers les données contenues dans des fichiers

═══════════════════════════════════════════════════════════════════
Fonction "check_path"
Date : 2026-01-16
Objectif : Vérifier que les couches de données existent et sont correctement chargées
═══════════════════════════════════════════════════════════════════

Vérifie l'existence d'un fichier ou d'un dossier avant de l'utiliser
Evite les erreurs de chargement dues à des chemins d'accès tronqués

Arguments :
    path : str - Chemin du fichier/dossier à vérifier
    nom_donnee : str - Nom descriptifi pour l'affichage
    is_dir : bool - True si c'est un dossier, False si c'est un fichier
Retourne :
    bool - True si le chemin existe, False sinon
"""
from pathlib import Path

def check_path(path, nom_donnee, is_dir=False):
    path_obj = Path(path)  # conversion de la chaine en objet Path (pour gestion multi plateforme)

# vérifier selon le type (fichier ou dossier)
    if is_dir:
        existe = path_obj.is_dir() # retourne True si c'est un dossier existant
    else:
        existe = path_obj.is_file() # retourne True si c'est un fichier existant

# afficher le résultat
    if existe:
        print(f" {nom_donnee} : Chemin d'accès OK")
    else:
        print(f" {nom_donnee} : Chemin d'accès INTROUVABLE")
        print(f" Chemin recherché : {path}")
    return existe
