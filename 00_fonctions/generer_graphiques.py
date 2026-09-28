# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 14:42:38 2026

@author: apolline.carton
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def generer_graphiques(df_scoring, gdf_EEE, colonne_id, output_dir):
    """
    Génère des graphiques PNG dans un sous-dossier /graphiques
    """

    dossier_graph = Path(output_dir) / "graphiques"
    dossier_graph.mkdir(exist_ok=True)

    # ============================
    # 1. Scatter + stats
    # ============================
    colonnes_scores = [c for c in df_scoring.columns if "_impact" in c]

    for col in colonnes_scores:
        data = df_scoring[col].dropna()

        plt.figure()
        plt.scatter(range(len(data)), data)

        moyenne = data.mean()
        mediane = data.median()
        max_theorique = data.max()  # ou valeur fixée si connue

        plt.axhline(moyenne, linestyle="--", label=f"moyenne={moyenne:.2f}")
        plt.axhline(mediane, linestyle=":", label=f"mediane={mediane:.2f}")
        plt.axhline(max_theorique, linestyle="-", label=f"max={max_theorique}")

        plt.title(f"{col} - distribution")
        plt.legend()

        plt.savefig(dossier_graph / f"{col}_scatter.png")
        plt.close()

    # ============================
    # 2. Histogrammes
    # ============================
    for col in colonnes_scores:
        data = df_scoring[col].dropna()

        plt.figure()
        plt.hist(data, bins=10)

        plt.title(f"{col} - histogramme")
        plt.savefig(dossier_graph / f"{col}_hist.png")
        plt.close()

    # ============================
    # 3. % tronçons avec EEE
    # ============================
    if colonne_id in gdf_EEE.columns:
        total = len(df_scoring)
        avec = (gdf_EEE[colonne_id] != 'NA').sum()
        sans = (gdf_EEE[colonne_id] == 'NA').sum()

        plt.figure()
        plt.bar(["avec EEE", "sans EEE"], [avec, sans])

        plt.title("Présence EEE sur tronçons")
        plt.savefig(dossier_graph / "EEE_presence.png")
        plt.close()

    # ============================
    # 4. Contribution enjeux
    # ============================
    cols_enjeux = ["score_enjeu_MS", "score_enjeu_N", "score_enjeu_P"]

    valeurs = []
    labels = []

    for col in cols_enjeux:
        if col in df_scoring.columns:
            valeurs.append(df_scoring[col].mean())
            labels.append(col)

    if valeurs:
        plt.figure()
        plt.bar(labels, valeurs)
        plt.title("Contribution moyenne des enjeux")
        plt.savefig(dossier_graph / "enjeux.png")
        plt.close()

    # ============================
    # 5. Top tronçons
    # ============================
    if "score_troncon_final" in df_scoring.columns:
        top = df_scoring.nlargest(10, "score_troncon_final")

        plt.figure()
        plt.bar(range(len(top)), top["score_troncon_final"])
        plt.title("Top 10 tronçons prioritaires")
        plt.savefig(dossier_graph / "top_troncons.png")
        plt.close()

    print(f"📊 Graphiques générés dans : {dossier_graph}")