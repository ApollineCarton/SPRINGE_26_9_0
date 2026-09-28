<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!--
  ════════════════════════════════════════════════════════════════════════
  SPRINGE — Style 09 : compacité la plus forte observée
  ════════════════════════════════════════════════════════════════════════
  Couche cible : couche cartographique des tronçons du GeoPackage SPRINGE.
  Testé sur    : QGIS 3.34.4 (chargement, classement, rendu).
                 Chargement vérifié par l'utilisatrice sur 3.44.11 pour
                 les styles 00, 01 et 05 ; à revérifier pour celui-ci.

  Question : « Le tronçon porte-t-il au moins une population continue, ou
              seulement des taches, ou seulement des individus isolés ? »
  Compacité = structure interne d'une population (protocole : isolés,
  taches discontinues, continue). Appréciation visuelle ordinale, PAS une
  densité numérique.

  PRÉREQUIS : la table « caracterisation_EEE_par_troncon_espece » du même
  GeoPackage doit être chargée dans le projet SOUS CE NOM EXACT
  (Couche > Ajouter une couche > Couche vecteur, choisir la table). Si elle
  manque ou porte un autre nom, tous les tronçons observés tombent dans la
  classe « non calculable ».

  Calcul : pour chaque tronçon, l'expression aggregate() additionne, sur les
  lignes de la table dont "id_troncon" égale le "nom_plo_fi" du tronçon
  (attribute(@parent, ...) = champ du tronçon en cours de dessin), le
  comptage demandé toutes espèces confondues. coalesce(..., 0) remplace un
  résultat vide par 0. On n'additionne que des COMPTAGES de populations :
  chaque population appartient à une seule espèce, la somme est donc exacte.

  Classes exclusives, de la plus forte à la plus faible :
    continue : au moins 1 population continue
    taches   : aucune continue, au moins 1 en taches
    isolés   : ni continue ni taches, au moins 1 d'individus isolés
    non renseignée : compacité absente pour toutes les populations
  Couleurs : sarcelle clair → foncé, distincte du bleu P et du vert N.

  Éléments communs à tous les styles SPRINGE :
    - Tronçons SANS observation : toujours en TIRETS, sans remplissage.
      Dans les styles de SCORE (01 à 04), ils prennent la couleur de la
      première classe : sans EEE connue, tous les indicateurs valent 0, donc
      la classe est juste — « pas de problématique APPARENTE », au vu des
      données disponibles. Dans les styles DESCRIPTIFS (05 à 10), ils restent
      en gris #A6A6A6 : nombre de populations, compacité ou année n'ont
      aucune valeur mesurée pour eux.
      Dans tous les cas : une absence d'observation n'est PAS une absence
      d'EEE, et à l'échelle d'une DIR les tirets se fondent en trait continu
      (la distinction n'apparaît qu'en zoomant).
    - Triangle jaune cerclé de noir : tronçon composé de plusieurs portions
      dispersées (polygones portant le même identifiant, fusionnés par le
      lanceur). Ses valeurs sont calculées sur TOUTES ses portions réunies.
      Un triangle est posé sur chaque portion, à partir du 1:100 000.
    - Règles de contrôle « à vérifier » en noir pointillé : aucun tronçon
      ne disparaît de la carte sans prévenir.
    - Étiquettes du numéro de tronçon, tamponnées, à partir du 1:50 000.
    - Info-bulle au survol (Vue > Afficher les info-bulles, couche active).

  Comment le charger :
      Clic droit sur la couche > Propriétés > Symbologie > Style (en bas)
      > Charger le style... > choisir ce fichier.
  Ce fichier contient symbologie + étiquettes + info-bulle : il remplace
  les étiquettes éventuellement configurées sur la couche.
  Les commentaires disparaissent si le style est ré-enregistré depuis QGIS.
  ════════════════════════════════════════════════════════════════════════
-->
<!--
  styleCategories : symbologie, étiquettes et info-bulle. Formulaires, jointures et champs de la couche ne sont pas touchés.
