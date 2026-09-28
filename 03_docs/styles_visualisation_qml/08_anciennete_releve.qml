<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!--
  ════════════════════════════════════════════════════════════════════════
  SPRINGE — Style 08 : ancienneté du relevé le plus récent
  ════════════════════════════════════════════════════════════════════════
  Couche cible : couche cartographique des tronçons du GeoPackage SPRINGE.
  Testé sur    : QGIS 3.34.4 (chargement, classement, rendu).
                 Chargement vérifié par l'utilisatrice sur 3.44.11 pour
                 les styles 00, 01 et 05 ; à revérifier pour celui-ci.

  Question : « De quand date le relevé le plus récent du tronçon ? »
  Ancienneté = année en cours (year(now())) − "annee_releve_max". Elle est
  recalculée à chaque affichage : la carte vieillit avec le temps, sans
  qu'il faille régénérer le style.
  Bornes 4 / 8 / 12 ans : multiples du cycle d'actualisation de 4 ans prévu
  au § IV.4 du protocole national (Albert 2017).
  Tronçon observé sans année : classe « année non renseignée », jamais
  rattachée à une classe par défaut.
  Couleurs : du brun vif (récent) au beige terne (ancien).

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
    <rules key="{08005ceb-5a1c-4e0e-8000-000000000001}">
      <!--
        Tronçons sans observation. Valeur SANS accent dans le GeoPackage.
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000010}" symbol="0" label="Aucune observation enregistrée (≠ absence d'EEE)" filter="&quot;statut_donnee&quot; = 'aucune observation enregistree'"/>

      <!--
        Année absente. Placée en premier : pour une valeur vide, les calculs
        d'ancienneté des règles suivantes donnent NULL et ne classent rien.
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000030}" symbol="1" label="Année de relevé non renseignée" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND (&quot;annee_releve_max&quot; IS NULL)"/>

      <!--
        4 ans ou moins : au plus un cycle d'actualisation.
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000031}" symbol="2" label="Relevé de 4 ans ou moins" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND ((year(now()) - &quot;annee_releve_max&quot;) &lt;= 4)"/>

      <!--
        Plus de 4 ans, jusqu'à 8 ans (deux cycles).
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000032}" symbol="3" label="Relevé de 5 à 8 ans" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND ((year(now()) - &quot;annee_releve_max&quot;) &gt; 4 AND (year(now()) - &quot;annee_releve_max&quot;) &lt;= 8)"/>

      <!--
        Plus de 8 ans, jusqu'à 12 ans (trois cycles).
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000033}" symbol="4" label="Relevé de 9 à 12 ans" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND ((year(now()) - &quot;annee_releve_max&quot;) &gt; 8 AND (year(now()) - &quot;annee_releve_max&quot;) &lt;= 12)"/>

      <!--
        Plus de 12 ans.
        Filtre = tronçon observé ET condition de la classe.
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000034}" symbol="5" label="Relevé de plus de 12 ans" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND ((year(now()) - &quot;annee_releve_max&quot;) &gt; 12)"/>

      <!--
        Contrôle : année non numérique ou impossible à classer.
        Contrôle : tronçon observé qui n'entre dans AUCUNE des classes ci-dessus
        (voir l'explication NOT coalesce(try(...)) en tête du moteur de rendu).
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000029}" symbol="6" label="Année de relevé incohérente (à vérifier)" filter="&quot;statut_donnee&quot; = 'observations enregistrees' AND NOT coalesce(try((&quot;annee_releve_max&quot; IS NULL) OR ((year(now()) - &quot;annee_releve_max&quot;) &lt;= 4) OR ((year(now()) - &quot;annee_releve_max&quot;) &gt; 4 AND (year(now()) - &quot;annee_releve_max&quot;) &lt;= 8) OR ((year(now()) - &quot;annee_releve_max&quot;) &gt; 8 AND (year(now()) - &quot;annee_releve_max&quot;) &lt;= 12) OR ((year(now()) - &quot;annee_releve_max&quot;) &gt; 12), false), false)"/>

      <!--
        Contrôle : statut vide, ou libellé modifié par une future version du lanceur.
        IN (...) teste l'appartenance à la liste ; statut vide → coalesce → faux → NOT → vrai.
      -->
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000019}" symbol="7" label="Statut de la donnée non reconnu (à vérifier)" filter="NOT coalesce(&quot;statut_donnee&quot; IN ('observations enregistrees', 'aucune observation enregistree'), false)"/>

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
      <rule key="{08005ceb-5a1c-4e0e-8000-000000000003}" symbol="8" scalemaxdenom="100000" label="Tronçon en plusieurs portions dispersées (valeurs calculées sur l'ensemble) — visible dès le 1:100 000" filter="num_geometries($geometry) &gt; 1"/>
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
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000100}">
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
        Symbole 1 — Année de relevé non renseignée
        Brun-gris #8C8173, tiret-point, sans remplissage : donnée partielle,
        distincte des tirets gris « aucune observation ».
      -->
      <symbol type="fill" name="1" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000101}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="140,129,115,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="140,129,115,255"/>
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
        Symbole 2 — Relevé de 4 ans ou moins
        #8C4A12, brun vif.
      -->
      <symbol type="fill" name="2" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000102}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="140,74,18,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="140,74,18,255"/>
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
        Symbole 3 — Relevé de 5 à 8 ans
        #B7793F.
      -->
      <symbol type="fill" name="3" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000103}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="183,121,63,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="183,121,63,255"/>
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
        Symbole 4 — Relevé de 9 à 12 ans
        #D1AE82.
      -->
      <symbol type="fill" name="4" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000104}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="209,174,130,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="209,174,130,255"/>
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
        Symbole 5 — Relevé de plus de 12 ans
        #E6DAC6, beige terne.
      -->
      <symbol type="fill" name="5" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000105}">
          <Option type="Map">
            <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="color" value="230,218,198,255"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="230,218,198,255"/>
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
        Symbole 6 — Année de relevé incohérente (à vérifier)
        Noir pointillé : anomalie à vérifier, sans couleur « d'alerte ».
      -->
      <symbol type="fill" name="6" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000106}">
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
        Symbole 7 — Statut de la donnée non reconnu : noir pointillé.
      -->
      <symbol type="fill" name="7" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000107}">
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
        Symbole 8 — Triangle des tronçons fragmentés (niveau de dessin 1, au-dessus des rubans).
      -->
      <symbol type="fill" name="8" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="CentroidFill" enabled="1" locked="0" pass="1" id="{08005ceb-5a1c-4e0e-8000-000000000190}">
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
          <symbol type="marker" name="@8@0" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
            <data_defined_properties>
              <Option type="Map">
                <Option type="QString" name="name" value=""/>
                <Option name="properties"/>
                <Option type="QString" name="type" value="collection"/>
              </Option>
            </data_defined_properties>
            <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{08005ceb-5a1c-4e0e-8000-000000000191}">
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
      Les polygones D et G d'un même PR se recouvrent à ~96 % : le dernier
      dessiné masque l'autre. Clé de tri : -1 pour un tronçon non observé,
      son année de relevé (0 si absente) — les relevés récents passent au-dessus pour un tronçon observé. Tri croissant (asc="1") : les valeurs
      les plus fortes sont dessinées en dernier, donc visibles.
    -->
    <orderby>
      <orderByClause asc="1" nullsFirst="1">if("statut_donnee" = 'observations enregistrees', coalesce("annee_releve_max", 0), -1)</orderByClause>
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
    Ligne 2 : année du relevé le plus récent (observé).
    Dernière ligne : résumé "synthese_EEE" rédigé par le lanceur.
  -->
  <mapTip enabled="1">&lt;b&gt;Tronçon [% "nom_plo_fi" %]&lt;/b&gt;[% if(num_geometries($geometry) &gt; 1, '&lt;br&gt;⚠ Tronçon composé de ' || num_geometries($geometry) || ' portions dispersées : valeurs calculées sur toutes les portions réunies', '') %]&lt;br&gt;[% if("statut_donnee" = 'observations enregistrees', 'Relevé le plus récent : ' || coalesce(to_string(to_int("annee_releve_max")), 'année non renseignée'), 'Aucune observation enregistrée') %]&lt;br&gt;[% "synthese_EEE" %]</mapTip>

  <!-- 2 = polygones : QGIS refuse ce style sur une couche de points ou de lignes. -->
  <layerGeometryType>2</layerGeometryType>
</qgis>
