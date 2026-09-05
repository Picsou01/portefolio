#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
L'ARPENTEUR - générateur du portfolio « Le Cadastre »
Maël Davidenko · BTS SIO SLAM · session 2027
=======================================================================

À QUOI ÇA SERT
    Les données du portfolio (réalisations, compétences, preuves) vivent
    dans trois fichiers JSON. Ce script les lit et écrit les pages HTML,
    ainsi que les pièces graphiques calculées : le relief topographique
    et la rose des vents.

    Conséquence : on ne corrige jamais une date dans vingt fichiers. On
    la corrige une fois dans le JSON, on relance, et tout est à jour.

CE QUE ÇA NE FAIT PAS
    Le site produit est du HTML/CSS/JS statique. Il n'a besoin ni de
    Python, ni de serveur, ni de réseau. Ce script est un outil de
    maintenance, pas une brique du site.

USAGE
    python outils/arpenteur.py
"""

import json
import math
import os
import re
import sys

# ---------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------
ICI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(ICI)


def chemin(*bouts):
    return os.path.join(BASE, *bouts)


def ecrire(relatif, contenu):
    dest = chemin(*relatif.split('/'))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8', newline='\n') as f:
        f.write(contenu)
    print(f'  ecrit  {relatif}  ({len(contenu):,} o)'.replace(',', ' '))


def lire_json(relatif):
    with open(chemin(*relatif.split('/')), encoding='utf-8') as f:
        return json.load(f)


def remplir(gabarit, **valeurs):
    """Remplace les {{CLES}} du gabarit.

    Pas de f-string ici : les gabarits contiennent du CSS et du
    JavaScript, donc des accolades que les f-strings interpréteraient.
    """
    sortie = gabarit
    for cle, valeur in valeurs.items():
        sortie = sortie.replace('{{' + cle + '}}', str(valeur))
    return sortie


def echapper(texte):
    return (str(texte).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def sans_balises(texte):
    return re.sub(r'<[^>]+>', '', str(texte)).strip()


# =====================================================================
# 1. LE RELIEF : courbes de niveau par marching squares
# =====================================================================
#
# On définit un relief mathématique (une somme de bosses gaussiennes)
# puis on en extrait les courbes de niveau, comme un cartographe trace
# les lignes d'altitude égale.
#
# L'algorithme s'appelle « marching squares » : on parcourt la grille
# case par case, on regarde lesquels des quatre coins dépassent le
# niveau cherché, et on en déduit par quels côtés la courbe traverse.
#
# Les bosses sont fixées en dur : le relief doit être identique à chaque
# génération, sinon le fond du site changerait à chaque lancement.

BOSSES = [
    # (centre x, centre y, amplitude, étalement x, étalement y)
    (0.20, 0.62, 1.00, 0.26, 0.20),
    (0.38, 0.30, 0.72, 0.19, 0.16),
    (0.63, 0.55, 0.90, 0.24, 0.19),
    (0.82, 0.28, 0.58, 0.17, 0.15),
    (0.90, 0.72, 0.66, 0.20, 0.17),
    (0.48, 0.82, 0.44, 0.22, 0.14),
    (0.08, 0.20, 0.38, 0.15, 0.13),
    (0.70, 0.05, 0.30, 0.18, 0.12),
]

NX, NY = 260, 170
NIVEAUX = 30
MAITRESSE = 5
LARGEUR_SVG, HAUTEUR_SVG = 1600, 1000

TABLE = {
    0: [], 15: [],
    1: [(3, 0)], 14: [(3, 0)],
    2: [(0, 1)], 13: [(0, 1)],
    3: [(3, 1)], 12: [(3, 1)],
    4: [(1, 2)], 11: [(1, 2)],
    6: [(0, 2)], 9: [(0, 2)],
    7: [(3, 2)], 8: [(3, 2)],
    5: [(3, 2), (0, 1)],
    10: [(3, 0), (1, 2)],
}


def altitude(x, y):
    h = 0.0
    for cx, cy, amp, sx, sy in BOSSES:
        dx = (x - cx) / sx
        dy = (y - cy) / sy
        h += amp * math.exp(-(dx * dx + dy * dy))
    return h


def point_sur_cote(cote, x0, y0, x1, y1, v, niveau):
    """Position exacte du passage de la courbe sur un côté de la case.

    On interpole : la courbe ne passe pas au milieu du côté, mais là où
    l'altitude vaut exactement le niveau cherché.
    """
    def t(va, vb):
        if abs(vb - va) < 1e-12:
            return 0.5
        return min(1.0, max(0.0, (niveau - va) / (vb - va)))

    hg, hd, bd, bg = v
    if cote == 0:
        return (x0 + (x1 - x0) * t(hg, hd), y0)
    if cote == 1:
        return (x1, y0 + (y1 - y0) * t(hd, bd))
    if cote == 2:
        return (x0 + (x1 - x0) * t(bg, bd), y1)
    return (x0, y0 + (y1 - y0) * t(hg, bg))


def segments_du_niveau(grille, niveau):
    segments = []
    pas_x = LARGEUR_SVG / (NX - 1)
    pas_y = HAUTEUR_SVG / (NY - 1)
    for j in range(NY - 1):
        for i in range(NX - 1):
            hg, hd = grille[j][i], grille[j][i + 1]
            bd, bg = grille[j + 1][i + 1], grille[j + 1][i]
            cas = 0
            if hg > niveau: cas |= 1
            if hd > niveau: cas |= 2
            if bd > niveau: cas |= 4
            if bg > niveau: cas |= 8
            paires = TABLE.get(cas)
            if not paires:
                continue
            x0, y0 = i * pas_x, j * pas_y
            x1, y1 = (i + 1) * pas_x, (j + 1) * pas_y
            v = (hg, hd, bd, bg)
            for a, b in paires:
                segments.append((point_sur_cote(a, x0, y0, x1, y1, v, niveau),
                                 point_sur_cote(b, x0, y0, x1, y1, v, niveau)))
    return segments


def chainer(segments):
    """Recoud les segments bout à bout en polylignes continues.

    Sans cette étape, une courbe serait faite de milliers de traits
    indépendants : dix fois plus lourd, et des micro-trous au rendu.
    """
    def cle(p):
        return (round(p[0], 2), round(p[1], 2))

    voisins = {}
    for a, b in segments:
        voisins.setdefault(cle(a), []).append((a, b))
        voisins.setdefault(cle(b), []).append((b, a))

    utilises = set()
    chaines = []
    for liste in voisins.values():
        for seg in liste:
            ident = (cle(seg[0]), cle(seg[1]))
            if ident in utilises or (ident[1], ident[0]) in utilises:
                continue
            chaine = [seg[0], seg[1]]
            utilises.add(ident)
            avance = True
            while avance:
                avance = False
                for suivant in voisins.get(cle(chaine[-1]), []):
                    id2 = (cle(suivant[0]), cle(suivant[1]))
                    if id2 in utilises or (id2[1], id2[0]) in utilises:
                        continue
                    chaine.append(suivant[1])
                    utilises.add(id2)
                    avance = True
                    break
            if len(chaine) > 3:
                chaines.append(chaine)
    return chaines


def simplifier(points, epsilon=1.1):
    """Allège une polyligne (Ramer-Douglas-Peucker).

    Marching squares produit un point par case traversée : des milliers
    de points quasi alignés. On ne garde que ceux qui s'écartent de plus
    de `epsilon` pixels de la corde. Tracé identique à l'œil, fichier
    treize fois plus léger.
    """
    if len(points) < 3:
        return points
    ax, ay = points[0]
    bx, by = points[-1]
    dx, dy = bx - ax, by - ay
    norme = math.hypot(dx, dy)
    pire, indice = 0.0, 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        d = (math.hypot(px - ax, py - ay) if norme < 1e-9
             else abs(dy * px - dx * py + bx * ay - by * ax) / norme)
        if d > pire:
            pire, indice = d, i
    if pire <= epsilon:
        return [points[0], points[-1]]
    return simplifier(points[:indice + 1], epsilon)[:-1] + simplifier(points[indice:], epsilon)


def courbes_de_niveau():
    """Renvoie [(n, maitresse, [(x, y), ...]), ...] pour tous les niveaux."""
    grille = [[altitude(i / (NX - 1), j / (NY - 1)) for i in range(NX)]
              for j in range(NY)]
    plancher = min(min(l) for l in grille)
    plafond = max(max(l) for l in grille)
    sortie = []
    for n in range(1, NIVEAUX):
        niveau = plancher + (plafond - plancher) * n / NIVEAUX
        for chaine in chainer(segments_du_niveau(grille, niveau)):
            allegee = simplifier(chaine)
            if len(allegee) >= 3:
                sortie.append((n, n % MAITRESSE == 0, allegee))
    return sortie


def svg_relief(courbes, couleur, opacite_base):
    """Tirage statique du relief : sert de fond de plaque, et de secours
    si le canvas n'est pas disponible."""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LARGEUR_SVG} {HAUTEUR_SVG}" '
        f'width="{LARGEUR_SVG}" height="{HAUTEUR_SVG}" fill="none" stroke="{couleur}" '
        'stroke-linecap="round" stroke-linejoin="round">',
        '<title>Lignes de niveau : relief calculé</title>'
    ]
    par_niveau = {}
    for n, maitresse, pts in courbes:
        par_niveau.setdefault((n, maitresse), []).append(pts)
    for (n, maitresse), lignes in sorted(par_niveau.items()):
        d = ''.join('<path d="M' + 'L'.join(f'{x:.0f} {y:.0f}' for x, y in p) + '"/>'
                    for p in lignes)
        parts.append(f'<g stroke-width="{1.6 if maitresse else 0.85}" '
                     f'opacity="{opacite_base * (1 if maitresse else .6):.3f}">{d}</g>')
    parts.append('</svg>')
    return '\n'.join(parts)