-->
<qgis version="3.34.4-Prizren" styleCategories="Symbology|Labeling|MapTips" labelsEnabled="1">

  <!--
    ──────────────────────────────────────────────────────────────────────
    MOTEUR DE RENDU « ensemble de règles », légende À PLAT
    ──────────────────────────────────────────────────────────────────────
    Fonctionnement à connaître : un tronçon est dessiné par TOUTES les
    règles qu'il vérifie, pas seulement par la première. On s'en sert :
      - les règles de CLASSES (et de contrôle) ont des filtres mutuellement
        exclusifs : chaque tronçon reçoit une seule couleur ;
      - la règle du TRIANGLE est volontairement indépendante : elle
        s'AJOUTE par-dessus la couleur du tronçon.

    Toutes les règles sont au même niveau, sans règle « groupe » : QGIS
    replie les sous-groupes dans le panneau Couches et dans la fenêtre
    Symbologie, ce qui cachait les classes de couleur (version précédente).

    Pas de règle ELSE non plus : un ELSE ne s'applique qu'aux tronçons qui
    ne vérifient AUCUNE autre règle du même niveau, triangle compris. Un
    tronçon fragmenté y échapperait. Les règles de contrôle « à vérifier »
    écrivent donc explicitement le contraire des classes :
      NOT coalesce(try( (classe 1) OR (classe 2) OR ... , false), false)
        (classe 1) OR ...  vrai si le tronçon tombe dans une classe
        try(..., false)    si le calcul plante (table absente...), vaut faux
        coalesce(..., false) si une valeur est vide (NULL), vaut faux
        NOT                inverse : la règle attrape tout ce qui n'est
                           dans aucune classe

    symbollevels="1" : dessin par niveaux. Les rubans sont au niveau 0
    (pass="0"), les triangles au niveau 1 (pass="1") : tous les triangles
    sont dessinés APRÈS tous les rubans, donc jamais recouverts.
  -->
  <renderer-v2 type="RuleRenderer" enableorderby="1" forceraster="0" symbollevels="1" referencescale="-1">
    <rules key="{09005ceb-5a1c-4e0e-8000-000000000001}">
      <!--
        Tronçons sans observation. Valeur SANS accent dans le GeoPackage.
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000010}" symbol="0" label="Aucune observation enregistrée (≠ absence d'EEE)" filter="&quot;statut_donnee&quot; = 'aucune observation enregistree'"/>

      <!--
        Au moins 1 population continue.
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000030}" symbol="1" label="Au moins une population continue" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND (coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0)"/>

      <!--
        Aucune continue, au moins 1 en taches.
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000031}" symbol="2" label="Populations en taches (aucune continue)" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND (coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_taches&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0)"/>

      <!--
        Ni continue ni taches, au moins 1 population d'individus isolés.
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000032}" symbol="3" label="Individus isolés uniquement" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND (coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_taches&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_isolees&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0)"/>

      <!--
        Aucune compacité renseignée, mais au moins 1 population sans compacité.
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000033}" symbol="4" label="Compacité non renseignée" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND (coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_taches&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_isolees&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_compacite_nr&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0)"/>

      <!--
        Contrôle : aucun comptage trouvé. Cause la plus probable : table de
        caractérisation non chargée, ou chargée sous un autre nom.
        Contrôle : tronçon observé qui n'entre dans AUCUNE des classes ci-dessus
        (voir l'explication NOT coalesce(try(...)) en tête du moteur de rendu).
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000029}" symbol="5" label="Non calculable — table « caracterisation_EEE_par_troncon_espece » absente du projet ?" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND NOT coalesce(try((coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0) OR (coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_taches&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0) OR (coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_taches&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_isolees&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0) OR (coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_continues&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_taches&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_isolees&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) = 0 AND coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:=&quot;nb_pop_compacite_nr&quot;, filter:=&quot;id_troncon&quot; = attribute(@parent, 'nom_plo_fi')), 0) &gt; 0), false), false)"/>

      <!--
        Contrôle : statut vide, ou libellé modifié par une future version du lanceur.
        IN (...) teste l'appartenance à la liste ; statut vide → coalesce → faux → NOT → vrai.
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000019}" symbol="6" label="Statut de la donnée non reconnu (à vérifier)" filter="NOT coalesce(&quot;statut_donnee&quot; IN ('observations enregistrees', 'aucune observation enregistree'), false)"/>

      <!--
        Tronçons fragmentés : cette règle s'AJOUTE à la couleur du tronçon.
        num_geometries($geometry) = nombre de portions du polygone du tronçon.
        Plus d'une portion = polygones de même identifiant fusionnés par le
        lanceur (mode « fusion » de la déduplication).
        scalemaxdenom="100000" : triangles visibles seulement à partir du
        1:100 000 en zoomant. Dans la zone de test, 106 tronçons sur 337 sont
        fragmentés, soit près de 500 triangles : à l'échelle d'une DIR entière,
        ils recouvraient complètement les rubans colorés.
      -->
      <rule key="{09005ceb-5a1c-4e0e-8000-000000000003}" symbol="7" scalemaxdenom="100000" label="Tronçon en plusieurs portions dispersées (valeurs calculées sur l'ensemble) — visible dès le 1:100 000" filter="num_geometries($geometry) &gt; 1"/>
    </rules>

    <!--
      ──────────────────────────────────────────────────────────────────────
      SYMBOLES
      ──────────────────────────────────────────────────────────────────────
      Symboles de ruban (couche SimpleFill) :
        color / outline_color  couleur "R,G,B,Alpha" (0 à 255)
        style                  remplissage : solid (plein) ou no (vide)
        outline_style          contour : solid, dash (tirets), dot (pointillés),
                               dash dot (tiret-point)
        outline_width + _unit  épaisseur en MM écran, constante à toute échelle
        Remplissage et contour de même couleur : plein en zoom, lisible dézoomé.
      Symbole du triangle (couche CentroidFill) : pose un marqueur sur le
      polygone plutôt que de le remplir.
        point_on_surface="1"   point garanti À L'INTÉRIEUR de la portion (un
                               centroïde peut tomber hors d'un ruban courbe)
        point_on_all_parts="1" un marqueur sur CHAQUE portion du tronçon
        marqueur SimpleMarker : name=triangle, 3 mm, jaune 255,230,0,
                               contour noir 0,4 mm
      (Pas de commentaires À L'INTÉRIEUR des blocs <Option>.)
    -->
    <symbols>
      <!--
        Symbole 0 — Aucune observation enregistrée
        Gris clair #A6A6A6, tirets, sans remplissage, 0,6 mm.
      -->
      <symbol type="fill" name="0" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000100}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="166,166,166,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="166,166,166,255"/>
            <Option type="QString" name="outline_style" value="dash"/>
            <Option type="QString" name="outline_width" value="0.6"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="style" value="no"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 1 — Au moins une population continue
        #2F7F74, sarcelle foncé.
      -->
      <symbol type="fill" name="1" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000101}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="47,127,116,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="47,127,116,255"/>
            <Option type="QString" name="outline_style" value="solid"/>
            <Option type="QString" name="outline_width" value="0.8"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="style" value="solid"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 2 — Populations en taches (aucune continue)
        #7FB8AE, sarcelle moyen.
      -->
      <symbol type="fill" name="2" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000102}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="127,184,174,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="127,184,174,255"/>
            <Option type="QString" name="outline_style" value="solid"/>
            <Option type="QString" name="outline_width" value="0.8"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="style" value="solid"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 3 — Individus isolés uniquement
        #D3E8E4, sarcelle très clair.
      -->
      <symbol type="fill" name="3" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000103}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="211,232,228,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="211,232,228,255"/>
            <Option type="QString" name="outline_style" value="solid"/>
            <Option type="QString" name="outline_width" value="0.8"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="style" value="solid"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 4 — Compacité non renseignée
        Gris-sarcelle #6F8F8A, tiret-point, sans remplissage : donnée partielle.
      -->
      <symbol type="fill" name="4" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000104}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="111,143,138,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="111,143,138,255"/>
            <Option type="QString" name="outline_style" value="dash dot"/>
            <Option type="QString" name="outline_width" value="0.6"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="style" value="no"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 5 — Non calculable — table « caracterisation_EEE_par_troncon_espece » absente du projet ?
        Noir pointillé : anomalie à vérifier, sans couleur « d'alerte ».
      -->
      <symbol type="fill" name="5" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000105}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="0,0,0,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="0,0,0,255"/>
            <Option type="QString" name="outline_style" value="dot"/>
            <Option type="QString" name="outline_width" value="0.6"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="style" value="no"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 6 — Statut de la donnée non reconnu : noir pointillé.
      -->
      <symbol type="fill" name="6" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000106}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="0,0,0,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="0,0,0,255"/>
            <Option type="QString" name="outline_style" value="dot"/>
            <Option type="QString" name="outline_width" value="0.6"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="style" value="no"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 7 — Triangle des tronçons fragmentés (niveau de dessin 1, au-dessus des rubans).
      -->
      <symbol type="fill" name="7" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="CentroidFill" enabled="1" locked="0" pass="1" id="{09005ceb-5a1c-4e0e-8000-000000000190}">
          <Option type="Map">
            <Option type="QString" name="clip_on_current_part_only" value="0"/>
            <Option type="QString" name="clip_points" value="0"/>
            <Option type="QString" name="point_on_all_parts" value="1"/>
            <Option type="QString" name="point_on_surface" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
          <symbol type="marker" name="@7@0" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
            <data_defined_properties>
              <Option type="Map">
                <Option type="QString" name="name" value=""/>
                <Option name="properties"/>
                <Option type="QString" name="type" value="collection"/>
              </Option>
            </data_defined_properties>
            <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{09005ceb-5a1c-4e0e-8000-000000000191}">
              <Option type="Map">
                <Option type="QString" name="angle" value="0"/>
                <Option type="QString" name="cap_style" value="square"/>
                <Option type="QString" name="color" value="255,230,0,255"/>
                <Option type="QString" name="horizontal_anchor_point" value="1"/>
                <Option type="QString" name="joinstyle" value="bevel"/>
                <Option type="QString" name="name" value="triangle"/>
                <Option type="QString" name="offset" value="0,0"/>
                <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
                <Option type="QString" name="offset_unit" value="MM"/>
                <Option type="QString" name="outline_color" value="0,0,0,255"/>
                <Option type="QString" name="outline_style" value="solid"/>
                <Option type="QString" name="outline_width" value="0.4"/>
                <Option type="QString" name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
                <Option type="QString" name="outline_width_unit" value="MM"/>
                <Option type="QString" name="scale_method" value="diameter"/>
                <Option type="QString" name="size" value="3"/>
                <Option type="QString" name="size_map_unit_scale" value="3x:0,0,0,0,0,0"/>
                <Option type="QString" name="size_unit" value="MM"/>
                <Option type="QString" name="vertical_anchor_point" value="1"/>
              </Option>
              <data_defined_properties>
                <Option type="Map">
                  <Option type="QString" name="name" value=""/>
                  <Option name="properties"/>
                  <Option type="QString" name="type" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
      </symbol>
    </symbols>

    <!--
      ──────────────────────────────────────────────────────────────────────
      ORDRE DE DESSIN
      ──────────────────────────────────────────────────────────────────────
      Tri sur le seul statut (0 non observé, 1 observé, croissant) : les
      observés passent au-dessus. On ne trie pas sur les comptages pour ne pas
      recalculer aggregate() une fois de plus par tronçon.
    -->
    <orderby>
      <orderByClause asc="1" nullsFirst="1">"statut_donnee" = 'observations enregistrees'</orderByClause>
    </orderby>
  </renderer-v2>

  <!--
    ──────────────────────────────────────────────────────────────────────
    ÉTIQUETTES (identiques au style 00, sauf une par portion)
    ──────────────────────────────────────────────────────────────────────
    Texte : champ "nom_plo_fi", Arial 8 pt, noir #1A1A1A.
    Tampon : blanc, 1 mm, 85 % d'opacité, coins arrondis (bufferJoinStyle
      128) : le numéro reste lisible sur n'importe quelle couleur.
    Placement 4 = horizontal, à l'intérieur du polygone ; le texte peut
      déborder d'un ruban étroit (fitInPolygonOnly="0") ; jamais deux
      étiquettes superposées (PreventOverlap).
    Visibles à partir du 1:50 000 : scaleMax="50000" (dans le vocabulaire
      QGIS, scaleMax = l'échelle la plus dézoomée où l'étiquette apparaît).
    obstacle="0" : les rubans ne repoussent pas leurs propres numéros.
    labelPerPart="1" : un numéro sur CHAQUE portion d'un tronçon fragmenté,
      pour pouvoir identifier chaque morceau isolé (différence avec le 00).
  -->
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style fieldName="nom_plo_fi" isExpression="0"
                  fontFamily="Arial" fontSize="8" fontSizeUnit="Point" fontWeight="50"
                  textColor="26,26,26,255" textOpacity="1"
                  multilineHeight="1" multilineHeightUnit="Percentage" allowHtml="0">
        <families/>
        <text-buffer bufferDraw="1" bufferSize="1" bufferSizeUnits="MM"
                     bufferColor="255,255,255,255" bufferOpacity="0.85"
                     bufferNoFill="1" bufferJoinStyle="128" bufferBlendMode="0"/>
      </text-style>
      <placement placement="4" polygonPlacementFlags="2" fitInPolygonOnly="0"
                 overlapHandling="PreventOverlap" priority="5"
                 dist="0" distUnits="MM" offsetType="0" quadOffset="4"
                 xOffset="0" yOffset="0" offsetUnits="MM" rotationAngle="0"
                 centroidWhole="0" centroidInside="0"/>
      <rendering drawLabels="1" scaleVisibility="1" scaleMin="0" scaleMax="50000"
                 obstacle="0" labelPerPart="1" upsidedownLabels="0"
                 limitNumLabels="0" maxNumLabels="2000" minFeatureSize="0"
                 fontLimitPixelSize="0" zIndex="0" unplacedVisibility="0"/>
    </settings>
  </labeling>

  <selection mode="Default">
    <selectionColor invalid="1"/>
  </selection>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>

  <!--
    ──────────────────────────────────────────────────────────────────────
    INFO-BULLE
    ──────────────────────────────────────────────────────────────────────
    [% ... %] = expression évaluée pour le tronçon survolé ; || colle des
    textes ; if(condition, si_vrai, si_faux). Le HTML (<b>, <br>) est écrit
    &lt; &gt; parce qu'on est dans du XML.
    Ligne 1 : numéro du tronçon, puis avertissement s'il est fragmenté.
    Ligne 2 : décompte des populations par compacité (mêmes aggregate()).
    try(..., message) : si la table manque, affiche un message au lieu d'une erreur.
    Dernière ligne : résumé "synthese_EEE" rédigé par le lanceur.
  -->
  <mapTip enabled="1">&lt;b&gt;Tronçon [% "nom_plo_fi" %]&lt;/b&gt;[% if(num_geometries($geometry) &gt; 1, '&lt;br&gt;⚠ Tronçon composé de ' || num_geometries($geometry) || ' portions dispersées : valeurs calculées sur toutes les portions réunies', '') %]&lt;br&gt;[% try(if("statut_donnee" = 'observations enregistrees', 'Populations : ' || coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:="nb_pop_continues", filter:="id_troncon" = attribute(@parent, 'nom_plo_fi')), 0) || ' continue(s) · ' || coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:="nb_pop_taches", filter:="id_troncon" = attribute(@parent, 'nom_plo_fi')), 0) || ' en taches · ' || coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:="nb_pop_isolees", filter:="id_troncon" = attribute(@parent, 'nom_plo_fi')), 0) || ' isolée(s) · ' || coalesce(aggregate(layer:='caracterisation_EEE_par_troncon_espece', aggregate:='sum', expression:="nb_pop_compacite_nr", filter:="id_troncon" = attribute(@parent, 'nom_plo_fi')), 0) || ' non renseignée(s)', 'Aucune observation enregistrée'), 'Comptages non calculables : table de caractérisation absente du projet') %]&lt;br&gt;[% "synthese_EEE" %]</mapTip>

  <!-- 2 = polygones : QGIS refuse ce style sur une couche de points ou de lignes. -->
  <layerGeometryType>2</layerGeometryType>
</qgis>
