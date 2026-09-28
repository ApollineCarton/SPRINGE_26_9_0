<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!--
  ════════════════════════════════════════════════════════════════════════
  SPRINGE — Style 11 : populations d'EEE (couche de points)
  ════════════════════════════════════════════════════════════════════════
  Couche cible : 'caracterisation_population' du GeoPackage SPRINGE
                 (PAS la couche des tronçons : ce style est refusé sur elle).
  Testé sur    : QGIS 3.34.4 (chargement, classement, rendu).
                 À revérifier sur 3.44.11.

  Question : « Où sont les populations, de quelle espèce, de quelle taille
              et de quelle structure ? »

  ⚠ UN POINT = UNE POPULATION AU SENS DU PROTOCOLE, PAS UNE PLANTE.
    Deux taches d'une même espèce distantes de moins de 50 m forment une
    seule population. Une forte concentration de végétation ne produit donc
    PAS un amas de points, mais UN SEUL point de grande taille.

  Trois informations sont portées simultanément :
    • la COULEUR  = l'espèce ;
    • la TAILLE   = la classe de longueur (losange si non renseignée) ;
    • le REMPLISSAGE = la compacité : plein (population continue), à demi
      teinté (taches discontinues), contour seul (individus isolés),
      contour pointillé (compacité non renseignée).

  La légende porte les trois : les entrées d'espèce dessinent les points,
  les entrées grises de taille et de remplissage ne servent qu'à expliquer
  (leur filtre est toujours faux, elles ne dessinent rien).

  Ce style se superpose à n'importe quel style de tronçons (01 à 10).

  Les valeurs lues ('Sup20m', 'Continue', 'nr'...) sont celles de la couche
  HARMONISÉE écrite par le lanceur : elles sont identiques quelle que soit
  la DIR d'origine. Ce style ne fonctionne donc pas sur une couche de points
  brute.

  Comment le charger :
      Clic droit sur la couche > Propriétés > Symbologie > Style (en bas)
      > Charger le style... > choisir ce fichier.
  Les commentaires disparaissent si le style est ré-enregistré depuis QGIS.
  ════════════════════════════════════════════════════════════════════════