def json_relief(courbes):
    """Le même relief, mais en données, pour que le canvas l'anime.

    Format volontairement compact : les coordonnées sont des entiers à
    plat, pas des objets. Sur 30 niveaux, cela fait la différence entre
    un fichier de 40 Ko et un de 15.
    """
    lignes = [{'n': n, 'm': 1 if maitresse else 0,
               'p': [int(round(v)) for xy in pts for v in xy]}
              for n, maitresse, pts in courbes]
    return json.dumps({'w': LARGEUR_SVG, 'h': HAUTEUR_SVG,
                       'niveaux': NIVEAUX, 'c': lignes},
                      separators=(',', ':'))


# =====================================================================
# 2. LA ROSE DES VENTS : ornement calculé, pas dessiné
# =====================================================================

def rose_des_vents(taille=600):
    """Une rose des vents à seize aires, en tracé pur.

    Trois rangs de pointes : quatre cardinales longues, quatre
    ordinales, huit intermédiaires courtes. Chaque pointe est un
    losange formé de deux triangles, dont l'un est légèrement teinté :
    c'est ce contraste qui donne le relief d'une gravure.
    """
    c = taille / 2
    p = []
    P = p.append

    P(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {taille} {taille}" '
      'fill="none" stroke="currentColor">')
    P('<title>Rose des vents</title>')

    # --- Cercles concentriques et graduation ---------------------------
    for r, op, w in ((0.97, .25, 1), (0.92, .5, 1), (0.62, .2, 1), (0.30, .3, 1), (0.10, .5, 1)):
        P(f'<circle cx="{c:.1f}" cy="{c:.1f}" r="{c * r:.1f}" opacity="{op}" stroke-width="{w}"/>')

    # Graduation : un trait tous les 5°, plus long tous les 15°
    for deg in range(0, 360, 5):
        a = math.radians(deg)
        long_ = 0.055 if deg % 15 == 0 else 0.028
        r1, r2 = c * 0.92, c * (0.92 - long_)
        x1, y1 = c + r1 * math.sin(a), c - r1 * math.cos(a)
        x2, y2 = c + r2 * math.sin(a), c - r2 * math.cos(a)
        op = .55 if deg % 15 == 0 else .28
        P(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
          f'opacity="{op}" stroke-width="1"/>')

    # --- Les pointes ----------------------------------------------------
    # (nombre d'aires, rayon de pointe, rayon d'épaule, opacité)
    rangs = ((16, 0.44, 0.085, .35), (8, 0.66, 0.10, .55), (4, 0.90, 0.13, .9))
    for aires, rayon, epaule, op in rangs:
        pas = 360 / aires
        for k in range(aires):
            deg = k * pas
            # on ne redessine pas les directions déjà couvertes par un rang plus long
            if aires == 16 and deg % 45 == 0:
                continue
            if aires == 8 and deg % 90 == 0:
                continue
            a = math.radians(deg)
            ag = math.radians(deg - pas / 2)
            ad = math.radians(deg + pas / 2)
            tx, ty = c + c * rayon * math.sin(a), c - c * rayon * math.cos(a)
            gx, gy = c + c * epaule * math.sin(ag), c - c * epaule * math.cos(ag)
            dx, dy = c + c * epaule * math.sin(ad), c - c * epaule * math.cos(ad)
            # aile gauche pleine, aile droite en trait : l'effet de gravure
            P(f'<path d="M{c:.1f} {c:.1f}L{gx:.1f} {gy:.1f}L{tx:.1f} {ty:.1f}Z" '
              f'fill="currentColor" fill-opacity="{op * .22:.3f}" stroke-width="1" opacity="{op}"/>')
            P(f'<path d="M{c:.1f} {c:.1f}L{dx:.1f} {dy:.1f}L{tx:.1f} {ty:.1f}Z" '
              f'stroke-width="1" opacity="{op * .75:.3f}"/>')

    # --- Les lettres cardinales ------------------------------------------
    for deg, lettre in ((0, 'N'), (90, 'E'), (180, 'S'), (270, 'O')):
        a = math.radians(deg)
        r = c * 0.985
        x, y = c + r * math.sin(a), c - r * math.cos(a)
        P(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle" '
          f'font-family="Chakra Petch, monospace" font-size="{taille * .052:.0f}" '
          'font-weight="600" letter-spacing="2" fill="currentColor" stroke="none" '
          f'opacity=".85">{lettre}</text>')

    P('</svg>')
    return '\n'.join(p)


# =====================================================================
# 2 bis. LE PARCELLAIRE : les neuf réalisations dessinées comme un plan
# =====================================================================
#
# On part d'un quadrilatère et on le divise par coupes successives,
# chaque coupe allant d'un bord à l'autre. C'est la méthode dite « en
# guillotine ». Son intérêt tient à un détail : les deux parcelles nées
# d'une coupe PARTAGENT les points de coupe. Aucun interstice ne peut
# donc s'ouvrir entre voisines, quelle que soit l'irrégularité des
# angles, alors qu'un découpage en rectangles déformés après coup en
# laisserait partout.

class Tirage:
    """Générateur pseudo-aléatoire à graine fixe.

    Le plan doit être identique à chaque génération : on ne peut pas
    utiliser le hasard du système, sinon le dessin changerait à chaque
    lancement du script.
    """

    def __init__(self, graine=20270605):
        self.e = graine

    def suivant(self):
        self.e = (1103515245 * self.e + 12345) % 2147483648
        return self.e / 2147483648

    def autour(self, ampleur):
        return (self.suivant() - 0.5) * 2 * ampleur


