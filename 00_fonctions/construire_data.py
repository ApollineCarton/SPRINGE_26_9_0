# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Module "construire_data"
Construit le dictionnaire DATA : le registre central des couches SIG,
organisé par enjeu (MS / N / P / COMMUN) puis par indicateur.
═══════════════════════════════════════════════════════════════════════════

RÔLE DE DATA
─────────────────────────────────────────────────────────────────
DATA est le catalogue qui dit à chaque indicateur quelles couches il
doit croiser avec les tronçons. Sa signature :

    DATA[enjeu][indicateur][nom_couche] = {
        "gdf"        : le GeoDataFrame,
        "type"       : "ponctuelle | linéaire | polygone",
        "source"     : d'où vient la donnée,
        "description": texte lisible pour le rapport,
    }

POURQUOI ESPACE_NOMS EN ARGUMENT
─────────────────────────────────────────────────────────────────
get_gdf() cherche les GeoDataFrames par leur NOM de variable
(« gdf_carrefours »…). Ces variables vivent dans l'espace de noms du
SCRIPT PRINCIPAL, pas dans celui de ce module.

Si on appelait globals() ici, on obtiendrait l'espace de noms de
construire_data.py — qui ne contient aucune couche. Le script principal
doit donc passer son propre globals() en argument. C'est le même
mécanisme que diagnostic_couches.diagnostic_variables().
═══════════════════════════════════════════════════════════════════════════
"""


# Notes de développement remontées par la dernière construction.
NOTES_TRAVAUX = []


def construire_data(espace_noms, couches_supp_chargees=None, est_dir=True,
                    warnings_liste=None):
    """
    Construit et retourne le dictionnaire DATA.

    Paramètres
    ----------
    espace_noms : dict
        globals() du script principal, où vivent les variables gdf_*.
    couches_supp_chargees : dict ou None
        {"MS1": [noms_variables], "MS2": [...], "MS3": [...]} — couches
        ajoutées manuellement par l'utilisateur via la fenêtre.
    est_dir : bool
        True si l'utilisateur est gestionnaire d'une DIR.
    warnings_liste : list ou None
        Liste où tracer les couches manquantes (_WARNINGS_SPRINGE).

    Retour
    ------
    dict : le catalogue DATA complet (non nettoyé — appeler ensuite
           diagnostic_couches.nettoyer_data pour retirer les absentes).
    """

    # Valeurs par défaut : évite un TypeError si l'appelant ne passe rien.
    if couches_supp_chargees is None:
        couches_supp_chargees = {"MS1": [], "MS2": [], "MS3": []}

    # Notes de développement rencontrées pendant la construction.
    # Exposées en attribut de module pour que le script principal
    # puisse les afficher sans que ce module dépende de travaux.py.
    notes_travaux = []

    # Alias locaux : le corps du dictionnaire ci-dessous utilise ces noms.
    _couches_supp_chargees = couches_supp_chargees
    _est_dir = est_dir

    def get_gdf(nom_variable):
        """
        Récupère un GeoDataFrame par son nom dans l'espace de noms fourni.
        Retourne None si la couche est absente — nettoyer_data() se
        chargera ensuite de retirer l'entrée du catalogue.
        """
        gdf = espace_noms.get(nom_variable)
        if gdf is None:
            print(f"⚠️  Couche '{nom_variable}' non trouvée → ignorée")
            if warnings_liste is not None:
                warnings_liste.append(f"Couche '{nom_variable}' non fournie")
        return gdf

    DATA = {
        "COMMUN":{},
        "MS": {},
        "N": {},
        "P": {}
    }

    # Contenu de MS - indicateurs
    # MS1 : visibilité critique
    DATA["MS"]["MS1"] = {
        "carrefours" : {
            "gdf": get_gdf("gdf_carrefours"),
            "type": "ponctuelle",
            "source": "SI Route",
            "description": "Est considéré comme carrefour toute intersection entre le réseau DIR et une voie quelconque dès lors qu'un transfert de véhicules est possible.\nCela concerne les carrefours plans, les giratoires et dispositifs d'échanges.\nQuand l'intersection concerne deux routes du réseau DIR, on aura 2 objets carrefours"
        },
        "echangeurs" : {
            "gdf": get_gdf("gdf_echangeurs"),
            "type": "ponctuelle",
            "source": "SI Route",
            "description": "Couvre les échangeurs présents sur les autoroutes concédées. Un échangeur peut figurer plusieurs fois car il apparaît sur chaque autoroute de l'échangeur (cas des bifurcations)"
        },
        "passages à niveaux" : {
            "gdf": get_gdf("gdf_pn"),
            "type": "ponctuelle",
            "source": "SI Route",
            "description": "Passages à niveaux entre le réseau routier national et des voies ferroviaires"
        },
    }
    # MS1b : trafic routier
    DATA["MS"]["MS1b"] = {
        "tmja": {
            "gdf": get_gdf("gdf_tmja"),
            "type": "point",
            "source": "SI Route",
            "description": "Trafic moyen journalier annuel. Trafic dans les deux sens, tous véhicules confondus."
        }
    }
    # MS2 : risque sanitaire
    DATA["MS"]["MS2"] = {

        "habitations" : {
            "gdf": get_gdf("gdf_API_IGN_habitation_bdcarto"),
            "type": "polygone",
            "source": "api ign",
            "description": "les habitations de BDcarto"
        },
        "zones_activites" : {
            "gdf": get_gdf("gdf_API_IGN_zone_activite_interet_bdcarto"),
            "type": "polygone",
            "source": "api ign",
            "description": "les zones d'activités de BDcarto"
        }, 
        "gares" : {
            "gdf": get_gdf("gdf_API_IGN_gares"),
            "type" : "ponctuelle",
            "source": "api ign",
            "description":"les gares"
        },
        "gares2": {
            "gdf": get_gdf("gdf_API_IGN_gares2"),
            "type" : "ponctuelle",
            "source": "api ign",
            "description": "les gares 2"
        },
    
        "aires_de_repos" : {
            "gdf": get_gdf("gdf_airesderepos"),
            "type": "ponctuelle",
            "source": "SI Route",
            "description": (
                "Aires de repos ou de services du réseau routier. "
                "Zones fréquentées par le public, pertinentes pour le risque sanitaire."
            )
        }

    }
    #MS3 : patrimoine routier
    DATA["MS"]["MS3"] = {
        "écrans acoustiques": {
            "gdf": get_gdf("gdf_ecransAcoustiques"),
            "type": "linéaire",
            "source": "SI Route",
            "description": "Differents types d'écrans anti-bruit, caractérisés par leur longeur, leur hauteur et leur nature"
        },
        "murs consédés": {
            "gdf": get_gdf("gdf_mursConsedes"),
            "type": "linéaire",
            "source": "SI Route",
            "description": "Comprend tous les murs de soutènement de hauteur supérieur ou égale à 2m"
        },
        "ponts consédés": {
            "gdf": get_gdf("gdf_pontsConsedes"),
            "type": "linéaire",
            "source": "SI Route",
            "description": "Ensemble des ouvrages d'art de plus de 2 mètres d'ouverture du DPAC (y compris les ouvrages d'autres gestionnaires). Un pont correspond à un tablier quelque soit la typologie des appuis (un ouvrage de franchissement peut donc être constitué de plusieurs ponts"
        },
   
        "passages_faune": {
            "gdf": get_gdf("gdf_paf"),
            "type": "ponctuelle",
            "source": "Geonature, dossiers Apolline",
            "description": "Passages à faune, géonature"
        }, #quand on affiche sur QGIS il y a ponctuel, linéaire et polygones !!!

        "ponts_sncf_api": {
            "gdf": get_gdf("gdf_API_ponts_sncf"),
            "type": "ponctuelle",
            "source": "API data.sncf.com",
            "description": "Ponts SNCF croisant le réseau routier issu de l'API SNCF"
        },
    
        "ponts" : {
            "gdf": get_gdf("gdf_API_ponts_sncf"),
            "type" : "ponctuelle",
            "source": "api ign",
            "description": "les gares 2"
        },
    
        "murs_non_concedes" : {
            "gdf": get_gdf("gdf_murs"),
            "type": "linéaire",
            "source": "SI Route",
            "description": (
                "Murs de soutènement du réseau routier national non concédé (RRNnc). "
                "Complète les murs concédés déjà présents."
            )
        },
    
        "ponts_non_concedes" : {
            "gdf": get_gdf("gdf_ponts"),
            "type": "linéaire",
            "source": "SI Route",
            "description": (
                "Ouvrages d'art (ponts) du réseau routier national non concédé (RRNnc). "
                "Complète les ponts concédés déjà présents."
            )
        }
    
    
    }

    # Contenu de N - Indicateurs

    #N1 : Proximité et menace des EEE sur zones naturelles sensibles 
    DATA["N"]["N1"] = {

        # Niveau 1 : protection forte (catégorie IUCN I-III) -> reconnaissance selon le décret n]2022-527 du 12 avril 2022
        "Niv1": {
            "Réserves_Intégrales_Parcs_Nationaux": {
                "gdf": get_gdf("gdf_API_INPN_RIPN"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves intégrales de parcs nationaux, libre évolution, aucune activité humaine autorisée, catégorie Ia UICN"
            },

            "Parcs Nationaux": {
                "gdf": get_gdf("gdf_API_INPN_Parcs_Nationaux"),
                "type": "polygone",
                "source": "INPN API",
                "description": "périmètre des parcs nationaux"
            },
            
            "RNN": {
                "gdf": get_gdf("gdf_API_INPN_RNN"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves Naturelles Nationales"
            },

            "perimtre_RNN": {
                "gdf": get_gdf("gdf_API_INPN_Perimetre_RNN"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Périmètre des Réserves Naturelles Nationales"
            },
        
            "RNR": {
                "gdf": get_gdf("gdf_API_INPN_RNR"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves Naturelles Régionales"
            },

            "APB": {
                "gdf": get_gdf("gdf_API_INPN_ArreteProtectionBiotope"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Arrêté de protection biotope"
            },

            "APHN":{
                 "gdf": get_gdf("gdf_API_INPN_ArreteProtectionHabNat"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Arrêté de protection biotope"
            },
              
            "Réserves_Biologiques": {
                "gdf": get_gdf("gdf_API_INPN_Reserves_Biologiques"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves biologiques intégrales RBI et dirigées RBD, catégorie Ia-IV UICN"
            },
        },

        "Niv2" : {
            "Conservatoire du Littoral" : {
                "gdf": get_gdf("gdf_API_INPN_ConservatoireLittoral"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites du Conservatoire du Littoral"
            },

            "Conservatoire d'espaces naturels" : {
                "gdf": get_gdf("gdf_API_INPN_CEN"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites du Conservatoire d'espaces naturels"
            }
        },
    
        "Niv3" : {
    
            "N2000_SIC": {
                "gdf": get_gdf("gdf_API_INPN_SIC"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites d’Importance Communautaire (SIC)"
            },
    
            "N2000_ZPS": {
                "gdf": get_gdf("gdf_API_INPN_ZPS"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Zones de Protection Spéciale (ZPS)"
            },

            "RAMSAR": {
                "gdf": get_gdf("gdf_API_INPN_RAMSAR"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites RAMSAR"
            }
        },
    
        "Niv4": {
            "ZICO" : {
                "gdf": get_gdf("gdf_API_INPN_ZICO"),
                "type": "polygone",
                "source": "INPN API",
                "description": " Zones d'Importance pour la Conservation des Oiseaux"
            }
        }
    }
    #N2 : PAs besoin de données SIG - Potentiel de transformation/potentiel invasif des habitats adjacents 

    #P1 : pas besoin de données SIG - Potentiel reproductif de l'EEE 

    #P2 : Proximité des vecteurs de dispersion des EEE en présence 
    # Note de développement remontée au script principal, qui
    # l'affichera via travaux(). On évite ainsi une dépendance de
    # ce module de données vers un module d'affichage.
    notes_travaux.append("trouver les voies ferrées - P2")
        
    DATA["P"]["P2"] = {

        # ── Vecteur hydrochore : dispersion par l'eau ──────────────────────
        # Cours d'eau → les propagules emportées par le courant colonisent
        # les berges en aval. Vecteur très efficace, surtout pour Reynoutria.
        "Hydrochorie": {
            "cours_eau": {
                "gdf"        : get_gdf("gdf_API_BDTOPO_cours_eau"),  # BD TOPO via API IGN
                "type"       : "linéaire",
                "source"     : "BD TOPO v3 — API Géoplateforme IGN",
                "description": "Cours d'eau de la BD TOPO v3. "
                               "Utilisés avec un tampon de 50m pour détecter "
                               "la proximité hydraulique avec les tronçons routiers."
            }
        },

        # ── Vecteurs anthropochores aggravants : dispersion par l'humain ───
        # Carrefours, échangeurs : points de concentration et transfert de véhicules
        #   → forte probabilité de transport de propagules entre réseaux.
        # Voies ferrées : engins de maintenance, ballast, vent des trains.
        "Anthropochorie": {
            "carrefours": {
                "gdf"        : get_gdf("gdf_carrefours"),
                "type"       : "ponctuelle",
                "source"     : "SI Route",
                "description": "Intersections entre le réseau DIR et toute voie "
                               "avec possibilité de transfert de véhicules "
                               "(carrefours plans, giratoires, dispositifs d'échange)."
            },
            "echangeurs": {
                "gdf"        : get_gdf("gdf_echangeurs"),
                "type"       : "ponctuelle",
                "source"     : "SI Route",
                "description": "Échangeurs sur autoroutes concédées. "
                               "Un échangeur peut figurer plusieurs fois "
                               "(bifurcations sur plusieurs autoroutes)."
            },
            "voies_ferrees": {
                "gdf"        : get_gdf("gdf_API_BDTOPO_voie_ferree"),  # ⭐ NOUVEAU — BD TOPO
                "type"       : "linéaire",
                "source"     : "BD TOPO v3 — API Géoplateforme IGN",
                "description": "Tronçons de voies ferrées de la BD TOPO v3. "
                               "Les abords ferroviaires sont des vecteurs de dispersion "
                               "via les engins de maintenance et le vent des trains."
            }
        }
    }

    # P3 : mêmes données que N1, mais on copie colle pour pouvoir appeler differement les niveaux !! Niv1_tamponP3
    DATA["P"]["P3"] = {

        # Niveau 1 : protection forte (catégorie IUCN I-III) -> reconnaissance selon le décret n]2022-527 du 12 avril 2022
        "Niv1_tamponP3": {
            "Réserves_Intégrales_Parcs_Nationaux": {
                "gdf": get_gdf("gdf_API_INPN_RIPN"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves intégrales de parcs nationaux, libre évolution, aucune activité humaine autorisée, catégorie Ia UICN"
            },

            "Parcs Nationaux": {
                "gdf": get_gdf("gdf_API_INPN_Parcs_Nationaux"),
                "type": "polygone",
                "source": "INPN API",
                "description": "périmètre des parcs nationaux"
            },
            
            "RNN": {
                "gdf": get_gdf("gdf_API_INPN_RNN"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves Naturelles Nationales"
            },

            "perimtre_RNN": {
                "gdf": get_gdf("gdf_API_INPN_Perimetre_RNN"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Périmètre des Réserves Naturelles Nationales"
            },
        
            "RNR": {
                "gdf": get_gdf("gdf_API_INPN_RNR"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves Naturelles Régionales"
            },

            "APB": {
                "gdf": get_gdf("gdf_API_INPN_ArreteProtectionBiotope"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Arrêté de protection biotope"
            },

            "APHN":{
                 "gdf": get_gdf("gdf_API_INPN_ArreteProtectionHabNat"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Arrêté de protection biotope"
            },
              
            "Réserves_Biologiques": {
                "gdf": get_gdf("gdf_API_INPN_Reserves_Biologiques"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Réserves biologiques intégrales RBI et dirigées RBD, catégorie Ia-IV UICN"
            },
        },

        "Niv2_tamponP3" : {
            "Conservatoire du Littoral" : {
                "gdf": get_gdf("gdf_API_INPN_ConservatoireLittoral") ,
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites du Conservatoire du Littoral"
            },

            "Conservatoire d'espaces naturels" : {
                "gdf": get_gdf("gdf_API_INPN_CEN")  ,
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites du Conservatoire d'espaces naturels"
            }
        },
    
        "Niv3_tamponP3" : {
    
            "N2000_SIC": {
                "gdf": get_gdf("gdf_API_INPN_SIC"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites d’Importance Communautaire (SIC)"
            },
    
            "N2000_ZPS": {
                "gdf": get_gdf("gdf_API_INPN_ZPS"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Zones de Protection Spéciale (ZPS)"
            },

            "RAMSAR": {
                "gdf": get_gdf("gdf_API_INPN_RAMSAR"),
                "type": "polygone",
                "source": "INPN API",
                "description": "Sites RAMSAR"
            }
        },
    
        "Niv4_tamponP3": {
            "ZICO" : {
                "gdf": get_gdf("gdf_API_INPN_ZICO"),
                "type": "polygone",
                "source": "INPN API",
                "description": " Zones d'Importance pour la Conservation des Oiseaux"
            }
        }
    }

    # P4 : Pas besoin de données SIG : Risque de colonisation des tronçons adjacents à enjeux 

    # --- COUCHES SUPPLÉMENTAIRES (ajoutées dynamiquement par l'utilisateur) -
    # On les injecte dans le DATA dict du bon indicateur.
    # Elles reçoivent un nom générique "supplementaire_N".

    for bloc, data_key in [("MS1", "MS1"), ("MS2", "MS2"), ("MS3", "MS3")]:
        for var_name in _couches_supp_chargees[bloc]:
            gdf = globals().get(var_name)
            if gdf is not None:
                DATA["MS"][data_key][var_name] = {
                    "gdf": gdf,
                    "type": "auto",  # la géométrie est détectée par sjoin
                    "source": "utilisateur",
                    "description": f"Couche supplémentaire ajoutée par l'utilisateur ({var_name})"
                }
            
    ''' signature de couche :
    {
        "gdf": nom du GeoDataFrame,
        "type": "ponctuelle | linéaire | polygone",
        "source": "...",
        "description": "..."
    }
    '''

    # On expose les notes au niveau du module : le script principal
    # fait « for n in construire_data.NOTES_TRAVAUX: travaux.travaux(n) ».
    global NOTES_TRAVAUX
    NOTES_TRAVAUX = notes_travaux

    return DATA