-->
<qgis version="3.34.4-Prizren" styleCategories="Symbology|Labeling|MapTips" labelsEnabled="1">

  <!--
    ──────────────────────────────────────────────────────────────────────
    MOTEUR DE RENDU
    ──────────────────────────────────────────────────────────────────────
    Rendu par règles, légende à plat (comme les styles 01 à 10) :
      - 5 règles d'espèce, filtres mutuellement exclusifs ;
      - 1 règle de contrôle « espèce non reconnue » ;
      - 8 règles de LÉGENDE au filtre 1 = 0, qui ne dessinent rien.

    Taille, forme, remplissage et contour ne sont pas figés dans les
    symboles : ils sont recalculés pour chaque population par des
    EXPRESSIONS (bloc data_defined_properties de chaque symbole). C'est ce
    qui permet de porter trois variables avec six symboles au lieu d'en
    écrire 5 × 4 × 4 = 80.
  -->
  <renderer-v2 type="RuleRenderer" enableorderby="1" forceraster="0" symbollevels="0" referencescale="-1">
    <rules key="{11005ceb-5a1c-4e0e-8000-000000000001}">
      <!--
        Population de Renouées.
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000010}" symbol="0" label="Renouées (Reynoutria sp.)" filter="&quot;espece&quot; = 'Reynoutria sp'"/>

      <!--
        Population de Ailante.
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000011}" symbol="1" label="Ailante (Ailanthus altissima)" filter="&quot;espece&quot; = 'Ailanthus altissima'"/>

      <!--
        Population de Ambroisie.
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000012}" symbol="2" label="Ambroisie (Ambrosia artemisiifolia)" filter="&quot;espece&quot; = 'Ambrosia artemisiifolia'"/>

      <!--
        Population de Berce du Caucase.
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000013}" symbol="3" label="Berce du Caucase (Heracleum mantegazzianum)" filter="&quot;espece&quot; = 'Heracleum mantegazzianum'"/>

      <!--
        Population de EEE autre.
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000014}" symbol="4" label="EEE autre (espèces hors des 4 catégories)" filter="&quot;espece&quot; = 'EEE autre'"/>

      <!--
        Contrôle : valeur d'espèce hors des 5 catégories SPRINGE, ou vide.
        NOT IN (...) est vrai hors de la liste ; coalesce(..., true) attrape en plus
        les valeurs vides, pour lesquelles NOT IN ne renvoie ni vrai ni faux.
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000019}" symbol="5" label="Espèce non reconnue (à vérifier)" filter="coalesce(&quot;espece&quot; NOT IN ('Reynoutria sp', 'Ailanthus altissima', 'Ambrosia artemisiifolia', 'Heracleum mantegazzianum', 'EEE autre'), true)"/>

      <!--
        Règle de LÉGENDE : le filtre 1 = 0 n'est jamais vrai, donc elle ne dessine
        aucune population. Elle sert uniquement à documenter dans la légende ce que
        la taille et le remplissage des ronds signifient.
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000030}" symbol="6" label="Taille du rond — longueur de la population :
   plus de 20 m" filter="1 = 0"/>

      <!--
        Règle de légende (filtre toujours faux, ne dessine rien).
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000031}" symbol="7" label="   5 à 20 m" filter="1 = 0"/>

      <!--
        Règle de légende (filtre toujours faux, ne dessine rien).
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000032}" symbol="8" label="   moins de 5 m" filter="1 = 0"/>

      <!--
        Règle de légende (filtre toujours faux, ne dessine rien).
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000033}" symbol="9" label="   longueur non renseignée (losange)" filter="1 = 0"/>

      <!--
        Règle de légende (filtre toujours faux, ne dessine rien).
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000034}" symbol="10" label="Remplissage — compacité de la population :
   population continue (rond plein)" filter="1 = 0"/>

      <!--
        Règle de légende (filtre toujours faux, ne dessine rien).
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000035}" symbol="11" label="   taches discontinues (rond à demi teinté)" filter="1 = 0"/>

      <!--
        Règle de légende (filtre toujours faux, ne dessine rien).
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000036}" symbol="12" label="   individus isolés (contour seul)" filter="1 = 0"/>

      <!--
        Règle de légende (filtre toujours faux, ne dessine rien).
      -->
      <rule key="{11005ceb-5a1c-4e0e-8000-000000000037}" symbol="13" label="   compacité non renseignée (contour pointillé)" filter="1 = 0"/>
    </rules>

    <!--
      ──────────────────────────────────────────────────────────────────────
      SYMBOLES
      ──────────────────────────────────────────────────────────────────────
      Chaque symbole est un marqueur simple (SimpleMarker) :
        name                  forme : circle, diamond, cross2...
        color                 couleur de REMPLISSAGE, en "R,V,B,Alpha" (0 à 255)
        outline_color/_style/_width   contour
        size + size_unit      diamètre, en MM écran (constant à toute échelle)

      Chaque symbole d'espèce a DEUX couches superposées :
        1. un HALO : même forme et même taille, sans remplissage, contour blanc
           à 82 % d'opacité et plus épais (1,2 mm). Il est dessiné en premier,
           donc il passe DESSOUS ;
        2. le marqueur coloré lui-même, contour de 0,4 mm.
      Le halo dépasse légèrement du marqueur et détache le point de son fond :
      sans lui, une petite population d'« EEE autre » (gris-bleu foncé) est
      illisible sur un tronçon gris foncé du style 05. Comme le halo n'est
      qu'un anneau, l'intérieur du marqueur reste transparent pour les
      individus isolés.

      Bloc data_defined_properties des symboles d'espèce — quatre expressions :

        size        case when "longueur" = 'Sup20m' then 5 ... end
                    case when ... then ... else ... end = « selon le cas ».
                    5 mm pour plus de 20 m, 3,6 pour 5 à 20 m, 2,4 pour moins
                    de 5 m, 3 pour une longueur non renseignée.

        name        if("longueur" = 'nr', 'diamond', 'circle')
                    losange quand la longueur est inconnue : la taille seule ne
                    pourrait pas distinguer « inconnue » de « petite ».

        fillColor   color_rgba(r, v, b, case when "compacite" = 'Continue'
                    then 255 when "compacite" = 'Taches' then 120 else 0 end)
                    color_rgba(rouge, vert, bleu, opacité) construit une couleur.
                    Les trois premiers nombres sont la teinte de l'espèce ; le
                    quatrième vient de la compacité : 255 = plein, 120 = à demi
                    teinté, 0 = transparent (seul le contour reste visible).

        outlineStyle  if("compacite" = 'nr', 'dot', 'solid')
                    contour pointillé quand la compacité est inconnue, ce qui la
                    distingue des individus isolés (également sans remplissage).

      (Pas de commentaires À L'INTÉRIEUR des blocs <Option>.)
    -->
    <symbols>
      <!--
        Symbole 0 — Renouées (Reynoutria sp.)
        Couleur #C2185B. Les quatre propriétés dynamiques (taille, forme, couleur de
        remplissage, style de contour) sont identiques dans tous les symboles d'espèce :
        seule la teinte change. Les valeurs fixes du bloc <Option> (size, color...) ne
        servent qu'à l'aperçu de la légende, où aucune population n'est en cours de
        dessin ; ce sont les expressions qui décident du rendu réel.
      -->
      <symbol name="0" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-0000000001h00">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="255,255,255,210"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="1.2"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000100}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="194,24,91,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="194,24,91,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="fillColor" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="color_rgba(194, 24, 91, case when &quot;compacite&quot; = 'Continue' then 255 when &quot;compacite&quot; = 'Taches' then 120 else 0 end)"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 1 — Ailante (Ailanthus altissima)
        Couleur #00695C. Les quatre propriétés dynamiques (taille, forme, couleur de
        remplissage, style de contour) sont identiques dans tous les symboles d'espèce :
        seule la teinte change. Les valeurs fixes du bloc <Option> (size, color...) ne
        servent qu'à l'aperçu de la légende, où aucune population n'est en cours de
        dessin ; ce sont les expressions qui décident du rendu réel.
      -->
      <symbol name="1" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-0000000001h00">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="255,255,255,210"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="1.2"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000101}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,105,92,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="0,105,92,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="fillColor" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="color_rgba(0, 105, 92, case when &quot;compacite&quot; = 'Continue' then 255 when &quot;compacite&quot; = 'Taches' then 120 else 0 end)"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 2 — Ambroisie (Ambrosia artemisiifolia)
        Couleur #EF6C00. Les quatre propriétés dynamiques (taille, forme, couleur de
        remplissage, style de contour) sont identiques dans tous les symboles d'espèce :
        seule la teinte change. Les valeurs fixes du bloc <Option> (size, color...) ne
        servent qu'à l'aperçu de la légende, où aucune population n'est en cours de
        dessin ; ce sont les expressions qui décident du rendu réel.
      -->
      <symbol name="2" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-0000000001h00">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="255,255,255,210"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="1.2"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000102}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="239,108,0,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="239,108,0,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="fillColor" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="color_rgba(239, 108, 0, case when &quot;compacite&quot; = 'Continue' then 255 when &quot;compacite&quot; = 'Taches' then 120 else 0 end)"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 3 — Berce du Caucase (Heracleum mantegazzianum)
        Couleur #4527A0. Les quatre propriétés dynamiques (taille, forme, couleur de
        remplissage, style de contour) sont identiques dans tous les symboles d'espèce :
        seule la teinte change. Les valeurs fixes du bloc <Option> (size, color...) ne
        servent qu'à l'aperçu de la légende, où aucune population n'est en cours de
        dessin ; ce sont les expressions qui décident du rendu réel.
      -->
      <symbol name="3" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-0000000001h00">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="255,255,255,210"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="1.2"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000103}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="69,39,160,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="69,39,160,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="fillColor" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="color_rgba(69, 39, 160, case when &quot;compacite&quot; = 'Continue' then 255 when &quot;compacite&quot; = 'Taches' then 120 else 0 end)"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 4 — EEE autre (espèces hors des 4 catégories)
        Couleur #455A64. Les quatre propriétés dynamiques (taille, forme, couleur de
        remplissage, style de contour) sont identiques dans tous les symboles d'espèce :
        seule la teinte change. Les valeurs fixes du bloc <Option> (size, color...) ne
        servent qu'à l'aperçu de la légende, où aucune population n'est en cours de
        dessin ; ce sont les expressions qui décident du rendu réel.
      -->
      <symbol name="4" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-0000000001h00">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="255,255,255,210"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="1.2"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000104}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="69,90,100,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="69,90,100,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="fillColor" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="color_rgba(69, 90, 100, case when &quot;compacite&quot; = 'Continue' then 255 when &quot;compacite&quot; = 'Taches' then 120 else 0 end)"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="name" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;longueur&quot; = 'nr', 'diamond', 'circle')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="outlineStyle" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="if(&quot;compacite&quot; = 'nr', 'dot', 'solid')"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
                <Option name="size" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="case when &quot;longueur&quot; = 'Sup20m' then 5.6 when &quot;longueur&quot; = '5a20m' then 4.2 when &quot;longueur&quot; = 'Inf5m' then 3 else 3.6 end"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>

      <!--
        Symbole 5 — Espèce non reconnue : croix noire, taille fixe, sans
        propriété dynamique. Signale une anomalie sans couleur d'espèce.
      -->
      <symbol name="5" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000105}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="cross2"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="0,0,0,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="3"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 6 — Légende seule : plus de 20 m
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="6" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000200}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="77,77,77,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="5.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 7 — Légende seule : 5 à 20 m
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="7" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000201}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="77,77,77,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="4.2"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 8 — Légende seule : moins de 5 m
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="8" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000202}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="77,77,77,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="3"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 9 — Légende seule : longueur non renseignée (losange)
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="9" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000203}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="77,77,77,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="diamond"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="3.6"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 10 — Légende seule : population continue (rond plein)
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="10" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000204}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="77,77,77,255"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="4"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 11 — Légende seule : taches discontinues (rond à demi teinté)
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="11" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000205}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="77,77,77,120"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="4"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 12 — Légende seule : individus isolés (contour seul)
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="12" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000206}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="solid"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="4"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
        Symbole 13 — Légende seule : compacité non renseignée (contour pointillé)
        Gris neutre : cette entrée explique une propriété, pas une espèce.
      -->
      <symbol name="13" type="marker" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0" id="{11005ceb-5a1c-4e0e-8000-000000000207}">
          <Option type="Map">
            <Option name="angle" type="QString" value="0"/>
            <Option name="cap_style" type="QString" value="square"/>
            <Option name="color" type="QString" value="0,0,0,0"/>
            <Option name="horizontal_anchor_point" type="QString" value="1"/>
            <Option name="joinstyle" type="QString" value="bevel"/>
            <Option name="name" type="QString" value="circle"/>
            <Option name="offset" type="QString" value="0,0"/>
            <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="offset_unit" type="QString" value="MM"/>
            <Option name="outline_color" type="QString" value="77,77,77,255"/>
            <Option name="outline_style" type="QString" value="dot"/>
            <Option name="outline_width" type="QString" value="0.4"/>
            <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="scale_method" type="QString" value="diameter"/>
            <Option name="size" type="QString" value="4"/>
            <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            <Option name="size_unit" type="QString" value="MM"/>
            <Option name="vertical_anchor_point" type="QString" value="1"/>
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
    </symbols>

    <!--
      ──────────────────────────────────────────────────────────────────────
      ORDRE DE DESSIN
      ──────────────────────────────────────────────────────────────────────
      Tri croissant sur la taille du rond : les grandes populations sont
      dessinées en dernier, donc jamais masquées par une petite voisine.
    -->
    <orderby>
      <orderByClause asc="1" nullsFirst="1">case when "longueur" = 'Sup20m' then 5.6 when "longueur" = '5a20m' then 4.2 when "longueur" = 'Inf5m' then 3 else 3.6 end</orderByClause>
    </orderby>
  </renderer-v2>

  <!--
    ──────────────────────────────────────────────────────────────────────
    ÉTIQUETTES — numéro de population
    ──────────────────────────────────────────────────────────────────────
    Même présentation que les styles de tronçons : noir 8 pt, tampon blanc
    de 1 mm, jamais deux étiquettes superposées.
    Le champ est "id_population" (1..n). ⚠ Ce numéro est attribué à chaque
    exécution de SPRINGE : il désigne un point dans CE fichier, il ne
    constitue pas un identifiant pérenne.
    Visibles à partir du 1:25 000, plus tard que les numéros de tronçons
    (scaleMax="25000") : les populations sont bien plus nombreuses et
    souvent groupées.
    dist="1" : l'étiquette est posée à 1 mm du point, pas dessus.
    obstacle="1" : un numéro n'est jamais posé sur une autre population.
  -->
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style fieldName="id_population" isExpression="0"
                  fontFamily="Arial" fontSize="8" fontSizeUnit="Point" fontWeight="50"
                  textColor="26,26,26,255" textOpacity="1"
                  multilineHeight="1" multilineHeightUnit="Percentage" allowHtml="0">
        <families/>
        <text-buffer bufferDraw="1" bufferSize="1" bufferSizeUnits="MM"
                     bufferColor="255,255,255,255" bufferOpacity="0.85"
                     bufferNoFill="1" bufferJoinStyle="128" bufferBlendMode="0"/>
      </text-style>
      <placement placement="0" dist="1" distUnits="MM" overlapHandling="PreventOverlap"
                 priority="5" offsetType="0" quadOffset="4" xOffset="0" yOffset="0"
                 offsetUnits="MM" rotationAngle="0" centroidWhole="0" centroidInside="0"/>
      <rendering drawLabels="1" scaleVisibility="1" scaleMin="0" scaleMax="25000"
                 obstacle="1" labelPerPart="0" upsidedownLabels="0"
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
    map('cle1', 'valeur1', 'cle2', 'valeur2', ...) construit un
    dictionnaire ; map_get(dictionnaire, cle) y lit une valeur. On traduit
    ainsi les codes du protocole en toutes lettres ('Sup20m' → 'plus de
    20 m') sans empiler des if() imbriqués.
    Pour les voir : Vue > Afficher les info-bulles, couche active.
  -->
  <mapTip enabled="1">&lt;b&gt;Population [% "id_population" %] — [% "espece_libelle" %]&lt;/b&gt;&lt;br&gt;Largeur : [% map_get(map('Inf1m','moins de 1 m','1a3m','1 à 3 m','Sup3m','plus de 3 m','nr','non renseignée'), "largeur") %] · Longueur : [% map_get(map('Inf5m','moins de 5 m','5a20m','5 à 20 m','Sup20m','plus de 20 m','nr','non renseignée'), "longueur") %]&lt;br&gt;Compacité : [% map_get(map('Isoles','individus isolés','Taches','taches discontinues','Continue','population continue','nr','non renseignée'), "compacite") %]&lt;br&gt;Tronçon(s) : [% "id_troncons" %]&lt;br&gt;Relevé : [% coalesce(to_string(to_int("annee_releve")), 'année non renseignée') %] · Localisation : [% coalesce("localisation", 'non fournie') %]</mapTip>

  <!-- 0 = géométrie ponctuelle : QGIS refuse ce style sur les tronçons (polygones). -->
  <layerGeometryType>0</layerGeometryType>
</qgis>