def _entre(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def couper(quad, ratio, vertical, tirage, gigue=0.035):
    """Coupe un quadrilatère en deux. Les points de coupe sont partagés.

    quad est donné dans l'ordre : haut-gauche, haut-droit, bas-droit,
    bas-gauche. La gigue incline légèrement la coupe : c'est elle qui
    donne au plan son air de relevé de terrain plutôt que de tableur.
    """
    hg, hd, bd, bg = quad
    d = tirage.autour(gigue)
    r1 = min(0.9, max(0.1, ratio + d))
    r2 = min(0.9, max(0.1, ratio - d))
    if vertical:
        a = _entre(hg, hd, r1)
        b = _entre(bg, bd, r2)
        return [hg, a, b, bg], [a, hd, bd, b]
    a = _entre(hg, bg, r1)
    b = _entre(hd, bd, r2)
    return [hg, hd, b, a], [a, b, bd, bg]


def _cote(quad):
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    return max(xs) - min(xs), max(ys) - min(ys)


def parceller(elements, quad, tirage):
    """Répartit une liste d'éléments pondérés dans un quadrilatère."""
    if len(elements) == 1:
        return [(elements[0][0], quad)]

    total = sum(p for _, p in elements)
    cible = total / 2
    cumul, coupure = 0, 1
    for i, (_, p) in enumerate(elements):
        if cumul + p / 2 >= cible and i > 0:
            coupure = i
            break
        cumul += p
    coupure = min(max(coupure, 1), len(elements) - 1)

    g1, g2 = elements[:coupure], elements[coupure:]
    p1 = sum(p for _, p in g1)
    ratio = p1 / total

    largeur, hauteur = _cote(quad)
    q1, q2 = couper(quad, ratio, largeur >= hauteur, tirage)
    return parceller(g1, q1, tirage) + parceller(g2, q2, tirage)


def _centre(quad):
    return (sum(p[0] for p in quad) / 4, sum(p[1] for p in quad) / 4)


def parcellaire_svg(parcelles, sections, largeur=1200, hauteur=560):
    """Le plan de bornage des réalisations, en SVG cliquable."""
    tirage = Tirage()
    m = 26
    cadre = [(m, m), (largeur - m, m + 4), (largeur - m - 3, hauteur - m), (m + 5, hauteur - m - 4)]

    # Premier partage : les zones, pondérées par leur nombre de parcelles.
    # La zone de seconde année n'a pas encore de parcelle : on lui réserve
    # tout de même son terrain, c'est plus honnête qu'une case absente.
    zones = []
    for s in sections:
        n = len([p for p in parcelles if p['section'] == s['id']])
        zones.append(((s, n), max(n, 1.6)))
    decoupe_zones = parceller(zones, cadre, tirage)

    p = []
    P = p.append
    P(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur}" '
      'class="parcellaire__svg" role="group" aria-label="Plan de bornage des neuf réalisations">')

    # Trame de fond
    P('<defs><pattern id="trameParc" width="26" height="26" patternUnits="userSpaceOnUse">'
      '<path d="M26 0H0V26" fill="none" stroke="currentColor" stroke-width=".4" opacity=".22"/>'
      '</pattern></defs>')
    P(f'<rect width="{largeur}" height="{hauteur}" fill="url(#trameParc)" opacity=".5"/>')

    for (s, n), quad in decoupe_zones:
        pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in quad)
        de_la_zone = [p_ for p_ in parcelles if p_['section'] == s['id']]

        # Le contour de zone, en trait fort
        P(f'<polygon points="{pts}" class="parcellaire__zone"/>')
        cx, cy = _centre(quad)

        if not de_la_zone:
            # Terrain réservé : hachuré, et dit comme tel
            P(f'<polygon points="{pts}" class="parcellaire__reserve"/>')
            P(f'<text x="{cx:.0f}" y="{cy - 6:.0f}" class="parcellaire__lettre" '
              'text-anchor="middle">RÉSERVE</text>')
            P(f'<text x="{cx:.0f}" y="{cy + 12:.0f}" class="parcellaire__mention" '
              'text-anchor="middle">seconde année</text>')
            continue

        # Puis les parcelles à l'intérieur de la zone
        for parcelle, sous_quad in parceller([(x, 1) for x in de_la_zone], quad, tirage):
            spts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in sous_quad)
            px, py = _centre(sous_quad)
            larg, haut = _cote(sous_quad)
            titre = f"Parcelle {parcelle['num']} : {parcelle['titreCourt']}"
            # data-comp permet au filtre par compétence d'agir aussi sur
            # cette vue : les deux représentations réagissent ensemble.
            P(f'<a href="{href_parcelle(parcelle)}" class="parcellaire__lien" '
              f'data-comp="{parcelle["competence"]}" aria-label="{echapper(titre)}">')
            P(f'<title>{echapper(titre)}</title>')
            P(f'<polygon points="{spts}" class="parcellaire__parcelle"/>')
            if larg > 74 and haut > 54:
                P(f'<text x="{px:.0f}" y="{py - 4:.0f}" class="parcellaire__num" '
                  f'text-anchor="middle">{parcelle["num"]}</text>')
                P(f'<text x="{px:.0f}" y="{py + 15:.0f}" class="parcellaire__mention" '
                  f'text-anchor="middle">C{parcelle["competence"]}</text>')
            else:
                P(f'<text x="{px:.0f}" y="{py + 4:.0f}" class="parcellaire__num" '
                  f'text-anchor="middle">{parcelle["num"]}</text>')
            P('</a>')

        # Le nom de la zone, en bandeau au bord haut du quadrilatère
        bx = (quad[0][0] + quad[1][0]) / 2
        by = quad[0][1] - 8
        P(f'<text x="{bx:.0f}" y="{by:.0f}" class="parcellaire__lettre" '
          f'text-anchor="middle">{echapper(s["court"].upper())}</text>')

    # Le point de station : d'où le relevé est pris
    P(f'<g class="parcellaire__station" transform="translate({largeur - 74},{hauteur - 52})">'
      '<circle r="17" fill="none" stroke="currentColor" stroke-width="1" opacity=".45"/>'
      '<circle r="9" fill="none" stroke="currentColor" stroke-width="1.4"/>'
      '<path d="M0 -24V24M-24 0H24" stroke="currentColor" stroke-width="1" opacity=".55"/>'
      '<circle r="2.6" fill="currentColor"/></g>')
    P(f'<text x="{largeur - 74}" y="{hauteur - 20}" class="parcellaire__mention" '
      'text-anchor="middle">STATION</text>')

    # L'échelle graphique
    P(f'<g transform="translate({m + 6},{hauteur - 16})">'
      '<rect width="40" height="5" fill="currentColor" opacity=".75"/>'
      '<rect x="40" width="40" height="5" fill="none" stroke="currentColor" stroke-width="1"/>'
      '<rect x="80" width="40" height="5" fill="currentColor" opacity=".75"/>'
      '</g>')
    # Aucune mention de proportionnalité : les neuf parcelles ont le même
    # poids, leurs surfaces sont donc équivalentes. Les faire dire autre
    # chose serait une jolie phrase et une fausse information.
    P(f'<text x="{m + 130}" y="{hauteur - 10}" class="parcellaire__mention">'
      'ÉCHELLE INDICATIVE · TROIS ZONES · NEUF PARCELLES BORNÉES</text>')

    P('</svg>')
    return '\n'.join(p)


