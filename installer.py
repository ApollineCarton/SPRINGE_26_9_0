# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

# =======================================================================
# SPRINGE - Script d'installation des dépendances
# =======================================================================
# ▶ À lancer UNE SEULE FOIS avant de lancer run.py
# ▶ Dans Spyder : ouvrir ce fichier et appuyer sur Run (F5)
# =======================================================================
 
import subprocess
import sys
from pathlib import Path
#pour les input utilisateur :
import tkinter as tk
print("librairie tk ok")
from tkinter import simpledialog, messagebox, filedialog
print("librairie dans tk ok")

 
print("=" * 60)
print("  SPRINGE - Installation des dépendances")
print("=" * 60)
 
# Chemin vers requirements.txt (même dossier que ce script)
requirements = Path(__file__).parent / "requirements.txt"
 
if not requirements.exists():
    print(f"\n❌ Fichier requirements.txt introuvable !")
    print(f"   Chemin attendu : {requirements}")
    print(f"   → Vérifie qu'il est bien dans le même dossier que installer.py")
    sys.exit(1)
 
print(f"\n📦 Fichier trouvé : {requirements}")
print(f"\n⏳ Installation en cours...\n")
 
# Lancement de pip install
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
    capture_output=False  # affiche la progression dans la console
)
 
print("\n" + "=" * 60)
 
if result.returncode == 0:
    print("  ✅ Toutes les librairies sont installées !")
    print("  → Tu peux maintenant lancer run.py")
else:
    print("  ⚠️  Certaines librairies n'ont pas pu être installées.")
    print("  → Lis les messages d'erreur ci-dessus pour identifier le problème.")
    print("  → Pour les librairies géospatiales (geopandas, fiona, shapely),")
    print("    il est parfois nécessaire de passer par conda :")
    print("    conda install -c conda-forge geopandas")
 
print("=" * 60)

# Affichage du résultat dans une vraie fenêtre
# Créer une fenêtre principale cachée
root = tk.Tk()
root.withdraw()
messagebox.showinfo("Résultat",
                    "L'installation est terminée avec succès !\nlancer_SPRINGE' est opérationnel pour lancement")