def marque_svg():
    """Le viseur du géomètre : cercle et croix. Sert de favicon."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<g fill="none" stroke="#ffb03a" stroke-width="2.2" stroke-linecap="round">'
            '<circle cx="16" cy="16" r="8.5"/><path d="M16 2.5v27M2.5 16h27"/>'
            '</g></svg>')


# =====================================================================
# 3. GABARITS COMMUNS
# =====================================================================

TETE = '''<!DOCTYPE html>
<html lang="fr" data-racine="{{RACINE}}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITRE}}</title>
<meta name="description" content="{{DESCRIPTION}}">
<meta name="author" content="Maël Davidenko">
<meta name="theme-color" content="#0a0705">
<meta name="color-scheme" content="dark light">
<meta property="og:type" content="website">
<meta property="og:title" content="{{TITRE}}">
<meta property="og:description" content="{{DESCRIPTION}}">
<meta property="og:locale" content="fr_FR">
<link rel="icon" href="{{RACINE}}assets/marque.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;500;600;700&amp;family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..600&amp;family=Spectral:ital,wght@0,300;0,400;0,600;1,400&amp;display=swap">
<link rel="stylesheet" href="{{RACINE}}css/style.css">
<link rel="stylesheet" href="{{RACINE}}css/cadastre.css">
<link rel="stylesheet" href="{{RACINE}}css/impression.css">
<script>
/* Deux choses AVANT le premier rendu, pour eviter tout clignotement :
   1. la classe `js`, qui autorise les effets masquant du contenu ; sans
      elle, une page ouverte sans JavaScript s'affiche entierement ;
   2. le theme.

   Le theme se resout ici, et une fois pour toutes : un choix memorise
   s'il existe, sinon la preference du systeme. L'attribut data-theme est
   donc TOUJOURS pose, ce qui evite d'avoir a dupliquer la palette claire
   dans une media query. */
(function () {
  var r = document.documentElement;
  r.classList.add('js');
  var t = null;
  try { t = localStorage.getItem('cadastre.theme'); } catch (e) {}
  if (t !== 'papier' && t !== 'nuit') {
    t = (window.matchMedia && matchMedia('(prefers-color-scheme: light)').matches)
      ? 'papier' : 'nuit';
  }
  r.dataset.theme = t;
})();
</script>
</head>
<body{{CORPS_ATTRS}}>
<a class="evitement" href="#contenu">Aller au contenu</a>

<div class="scene" aria-hidden="true">
  <canvas id="relief"></canvas>
  <div class="scene__trame"></div>
  <div class="scene__lampe"></div>
  <div class="scene__grain"></div>
  <div class="scene__vignette"></div>
</div>

<div class="rail" aria-hidden="true">
  <div class="rail__ligne"></div>
  <div class="rail__graduation"></div>
  <span class="rail__borne rail__borne--haut">000</span>
  <span class="rail__valeur" data-role="rail-cote">000</span>
  <svg class="rail__curseur" data-role="rail-curseur" viewBox="0 0 15 15" fill="none" stroke="currentColor" stroke-width="1.4">
    <path d="M7.5 1.5 13.5 7.5 7.5 13.5 1.5 7.5Z"/><circle cx="7.5" cy="7.5" r="1.6" fill="currentColor"/>
  </svg>
  <span class="rail__borne rail__borne--bas">100</span>
</div>
'''

ENTETE = '''<header class="entete">
  <div class="enveloppe entete__interieur">
    <a class="marque" href="{{RACINE}}index.html">
      <svg class="marque__viseur" viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
        <circle class="anneau" cx="16" cy="16" r="8.5" stroke-dasharray="3.4 3"/>
        <path d="M16 3v26M3 16h26"/><circle cx="16" cy="16" r="1.8" fill="currentColor" stroke="none"/>
      </svg>
      <span class="marque__nom">Maël Davidenko<small>Cadastre · E5</small></span>
    </a>

    <nav class="nav" aria-label="Navigation principale">
      <a class="nav__lien" href="{{RACINE}}index.html#plan" data-section="plan">Le plan</a>
      <a class="nav__lien" href="{{RACINE}}index.html#realisations" data-section="realisations">Réalisations</a>
      <a class="nav__lien" href="{{RACINE}}index.html#competences" data-section="competences">Compétences</a>
      <a class="nav__lien" href="{{RACINE}}veille.html">Veille</a>
      <a class="nav__lien" href="{{RACINE}}parcours.html">Parcours</a>
      <a class="nav__lien" href="{{RACINE}}tableau-de-synthese.html">Tableau E5</a>
    </nav>

    <div class="outils">
      <div class="carnet">
        <button type="button" class="bouton" data-role="carnet" aria-expanded="false" aria-label="Carnet de relevé : parcelles déjà consultées">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 3h12l4 4v14H4z"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>
          <span data-role="carnet-compte">0/9</span>
        </button>
        <div class="carnet__panneau plaque" data-role="carnet-panneau" hidden>
          <div class="plaque__i">
            <p class="carnet__titre"><span class="hud hud--or">Carnet de relevé</span><span class="hud">local</span></p>
            <ul class="carnet__liste" data-role="carnet-liste"></ul>
            <div class="carnet__pied">
              <span class="hud">rien n'est envoyé</span>
              <button type="button" class="carnet__vider" data-role="carnet-vider">Effacer</button>
            </div>
          </div>
        </div>
      </div>
      <button type="button" class="bouton" data-role="theme" aria-label="Changer de thème">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M5 5l1.8 1.8M17.2 17.2 19 19M19 5l-1.8 1.8M6.8 17.2 5 19"/></svg>
        <span data-role="theme-libelle">Papier</span>
      </button>
    </div>
  </div>
</header>
'''

PIED = '''<footer class="pied">
  <div class="enveloppe">
    <div class="pied__grille">
      <div>
        <p class="hud hud--or pied__titre">Le cadastre</p>
        <ul class="pied__liste">
          <li><a href="{{RACINE}}index.html#plan">Plan de compétences</a></li>
          <li><a href="{{RACINE}}index.html#realisations">Les neuf réalisations</a></li>
          <li><a href="{{RACINE}}index.html#competences">Les six compétences</a></li>
          <li><a href="{{RACINE}}tableau-de-synthese.html">Tableau de synthèse E5</a></li>
        </ul>
      </div>
      <div>
        <p class="hud hud--or pied__titre">Le géomètre</p>
        <ul class="pied__liste">
          <li><a href="{{RACINE}}parcours.html">Parcours et certifications</a></li>
          <li><a href="{{RACINE}}veille.html">Veille technologique</a></li>
          <li><a href="{{GITHUB}}">Dépôt public</a></li>
        </ul>
      </div>
      <div>
        <p class="hud hud--or pied__titre">Cadre</p>
        <ul class="pied__liste">
          <li><a href="{{RACINE}}mentions-legales.html">Mentions légales</a></li>
        </ul>
        <p class="hud" style="margin-top:1rem;line-height:1.8">BTS SIO · option SLAM<br>Épreuve E5 · session 2027<br>Institution des Chartreux (SUP ALTA)</p>
      </div>
    </div>
    <div class="pied__bas">
      <p class="hud hud--or">⌖ 45°57′ N · 5°21′ E · Douvres, Ain</p>
      <p class="hud">Maël Davidenko · tous droits réservés</p>
    </div>
  </div>
</footer>
'''

SCRIPTS = '''<script src="{{RACINE}}js/parcelles.js"></script>
<script src="{{RACINE}}js/relief.js"></script>
<script src="{{RACINE}}js/script.js"></script>
<script src="{{RACINE}}js/cadastre.js"></script>
<script src="{{RACINE}}js/carnet.js"></script>
</body>
</html>
'''


def page(titre, description, corps, racine='', corps_attrs=''):
    entier = TETE + ENTETE + corps + PIED + SCRIPTS
    return remplir(entier,
                   TITRE=echapper(titre),
                   DESCRIPTION=echapper(description),
                   RACINE=racine,
                   CORPS_ATTRS=corps_attrs,
                   GITHUB=CANDIDAT.get('github', '#'))


# =====================================================================
# 4. FRAGMENTS
# =====================================================================

def plaque(contenu, classes='', attrs=''):
    """Une plaque chanfreinée : couche extérieure pour le filet, couche
    intérieure pour le fond. Voir .plaque dans style.css."""
    cls = ('plaque ' + classes).strip()
    return f'<div class="{cls}"{attrs}><div class="plaque__i">{contenu}</div></div>'


def plaque_lien(contenu, href, classes='', attrs=''):
    cls = ('plaque ' + classes).strip()
    return f'<a class="{cls}" href="{href}"{attrs}><span class="plaque__i">{contenu}</span></a>'



def lien_preuve(href, racine=''):
    """Un href de preuve est declare relatif a la racine du site.

    Les fiches vivant dans un sous-dossier, c'est ici qu'on prefixe, une
    fois pour toutes, plutot que de faire porter le chemin par les
    donnees. Les adresses absolues passent telles quelles.
    """
    if not href:
        return href
    if href.startswith(('http://', 'https://', 'mailto:', '#')):
        return href
    return racine + href


def fil_ariane(elements, racine):
    bouts = []
    for i, (libelle, href) in enumerate(elements):
        if i:
            bouts.append('<span class="hud sep" aria-hidden="true">/</span>')
        if href:
            bouts.append(f'<a class="hud" href="{racine}{href}">{echapper(libelle)}</a>')
        else:
            bouts.append(f'<span class="hud hud--or">{echapper(libelle)}</span>')
    return '<nav class="fil" aria-label="Fil d\'Ariane">' + ''.join(bouts) + '</nav>'


def relief_barres(n):
    return '<span class="relief" aria-hidden="true">' + '<i></i>' * min(n, 3) + '</span>'


def href_parcelle(p, racine=''):
    return f'{racine}parcelles/p{p["num"]}-{p["slug"]}.html'


def href_competence(c, racine=''):
    return f'{racine}competences/{c["slug"]}.html'


def titre_section(planche, titre, note, ancre=None):
    """L'en-tête d'une section : un grand numéro de planche en marge, le
    titre, puis une note qui dit à quoi sert la section. Le numéro en
    contour sert de repère visuel : on sait toujours où l'on est."""
    id_attr = f' id="{ancre}"' if ancre else ''
    return f'''<header class="section-tete revele"{id_attr}>
      <span class="section-tete__planche" aria-hidden="true">{planche}</span>
      <div class="section-tete__corps">
        <p class="hud hud--or section-tete__marque">Planche {planche}</p>
        <h2>{titre}</h2>
        <p class="section-tete__note">{note}</p>
      </div>
    </header>'''


def construire_plan(racine=''):
    """LE PLAN : le tableau de synthèse, en HTML sémantique.

    Écrit en dur dans la page. Le JavaScript ne fait que l'enrichir
    (visée, filtre, clavier). Sans JavaScript il reste entièrement
    lisible, navigable et imprimable.
    """
    lignes = []

    cols = []
    for c in COMPETENCES:
        n = COUVERTURE[c['code']]
        cols.append(f'''<th class="plan__col" scope="col" data-comp="{c['code']}">
          <a href="{href_competence(c, racine)}">
            <span class="plan__code">{c['code']}</span>
            <span class="plan__nom">{echapper(c['titre'])}</span>
            {relief_barres(n)}
            <span class="plan__compte">{n} réalisation{'s' if n > 1 else ''}</span>
          </a>
        </th>''')

    lignes.append('<thead><tr>')
    lignes.append('<th class="plan__coin" scope="col">'
                  '<span class="hud hud--vif">Réalisation professionnelle</span>'
                  '<span class="hud">↓ &nbsp;compétences mises en œuvre →</span></th>')
    lignes.extend(cols)
    lignes.append('</tr></thead><tbody>')

    for s in SECTIONS:
        lignes.append(f'''<tr class="plan__section"><th colspan="7" scope="colgroup">
          <span class="hud plan__section-titre">{echapper(s['titre'])}</span>
          <span class="plan__section-note">{echapper(s['note'])}</span>
        </th></tr>''')

        de_la_section = [p for p in PARCELLES if p['section'] == s['id']]
        if not de_la_section:
            vides = ''.join(f'<td class="plan__case" data-col="{c["code"]}"></td>' for c in COMPETENCES)
            lignes.append('<tr class="plan__ligne plan__ligne--vide">'
                          '<th class="plan__ligne-titre" scope="row">'
                          '<span class="hud">Aucune parcelle bornée à ce jour</span>'
                          '</th>' + vides + '</tr>')
            continue

        for p in de_la_section:
            cases = []
            for c in COMPETENCES:
                if c['code'] == p['competence']:
                    cases.append(f'''<td class="plan__case plan__case--borne" data-col="{c['code']}">
                      <a class="borne" href="{href_parcelle(p, racine)}">
                        <svg class="borne__reticule" viewBox="0 0 40 40" aria-hidden="true">
                          <circle class="borne__anneau" cx="20" cy="20" r="15.5"/>
                          <path class="borne__croix" d="M20 1v38M1 20h38"/>
                          <circle class="borne__cercle" cx="20" cy="20" r="9"/>
                          <circle class="borne__coeur" cx="20" cy="20" r="2.4"/>
                        </svg>
                        <span class="sr">Compétence {c['code']}, {echapper(c['titre'])}, mise en œuvre par la réalisation {p['num']}, {echapper(p['titreCourt'])}. Ouvrir la fiche.</span>
                      </a>
                    </td>''')
                else:
                    cases.append(f'<td class="plan__case" data-col="{c["code"]}"></td>')

            lignes.append(f'''<tr class="plan__ligne" data-comp="{p['competence']}" data-slug="{p['slug']}">
              <th class="plan__ligne-titre" scope="row">
                <a href="{href_parcelle(p, racine)}">
                  <span class="plan__num">{p['num']}</span>
                  <span class="plan__intitule"><span class="plan__long">{echapper(p['titre'])}</span><span class="plan__court">{echapper(p['titreCourt'])}</span></span>
                  <span class="plan__periode">{echapper(p['periodeCourte'])}</span>
                </a>
              </th>{''.join(cases)}
            </tr>''')

    lignes.append('</tbody>')

    filtres = ''.join(
        f'<button type="button" class="bouton" data-filtre-comp="{c["code"]}" '
        f'aria-pressed="false" title="{echapper(c["titre"])}">{c["code"]}</button>'
        for c in COMPETENCES)

    # Deux vues des mêmes données, dans la même section : le tableau
    # officiel, et le plan de bornage. Les deux sont écrites dans la
    # page ; le JavaScript n'en fait qu'un basculement. Sans script, on
    # voit les deux l'une sous l'autre : rien ne manque jamais.
    interieur = f'''<div class="plan-barre">
    <span class="hud">Vue</span>
    <div class="vues__choix" role="group" aria-label="Choisir la représentation">
      <button type="button" class="bouton" data-vue="tableau" aria-pressed="true">Tableau</button>
      <button type="button" class="bouton" data-vue="bornage" aria-pressed="false">Plan de bornage</button>
    </div>
    <p class="hud plan-barre__etat" data-role="plan-etat"><strong>9</strong> réalisations &nbsp;·&nbsp; <strong>6</strong> compétences couvertes sur 6</p>
    <span class="hud">Filtrer</span>
    {filtres}
  </div>

  <div class="vue" data-vue-contenu="tableau">
    <div class="plan-defile" data-role="plan-defile">
      <div class="visee visee--h" data-role="visee-h"></div>
      <div class="visee visee--v" data-role="visee-v"></div>
      <table class="plan" data-role="plan">
        <caption>Tableau de synthèse : chaque ligne est une réalisation professionnelle, chaque colonne une compétence du bloc 1. Une borne dans une case signifie que la réalisation met en œuvre cette compétence ; elle mène à la fiche détaillée.</caption>
        {''.join(lignes)}
      </table>
    </div>
  </div>

  <div class="vue" data-vue-contenu="bornage">
    <div class="parcellaire">
      {parcellaire_svg(PARCELLES, SECTIONS)}
      <p class="hud parcellaire__legende">Plan de bornage : chaque quadrilatère est une réalisation, chaque zone une période du tableau de synthèse. Le terrain hachuré reste à borner en seconde année.</p>
    </div>
  </div>'''

    return plaque(interieur, 'plan-cadre revele', ' data-role="vues"')


# =====================================================================
# 5. LES PAGES
# =====================================================================

def page_accueil():
    c = CANDIDAT

    chiffres = ''.join(plaque(
        f'''<span class="chiffre__fond"></span>
        <p class="chiffre__valeur"><span data-compteur="{echapper(x['valeur'])}">{echapper(x['valeur'])}</span><small>{echapper(x['unite'])}</small></p>
        <p class="hud chiffre__libelle">{echapper(x['libelle'])}</p>
        <p class="chiffre__detail">{echapper(x['detail'])}</p>''',
        'chiffre') for x in CHIFFRES)

    parcelles = ''.join(plaque_lien(
        f'''<span class="parcelle__lustre"></span>
        <span class="parcelle__tete">
          <span class="parcelle__num">{p['num']}</span>
          <span class="parcelle__comp">C{p['competence']}</span>
        </span>
        <span class="parcelle__titre">{echapper(p['titre'])}</span>
        <span class="parcelle__resume">{echapper(p['resume'])}</span>
        <span class="parcelle__pied">
          <span class="etat etat--{p['statut']}">{echapper(p['statutLibelle'])}</span>
          <span class="hud">{echapper(p['periodeCourte'])}</span>
        </span>
        <span class="jetons">{''.join(f'<span class="jeton">{echapper(t)}</span>' for t in p['technique'][:4])}</span>''',
        href_parcelle(p), 'parcelle', f' style="--i:{i}"') for i, p in enumerate(PARCELLES))

    terrain = ''.join(plaque_lien(
        f'''<span class="competence-carte__fond"></span>
        <span class="competence-carte__code">{x['code']}</span>
        <span class="competence-carte__titre">{echapper(x['titre'])}</span>
        <span class="competence-carte__devise">« {echapper(x['devise'])} »</span>
        <span class="hud competence-carte__compte">{COUVERTURE[x['code']]} réalisation{'s' if COUVERTURE[x['code']] > 1 else ''} · {len(x['sous'])} sous-compétences</span>''',
        href_competence(x), 'competence-carte', f' style="--i:{i}"') for i, x in enumerate(COMPETENCES))

    cartouche = ''.join(
        f'<div class="cartouche__champ"><span class="cartouche__cle">{echapper(k)}</span>'
        f'<span class="cartouche__valeur">{echapper(v)}</span></div>'
        for k, v in (
            ('Candidat', f"{c['nom']} {c['prenom']}"),
            ('Épreuve', c['epreuve']),
            ('Option', f"{c['option']} ({c['optionLongue']})"),
            ('Session', c['session']),
            ('Centre de formation', c['centre']),
            ('Milieu professionnel', 'Mairie de Douvres (Ain), 01/06/26 au 03/07/26, prolongé'),
        ))

    accroche = ''.join(f'<p>{echapper(x)}</p>' for x in c['accroche'])

    portes = ''.join(plaque_lien(
        f'''<span class="porte__num">{echapper(p['num'])}</span>
        <span class="porte__titre">{echapper(p['titre'])}</span>
        <span class="porte__texte">{echapper(p['texte'])}</span>
        <span class="hud porte__cible">{echapper(p['cible'])} →</span>''',
        p['href'], 'porte', f' style="--i:{i}"') for i, p in enumerate(PORTES))

    corps = f'''<main id="contenu">

  <section class="couverture">
    <div class="rose" aria-hidden="true">{rose_des_vents(600)}</div>
    <div class="enveloppe">
      <p class="couverture__releve">
        <span class="hud hud--or">⌖ {echapper(c['coordonnees'])}</span>
        <span class="hud">{echapper(c['lieu'])}</span>
        <span class="hud">{echapper(c['altitude'])}</span>
        <span class="hud">Planche 00</span>
      </p>

      <h1 class="couverture__nom">
        <span class="sur">Portfolio professionnel de</span>
        <span class="grand" data-texte="Maël Davidenko">Maël Davidenko</span>
      </h1>
      <p class="couverture__baseline">{echapper(c['baseline'])}</p>
      <p class="couverture__qualite">
        <span class="hud">{echapper(c['diplome'])}</span>
        <span class="hud">Option {echapper(c['option'])}</span>
        <span class="hud">{echapper(c['annee'])}</span>
        <span class="hud">Session {echapper(c['session'])}</span>
      </p>

      <div class="couverture__corps">
        <div>
          <div class="couverture__accroche">{accroche}</div>
          <blockquote class="couverture__citation">
            <p>« {echapper(c['phrase'])} »</p>
            <footer class="hud">{echapper(c['phraseSource'])}</footer>
          </blockquote>
        </div>
        <div class="chiffres">{chiffres}</div>
      </div>
    </div>
  </section>

  <section class="section section--portes" id="entrees">
    <div class="enveloppe">
      <p class="hud portes__titre revele">Trois façons de lire ce dossier</p>
      <div class="portes revele revele--decale">{portes}</div>
    </div>
  </section>

  <section class="section">
    <div class="enveloppe">
      {titre_section('01', 'Le plan de compétences',
        "Le tableau de synthèse officiel de l'épreuve E5, rendu arpentable. Chaque ligne est une "
        "réalisation, chaque colonne une compétence du bloc 1, et <strong>chaque borne est un "
        "chemin</strong> vers la fiche détaillée. Survolez une case pour prendre la visée, filtrez "
        "par compétence, ou basculez sur le plan de bornage.", 'plan')}
      {construire_plan()}
    </div>
  </section>

  <section class="section">
    <div class="enveloppe">
      {titre_section('02', 'Les neuf réalisations',
        "Le détail de chaque travail : le besoin de départ, la démarche suivie, ce qui a été livré, "
        "les preuves associées et ce que j'en retiens. Six d'entre elles viennent d'un stage où il "
        "fallait sauver vingt-trois ans de mémoire d'un village : près de 4 000 articles et "
        "8 500 photographies.", 'realisations')}
      <div class="parcelles revele revele--decale">{parcelles}</div>
    </div>
  </section>

  <section class="section">
    <div class="enveloppe">
      {titre_section('03', 'Les six compétences',
        "Le bloc 1 du référentiel : « Support et mise à disposition de services informatiques ». "
        "Chaque compétence est adossée aux réalisations qui la mettent en œuvre, à leurs preuves, "
        "et aux indicateurs sur lesquels la commission apprécie le niveau de maîtrise.", 'competences')}
      <div class="terrain revele revele--decale">{terrain}</div>
    </div>
  </section>

  <section class="section section--serre">
    <div class="enveloppe">
      {plaque(f'<p class="hud hud--or" style="margin-bottom:.9rem">Cartouche de la planche</p><div class="cartouche__grille">{cartouche}</div>', 'cartouche revele')}
    </div>
  </section>

</main>
'''
    return page('Maël Davidenko - Portfolio E5 · Le Cadastre',
                "Portfolio de l'épreuve E5 du BTS SIO option SLAM. Neuf réalisations professionnelles, "
                "six compétences du bloc 1, un plan de compétences interactif.",
                corps)


def page_parcelle(p, precedente, suivante):
    racine = '../'
    comp = PAR_CODE[p['competence']]

    blocs = []
    for b in p['corps']:
        contenu = ''.join(f'<p>{x}</p>' for x in b.get('paras', []))
        if b.get('liste'):
            contenu += '<ul class="liste-plan">' + ''.join(f'<li>{x}</li>' for x in b['liste']) + '</ul>'
        blocs.append(f'<section class="bloc revele"><h2 class="bloc__titre">'
                     f'<span>{echapper(b["titre"])}</span></h2>{contenu}</section>')

    preuves = ''.join('<li>' + plaque(
        f'''<span class="preuve__titre">{('<a href="' + lien_preuve(x['href'], racine) + '">' + echapper(x['titre']) + '</a>') if x.get('href') else echapper(x['titre'])}</span>
        <span class="etat etat--{x['etat']}">{ETATS[x['etat']]}</span>
        <span class="hud preuve__type">{echapper(x['type'])}</span>
        {f'<span class="preuve__note">{echapper(x["note"])}</span>' if x.get('note') else ''}''',
        'preuve') + '</li>' for x in p['preuves'])

    prouve = ''.join(f'<li>{echapper(x)}</li>' for x in p['prouve'])
    jetons = ''.join(f'<span class="jeton">{echapper(t)}</span>' for t in p['technique'])


    # Une preuve qu'on voit vaut mieux qu'une preuve qu'il faut telecharger.
    illustrations = ''
    if p.get('illustrations'):
        figures = ''.join(
            f'''<figure class="illustration">
              <img src="{racine}{i['fichier']}" alt="{echapper(i['legende'])}" loading="lazy">
              <figcaption class="hud">{echapper(i['legende'])}</figcaption>
            </figure>''' for i in p['illustrations'])
        illustrations = (
            '<section class="bloc revele"><h2 class="bloc__titre">'
            '<span>En images</span></h2>' + figures + '</section>')

    voisines = ''
    if precedente:
        voisines += plaque_lien(
            f'<span class="hud">← Parcelle {precedente["num"]}</span>'
            f'<span class="voisine__titre">{echapper(precedente["titreCourt"])}</span>',
            href_parcelle(precedente, racine), 'voisine')
    if suivante:
        voisines += plaque_lien(
            f'<span class="hud">Parcelle {suivante["num"]} →</span>'
            f'<span class="voisine__titre">{echapper(suivante["titreCourt"])}</span>',
            href_parcelle(suivante, racine), 'voisine voisine--suivante')

    cartouche = ''.join(
        f'<div class="cartouche__champ"><span class="cartouche__cle">{echapper(k)}</span>'
        f'<span class="cartouche__valeur">{echapper(v)}</span></div>'
        for k, v in (
            ('Parcelle', f"n° {p['num']}"),
            ('Période', p['periode']),
            ('Lieu', p['lieu']),
            ('Rôle', p['role']),
            ('Compétence', f"{comp['code']} · {comp['court']}"),
            ('Preuves', f"{len(p['preuves'])} document{'s' if len(p['preuves']) > 1 else ''}"),
        ))

    corps = f'''<main id="contenu">
  <div class="enveloppe">
    {fil_ariane([('Cadastre', 'index.html'), ('Réalisations', 'index.html#realisations'), (f"Parcelle {p['num']}", None)], racine)}

    <header class="fiche__tete">
      <span class="fiche__numero">{p['num']}</span>
      <h1 class="fiche__titre">{echapper(p['titre'])}</h1>
      <p class="fiche__soustitre">{echapper(p['sousTitre'])}</p>
      <p class="fiche__resume">{echapper(p['resume'])}</p>
      <div class="rang" style="margin-top:1.4rem">
        <span class="etat etat--{p['statut']}">{echapper(p['statutLibelle'])}</span>
        <a class="etat etat--livre" href="{href_competence(comp, racine)}" style="text-decoration:none">Compétence {comp['code']}</a>
        <span class="hud">{echapper(p['periode'])}</span>
      </div>
    </header>

    <div class="fiche">
      <div>
        {''.join(blocs)}

        {illustrations}

        <section class="bloc revele">
          <h2 class="bloc__titre"><span>Les preuves</span></h2>
          <p>Les documents ci-dessous constituent les traces de cette réalisation. Leur état indique s'ils sont consultables ici, confidentiels, ou encore non publiés.</p>
          <ul class="preuves">{preuves}</ul>
        </section>

        <section class="bloc revele">
          <h2 class="bloc__titre"><span>Ce que cette réalisation démontre</span></h2>
          {plaque(f'<p class="hud hud--or encart__titre">Compétence {comp["code"]} : {echapper(comp["titre"])}</p><ul class="liste-plan">{prouve}</ul>', 'encart')}
          <div class="enseignement">
            <p class="hud">Ce que j'en retiens</p>
            <p>« {echapper(p['enseignement'])} »</p>
          </div>
        </section>
      </div>

      <aside class="fiche__marge">
        {plaque(f'<p class="hud hud--or">Cartouche de la parcelle</p><div class="cartouche__grille">{cartouche}</div><p class="hud" style="margin:1.2rem 0 .6rem">Environnement technologique</p><div class="jetons">{jetons}</div>', 'cartouche')}
      </aside>
    </div>

    <nav class="voisines" aria-label="Parcelles voisines">{voisines}</nav>
  </div>
</main>
'''
    return page(f"Parcelle {p['num']} - {p['titreCourt']} · Portfolio E5",
                p['resume'][:180], corps, racine=racine,
                corps_attrs=f' data-parcelle="{p["slug"]}"')


def page_competence(c):
    racine = '../'
    liees = [p for p in PARCELLES if p['competence'] == c['code']]

    sous = ''.join(f'<li>{echapper(x)}</li>' for x in c['sous'])
    indics = ''.join(f'<li>{echapper(x)}</li>' for x in c['indicateurs'])

    cartes = ''.join(plaque_lien(
        f'''<span class="parcelle__lustre"></span>
        <span class="parcelle__tete">
          <span class="parcelle__num">{p['num']}</span>
          <span class="parcelle__comp">C{p['competence']}</span>
        </span>
        <span class="parcelle__titre">{echapper(p['titre'])}</span>
        <span class="parcelle__resume">{echapper(p['resume'])}</span>
        <span class="parcelle__pied">
          <span class="etat etat--{p['statut']}">{echapper(p['statutLibelle'])}</span>
          <span class="hud">{echapper(p['periodeCourte'])}</span>
        </span>''',
        href_parcelle(p, racine), 'parcelle') for p in liees)

    preuves_liees = ''.join('<li>' + plaque(
        f'''<span class="preuve__titre">{('<a href="' + lien_preuve(x['href'], racine) + '">' + echapper(x['titre']) + '</a>') if x.get('href') else echapper(x['titre'])}</span>
        <span class="etat etat--{x['etat']}">{ETATS[x['etat']]}</span>
        <span class="hud preuve__type">Parcelle {p['num']} · {echapper(x['type'])}</span>''',
        'preuve') + '</li>' for p in liees for x in p['preuves'])

    cartouche = ''.join(
        f'<div class="cartouche__champ"><span class="cartouche__cle">{echapper(k)}</span>'
        f'<span class="cartouche__valeur">{echapper(v)}</span></div>'
        for k, v in (
            ('Code', c['code']),
            ('Bloc', '1 : Support et mise à disposition de services informatiques'),
            ('Sous-compétences', str(len(c['sous']))),
            ('Couverture', f"{len(liees)} réalisation{'s' if len(liees) > 1 else ''}"),
        ))

    corps = f'''<main id="contenu">
  <div class="enveloppe">
    {fil_ariane([('Cadastre', 'index.html'), ('Compétences', 'index.html#competences'), (f"Compétence {c['code']}", None)], racine)}

    <header class="fiche__tete">
      <span class="fiche__numero">{c['code']}</span>
      <h1 class="fiche__titre">{echapper(c['titre'])}</h1>
      <p class="fiche__soustitre">« {echapper(c['devise'])} »</p>
      <p class="fiche__resume">Compétence du bloc 1 : Support et mise à disposition de services informatiques. Couverte par {len(liees)} réalisation{'s' if len(liees) > 1 else ''} de mon tableau de synthèse.</p>
    </header>

    <div class="fiche">
      <div>
        <section class="bloc revele">
          <h2 class="bloc__titre"><span>Ce que le référentiel demande</span></h2>
          <p>Les sous-compétences telles qu'elles figurent au référentiel du BTS SIO.</p>
          <ul class="liste-plan">{sous}</ul>
        </section>

        <section class="bloc revele">
          <h2 class="bloc__titre"><span>Mes réalisations pour cette compétence</span></h2>
          <div class="parcelles" style="margin-top:1.2rem">{cartes}</div>
        </section>

        <section class="bloc revele">
          <h2 class="bloc__titre"><span>Les preuves rattachées</span></h2>
          <ul class="preuves">{preuves_liees}</ul>
        </section>

        <section class="bloc revele">
          <h2 class="bloc__titre"><span>Indicateurs de performance</span></h2>
          <p>Les critères sur lesquels la commission d'interrogation apprécie le niveau de maîtrise.</p>
          {plaque(f'<p class="hud hud--or encart__titre">Référentiel E5 · compétence {c["code"]}</p><ul class="liste-plan">{indics}</ul>', 'encart')}
        </section>
      </div>

      <aside class="fiche__marge">
        {plaque(f'<p class="hud hud--or">Cartouche de la compétence</p><div class="cartouche__grille">{cartouche}</div><p class="hud" style="margin:1.2rem 0 .6rem">Relief de couverture</p>{relief_barres(len(liees))}', 'cartouche')}
      </aside>
    </div>
  </div>
</main>
'''
    return page(f"Compétence {c['code']} - {c['titre']} · Portfolio E5",
                f"Compétence {c['code']} du bloc 1 du BTS SIO : {c['titre']}. "
                "Réalisations, preuves et indicateurs de performance.",
                corps, racine=racine)


def rendre_bloc(b, racine=''):
    """Rend un bloc de contenu rédigé.

    Les champs `aCompleter` du JSON ne sont volontairement PAS rendus :
    ce sont des notes de travail, elles n'ont rien à faire sur le site
    public. Elles ressortent dans A-FAIRE.md.
    """
    m = []
    if b.get('titre'):
        m.append(f'<h2 class="bloc__titre"><span>{echapper(b["titre"])}</span></h2>')
    for p in b.get('paras', []):
        m.append(f'<p>{p}</p>')
    if b.get('liste'):
        m.append('<ul class="liste-plan">' + ''.join(f'<li>{x}</li>' for x in b['liste']) + '</ul>')

    if b.get('tableau'):
        t = b['tableau']
        entetes = ''.join(f'<th scope="col">{echapper(c)}</th>' for c in t['colonnes'])
        corps = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in ligne) + '</tr>'
                        for ligne in t['lignes'])
        m.append(plaque(f'<table class="tableau-simple"><thead><tr>{entetes}</tr></thead>'
                        f'<tbody>{corps}</tbody></table>', 'tableau-cadre'))

    for c in b.get('certifications', []):
        m.append(plaque(
            f'''<div class="certif__tete">
              <span class="certif__organisme">{echapper(c['organisme'])}</span>
              <span class="hud">{echapper(c['date'])}</span>
            </div>
            <h3 class="certif__intitule">{echapper(c['intitule'])}</h3>
            <p class="hud">{echapper(c['plateforme'])}</p>
            <p class="certif__note">{echapper(c['note'])}</p>''', 'certif'))

    for l in b.get('liens', []):
        m.append(f'<p><a class="lien" href="{CANDIDAT.get(l["cle"], "#")}">'
                 f'{echapper(l["libelle"])}</a></p>')

    if b.get('apres'):
        m.append(f'<p>{b["apres"]}</p>')

    if b.get('lienParcelle'):
        m.append(f'<p><a class="lien" href="{racine}parcelles/{b["lienParcelle"]}.html">'
                 'Voir la fiche complète de cette réalisation →</a></p>')

    return '<section class="bloc revele">' + ''.join(m) + '</section>'


def page_redigee(pg):
    racine = ''
    cartouche = ''.join(
        f'<div class="cartouche__champ"><span class="cartouche__cle">{echapper(k)}</span>'
        f'<span class="cartouche__valeur">{echapper(v)}</span></div>'
        for k, v in pg.get('cartouche', []))

    corps = f'''<main id="contenu">
  <div class="enveloppe">
    {fil_ariane([('Cadastre', 'index.html'), (pg['titre'], None)], racine)}

    <header class="fiche__tete">
      <span class="fiche__numero">{echapper(pg['numero'])}</span>
      <h1 class="fiche__titre">{echapper(pg['titre'])}</h1>
      <p class="fiche__soustitre">{echapper(pg['sousTitre'])}</p>
      <p class="fiche__resume">{echapper(pg['resume'])}</p>
    </header>

    <div class="fiche">
      <div>{''.join(rendre_bloc(b, racine) for b in pg['corps'])}</div>
      <aside class="fiche__marge">
        {plaque(f'<p class="hud hud--or">Cartouche</p><div class="cartouche__grille">{cartouche}</div>', 'cartouche')}
      </aside>
    </div>
  </div>
</main>
'''
    return page(f"{pg['titre']} - Maël Davidenko", pg['description'], corps, racine=racine)


def page_tableau():
    c = CANDIDAT
    # Chaque piece annonce son poids : la commission sait ce qu'elle
    # telecharge avant de cliquer.
    def poids(rel):
        f = chemin(*rel.split('/'))
        if not os.path.exists(f):
            return ''
        o = os.path.getsize(f)
        return f'{o / 1048576:.1f} Mo' if o > 1048576 else f'{o / 1024:.0f} Ko'

    dossier = ''.join(plaque_lien(
        f'''<span class="dossier__tete">
          <span class="dossier__titre">{echapper(x['titre'])}</span>
          <span class="hud dossier__poids">{poids(x['fichier'])}</span>
        </span>
        <span class="hud dossier__type">{echapper(x['type'])}</span>
        <span class="dossier__note">{echapper(x['note'])}</span>''',
        x['fichier'], 'dossier__piece', f' style="--i:{i}" download')
        for i, x in enumerate(DOSSIER))

    cartouche = ''.join(
        f'<div class="cartouche__champ"><span class="cartouche__cle">{echapper(k)}</span>'
        f'<span class="cartouche__valeur">{v}</span></div>'
        for k, v in (
            ('Nom et prénom', echapper(f"{c['nom']} {c['prenom']}")),
            ('N° candidat', '<span class="discret">à compléter</span>'),
            ('Option', '▢ SISR &nbsp;&nbsp; ☒ SLAM'),
            ('Session', echapper(c['session'])),
            ('Centre de formation', echapper(c['centre'])),
            ('Adresse URL du portfolio', '<a class="lien" href="https://picsou01.github.io/portefolio/">picsou01.github.io/portefolio</a>'),
        ))

    corps = f'''<main id="contenu">
  <div class="enveloppe">
    {fil_ariane([('Cadastre', 'index.html'), ('Tableau de synthèse', None)], '')}

    <header class="fiche__tete">
      <h1 class="fiche__titre">Tableau de synthèse des réalisations professionnelles</h1>
      <p class="fiche__soustitre">BTS Services informatiques aux organisations, session {echapper(c['session'])}</p>
      <p class="fiche__resume">Version en ligne et arpentable du tableau de synthèse officiel de l'épreuve E5. Il reprend à l'identique les réalisations, les périodes et les compétences cochées du document remis à la commission.</p>
    </header>

    <div style="margin-block:1.8rem">
      {plaque(f'<div class="cartouche__grille">{cartouche}</div>', 'cartouche revele')}
    </div>

    {construire_plan()}

    <section class="section section--serre" style="padding-top:2.6rem">
      <p class="hud hud--or" style="margin-bottom:1rem">Les pièces du dossier</p>
      <div class="dossier revele revele--decale">{dossier}</div>
    </section>

    <div style="margin-top:1.8rem">
      {plaque('<p class="hud hud--or encart__titre">Note à l\'attention de la commission</p><p>Ce tableau est identique au document remis. Chaque borne est cliquable : elle mène à la fiche détaillée de la réalisation, avec son contexte, la démarche suivie, les preuves associées et leur état de disponibilité. Les preuves confidentielles sont signalées comme telles et restent consultables sur demande auprès de la Mairie de Douvres.</p>', 'encart revele')}
    </div>
  </div>
</main>
'''
    return page('Tableau de synthèse E5 - Maël Davidenko',
                "Tableau de synthèse officiel des réalisations professionnelles de l'épreuve E5, rendu interactif.",
                corps)


def index_parcelles_js():
    entrees = ',\n'.join(
        '    { slug: "%s", num: "%s", titre: "%s", href: "%s" }'
        % (p['slug'], p['num'], p['titreCourt'].replace('"', '\\"'), href_parcelle(p))
        for p in PARCELLES)
    return ('/* Généré par outils/arpenteur.py, ne pas modifier à la main. */\n'
            'window.CADASTRE_PARCELLES = [\n' + entrees + '\n];\n')


# =====================================================================
# 6. EXÉCUTION
# =====================================================================

ETATS = {
    'en-ligne': 'Consultable',
    'confidentiel': 'Sur demande',
    'a-deposer': 'Non publié',
    'livre': 'Livré',
}

if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    print("\n  L'ARPENTEUR · génération du cadastre\n  " + '-' * 44)

    donnees = lire_json('donnees/cadastre.json')
    parcelles_json = lire_json('donnees/parcelles.json')
    pages_json = lire_json('donnees/pages.json')

    CANDIDAT = donnees['candidat']
    CHIFFRES = donnees['chiffres']
    PORTES = donnees['portes']
    DOSSIER = donnees['dossier']
    COMPETENCES = donnees['competences']
    SECTIONS = donnees['sections']
    PARCELLES = parcelles_json['parcelles']

    PAR_CODE = {c['code']: c for c in COMPETENCES}
    COUVERTURE = {c['code']: sum(1 for p in PARCELLES if p['competence'] == c['code'])
                  for c in COMPETENCES}

    # --- Contrôle de cohérence : mieux vaut échouer ici que devant le jury.
    erreurs = []
    for p in PARCELLES:
        if p['competence'] not in PAR_CODE:
            erreurs.append(f"parcelle {p['num']} : compétence inconnue « {p['competence']} »")
        if p['section'] not in {s['id'] for s in SECTIONS}:
            erreurs.append(f"parcelle {p['num']} : section inconnue « {p['section']} »")
        for x in p['preuves']:
            if x['etat'] not in ETATS:
                erreurs.append(f"parcelle {p['num']} : état de preuve inconnu « {x['etat']} »")
    vides = [c['code'] for c in COMPETENCES if COUVERTURE[c['code']] == 0]
    if vides:
        erreurs.append('compétences non couvertes : ' + ', '.join(vides))
    if erreurs:
        print('\n  ARRÊT : incohérences dans les données :')
        for e in erreurs:
            print('   · ' + e)
        sys.exit(1)

    print(f'  {len(PARCELLES)} parcelles · {len(COMPETENCES)} compétences · '
          f'couverture {sum(1 for v in COUVERTURE.values() if v)}/6\n')

    # --- Les pièces graphiques calculées
    print('  Relief topographique (marching squares)…')
    courbes = courbes_de_niveau()
    print(f'    {len(courbes)} courbes, {sum(len(p) for _, _, p in courbes)} points')
    ecrire('assets/lignes-de-niveau.svg', svg_relief(courbes, '#4a3a22', 0.6))
    ecrire('assets/lignes-de-niveau-nuit.svg', svg_relief(courbes, '#ffc46a', 0.5))
    ecrire('assets/relief.json', json_relief(courbes))
    ecrire('assets/rose-des-vents.svg', rose_des_vents())
    ecrire('assets/marque.svg', marque_svg())

    ecrire('js/parcelles.js', index_parcelles_js())

    # --- Les pages
    ecrire('index.html', page_accueil())
    ecrire('tableau-de-synthese.html', page_tableau())
    for i, p in enumerate(PARCELLES):
        ecrire(f'parcelles/p{p["num"]}-{p["slug"]}.html',
               page_parcelle(p,
                             PARCELLES[i - 1] if i > 0 else None,
                             PARCELLES[i + 1] if i < len(PARCELLES) - 1 else None))
    for c in COMPETENCES:
        ecrire(f'competences/{c["slug"]}.html', page_competence(c))
    for pg in pages_json['pages']:
        ecrire(pg['fichier'], page_redigee(pg))

    # --- Le relevé de ce qui manque, hors du site public
    manquants = [f"- [ ] **Parcelle {p['num']} · {p['titreCourt']}** : {x['titre']} *({x['type']})*"
                 + (f" ({x['note']})" if x.get('note') else '')
                 for p in PARCELLES for x in p['preuves'] if x['etat'] == 'a-deposer']
    a_completer = [f"- [ ] **{pg['titre']} › {b.get('titre', '(sans titre)')}** : "
                   + sans_balises(b['aCompleter'])
                   for pg in pages_json['pages'] for b in pg['corps'] if b.get('aCompleter')]
    confidentiels = [f"- {p['titreCourt']} : {x['titre']}"
                     for p in PARCELLES for x in p['preuves'] if x['etat'] == 'confidentiel']

    ecrire('A-FAIRE.md',
           "# Ce qu'il reste à faire\n\n"
           "> Fichier régénéré à chaque `python outils/arpenteur.py`. Ne pas le modifier "
           "à la main : il découle de l'état des preuves déclaré dans `donnees/parcelles.json` "
           "et des notes `aCompleter` de `donnees/pages.json`.\n\n"
           "> Ces notes ne s'affichent **pas** sur le site : le portfolio public ne montre "
           "jamais ses coutures.\n\n"
           f'## Preuves à déposer ({len(manquants)})\n\n'
           "Déposer les fichiers dans `assets/preuves/`, puis passer l'état de `\"a-deposer\"` "
           "à `\"en-ligne\"` et ajouter un `\"href\"` dans `donnees/parcelles.json`.\n\n"
           + '\n'.join(manquants)
           + f'\n\n## Passages à rédiger ({len(a_completer)})\n\n' + '\n'.join(a_completer)
           + '\n\n## Preuves confidentielles : ne jamais publier\n\n' + '\n'.join(confidentiels)
           + "\n\nElles sont signalées « Sur demande » sur le site et restent consultables "
             "auprès de la Mairie de Douvres.\n")

    # --- Contrôle final : aucun lien interne ne doit pointer dans le vide.
    produites = [os.path.join(d, f)
                 for d, _, fs in os.walk(BASE)
                 if not any(x in d for x in ('.git', '.idea', '.claude', 'outils', 'bac-a-sable'))
                 for f in fs if f.endswith('.html')]
    casses = []
    for p in produites:
        with open(p, encoding='utf-8') as fh:
            texte = fh.read()
        for href in re.findall(r'(?:href|src)="([^"]*)"', texte):
            if not href or href.startswith(('http', 'mailto:', 'data:', '#', '//')):
                continue
            cible = os.path.normpath(os.path.join(os.path.dirname(p), href.split('#')[0]))
            if not os.path.exists(cible):
                casses.append((os.path.relpath(p, BASE), href))
    if casses:
        print(f'\n  ARRÊT : {len(casses)} lien(s) interne(s) cassé(s) :')
        for source, href in casses[:20]:
            print(f'   · {source} → {href}')
        sys.exit(1)

    # --- Règle de rédaction : aucun tiret long.
    # Seuls le trait d'union et le tiret bas sont admis. Un contrôle
    # automatique vaut mieux qu'une bonne résolution : la règle ne se
    # perdra pas au fil des retouches.
    INTERDITS = {
        '‐': 'HYPHEN', '‑': 'NON-BREAKING HYPHEN', '‒': 'FIGURE DASH',
        '–': 'EN DASH', '—': 'EM DASH', '―': 'HORIZONTAL BAR',
        '−': 'MINUS SIGN', '­': 'SOFT HYPHEN', '－': 'FULLWIDTH HYPHEN',
    }
    fautes = []
    for p_ in produites:
        with open(p_, encoding='utf-8') as fh:
            texte = fh.read()
        for ch, nom in INTERDITS.items():
            n = texte.count(ch)
            if n:
                i = texte.find(ch)
                fautes.append((os.path.relpath(p_, BASE), nom, n,
                               texte[max(0, i - 45):i + 45].replace('\n', ' ')))
    if fautes:
        print(f'\n  ARRÊT : tiret(s) long(s) dans {len(fautes)} fichier(s) :')
        for source, nom, n, extrait in fautes[:12]:
            print(f'   · {source} : {n} × {nom}')
            print(f'     …{extrait}…')
        sys.exit(1)

    total = 2 + len(PARCELLES) + len(COMPETENCES) + len(pages_json['pages'])
    print(f'\n  {len(produites)} pages contrôlées, aucun lien cassé.')
    print(f'  Cadastre levé : {total} pages. Ouvrir index.html.\n')
