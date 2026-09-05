/* =====================================================================
   LE CADASTRE - le relief vivant
   Rendu sur <canvas> des courbes de niveau calculées par
   outils/arpenteur.py et exportées dans assets/relief.json.

   POURQUOI UN CANVAS PLUTÔT QU'UNE IMAGE
   Une image de fond est morte : elle ne réagit à rien. Ici le relief
   est une donnée, pas un pixel. On peut donc :
     · le tracer progressivement au chargement, comme un relevé qui
       s'inscrit sous la plume ;
     · le faire réagir au pointeur, comme une main sous une feuille ;
     · le balayer d'une lumière, comme une lampe qu'on promène ;
     · le décomposer en trois plans de profondeur qui défilent à des
       vitesses différentes.

   COÛT
   Le fichier tient en quelques milliers de points. Une image par
   seconde coûte quelques milliers d'opérations : rien. Le rendu
   s'arrête dès que l'onglet passe en arrière-plan, et se réduit à un
   tracé unique et fixe si le visiteur a demandé moins d'animations.
   ===================================================================== */

(() => {
    'use strict';

    const toile = document.getElementById('relief');
    if (!toile || !toile.getContext) return;

    const ctx = toile.getContext('2d', { alpha: true });
    const racine = document.documentElement;
    const mouvementReduit = matchMedia('(prefers-reduced-motion: reduce)');

    /* -----------------------------------------------------------------
       Les couleurs viennent du CSS : le relief suit donc automatiquement
       la bascule jour / nuit, sans qu'aucune valeur ne soit dupliquée
       ici. On les relit à chaque changement de thème.
       ----------------------------------------------------------------- */
    let teinte = { froid: '150,120,70', chaud: '255,176,58', vif: '255,214,138' };

    function couleurCss(nom, secours) {
        const brut = getComputedStyle(racine).getPropertyValue(nom).trim();
        if (!brut) return secours;
        // On passe par le canvas pour normaliser n'importe quelle notation.
        const d = document.createElement('canvas').getContext('2d');
        d.fillStyle = '#000';
        d.fillStyle = brut;
        const m = d.fillStyle;
        if (m.startsWith('#')) {
            return [1, 3, 5].map((i) => parseInt(m.substr(i, 2), 16)).join(',');
        }
        const n = m.match(/[\d.]+/g);
        return n ? n.slice(0, 3).map(Number).join(',') : secours;
    }

    function relireCouleurs() {
        teinte = {
            froid: couleurCss('--trait-vif', '86,65,42'),
            chaud: couleurCss('--or', '255,176,58'),
            vif:   couleurCss('--or-clair', '255,214,138'),
        };
    }
    relireCouleurs();

    /* -----------------------------------------------------------------
       État
       ----------------------------------------------------------------- */
    let donnees = null;      // { w, h, niveaux, c: [{ n, m, p:[x,y,...] }] }
    let plans = [];          // les trois plans de profondeur
    let L = 0, H = 0, dpr = 1;
    let debut = 0;           // horodatage du premier tracé
    let defilement = 0;
    let pointeur = { x: -9999, y: -9999, force: 0 };
    let anime = 0;
    let nbPoints = 0;

    /* -----------------------------------------------------------------
       Mise à l'échelle : le relief est décrit dans un repère 1600×1000.
       On le cadre en « couvrir », puis on l'agrandit un peu pour que la
       parallaxe ait de la marge sans découvrir les bords.
       ----------------------------------------------------------------- */
    function cadrage() {
        const marge = 1.22;
        const e = Math.max(L / donnees.w, H / donnees.h) * marge;
        return { e, dx: (L - donnees.w * e) / 2, dy: (H - donnees.h * e) / 2 };
    }

    function redimensionner() {
        dpr = Math.min(devicePixelRatio || 1, 2);
        L = innerWidth;
        H = innerHeight;
        toile.width = Math.round(L * dpr);
        toile.height = Math.round(H * dpr);
        toile.style.width = L + 'px';
        toile.style.height = H + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    /* -----------------------------------------------------------------
       Répartition en trois plans.
       Les niveaux bas (les vallées, les grandes courbes enveloppantes)
       partent au fond ; les niveaux hauts (les sommets, les petites
       boucles serrées) viennent au premier plan. C'est ce qui donne la
       profondeur : le fond bouge peu, le premier plan bouge beaucoup.
       ----------------------------------------------------------------- */
    function repartir() {
        const N = donnees.niveaux;
        plans = [
            { lignes: [], parallaxe: 0.012, alpha: 0.30, trait: 0.7, teinte: 'froid' },
            { lignes: [], parallaxe: 0.035, alpha: 0.46, trait: 0.9, teinte: 'froid' },
            { lignes: [], parallaxe: 0.070, alpha: 0.62, trait: 1.1, teinte: 'chaud' },
        ];
        donnees.c.forEach((ligne, i) => {
            const part = ligne.n / N;
            const plan = part < 0.38 ? 0 : (part < 0.7 ? 1 : 2);
            // Ordre d'apparition : par altitude, avec un décalage stable
            // par ligne pour que le tracé ne monte pas comme un mur.
            ligne.apparition = part * 0.62 + ((i * 37) % 100) / 100 * 0.22;
            ligne.maitresse = ligne.m === 1;
            plans[plan].lignes.push(ligne);
            nbPoints += ligne.p.length / 2;
        });
    }

    /* -----------------------------------------------------------------
       Le tracé
       ----------------------------------------------------------------- */
    const RAYON_POINTEUR = 230;
    const POUSSEE = 16;

    function tracerPlan(plan, cadre, avancement, chaud) {
        const { e, dx, dy } = cadre;
        const decalage = defilement * plan.parallaxe;
        const interactif = pointeur.force > 0.01 && nbPoints < 26000;

        ctx.lineWidth = plan.trait;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';

        for (const ligne of plan.lignes) {
            // Fondu d'apparition, ligne par ligne
            const v = avancement >= 1 ? 1
                    : Math.max(0, Math.min(1, (avancement - ligne.apparition) / 0.3));
            if (v <= 0) continue;

            const base = plan.alpha * v * (ligne.maitresse ? 1 : 0.55);
            const t = chaud ? teinte.vif : teinte[plan.teinte];
            ctx.strokeStyle = `rgba(${t},${(chaud ? base * 1.5 : base).toFixed(3)})`;

            const p = ligne.p;
            ctx.beginPath();
            for (let i = 0; i < p.length; i += 2) {
                let x = p[i] * e + dx;
                let y = p[i + 1] * e + dy - decalage;

                if (interactif) {
                    const ax = x - pointeur.x;
                    const ay = y - pointeur.y;
                    const d2 = ax * ax + ay * ay;
                    if (d2 < RAYON_POINTEUR * RAYON_POINTEUR) {
                        const d = Math.sqrt(d2) || 1;
                        // (1 - d/R)² : l'effet s'éteint doucement sur le bord
                        const k = (1 - d / RAYON_POINTEUR);
                        const pousse = k * k * POUSSEE * pointeur.force;
                        x += (ax / d) * pousse;
                        y += (ay / d) * pousse;
                    }
                }

                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }
    }

    /* --- Le balayage : une lampe qui traverse le relevé ----------------- */
    const PERIODE_BALAYAGE = 11000;
    const LARGEUR_BALAYAGE = 230;

    function tracer(temps) {
        if (!donnees) return;
        if (!debut) debut = temps;

        const ecoule = temps - debut;
        const statique = mouvementReduit.matches;
        const avancement = statique ? 1 : Math.min(1, ecoule / 2600);

        ctx.clearRect(0, 0, L, H);
        const cadre = cadrage();

        for (const plan of plans) tracerPlan(plan, cadre, avancement, false);

        // Deuxième passe, découpée dans une bande étroite : les courbes
        // qui s'y trouvent sont retracées en clair, avec un halo. C'est
        // moins cher que de tester chaque point contre la bande.
        if (!statique && avancement >= 1) {
            const phase = (ecoule % PERIODE_BALAYAGE) / PERIODE_BALAYAGE;
            if (phase < 0.55) {
                const x = (phase / 0.55) * (L + LARGEUR_BALAYAGE * 2) - LARGEUR_BALAYAGE;
                ctx.save();
                ctx.beginPath();
                ctx.rect(x - LARGEUR_BALAYAGE / 2, 0, LARGEUR_BALAYAGE, H);
                ctx.clip();
                ctx.shadowColor = `rgba(${teinte.chaud},.55)`;
                ctx.shadowBlur = 12;
                for (const plan of plans) tracerPlan(plan, cadre, 1, true);
                ctx.restore();
            }
        }

        // Le pointeur relâche son influence quand la souris s'éloigne
        if (pointeur.force > 0) pointeur.force = Math.max(0, pointeur.force - 0.012);

        if (statique) { anime = 0; return; }
        anime = requestAnimationFrame(tracer);
    }

    function relancer() {
        if (!anime && donnees && !document.hidden) anime = requestAnimationFrame(tracer);
    }

    /* -----------------------------------------------------------------
       Écoutes
       ----------------------------------------------------------------- */
    addEventListener('resize', () => { redimensionner(); }, { passive: true });

    addEventListener('scroll', () => { defilement = scrollY; }, { passive: true });

    addEventListener('pointermove', (e) => {
        if (e.pointerType === 'touch') return;
        pointeur.x = e.clientX;
        pointeur.y = e.clientY;
        pointeur.force = 1;
    }, { passive: true });

    addEventListener('pointerleave', () => { pointeur.force = 0; }, { passive: true });

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) { cancelAnimationFrame(anime); anime = 0; }
        else { debut = 0; relancer(); }
    });

    // Le thème change : on relit les couleurs plutôt que de les dupliquer.
    new MutationObserver(relireCouleurs)
        .observe(racine, { attributes: true, attributeFilter: ['data-theme'] });

    mouvementReduit.addEventListener('change', () => { debut = 0; relancer(); });

    /* -----------------------------------------------------------------
       Chargement
       En cas d'échec (fichier absent, ouverture en file:// sur un
       navigateur qui refuse fetch), on ne fait rien : les couches CSS
       du fond suffisent à tenir la page. Rien ne casse.
       ----------------------------------------------------------------- */
    const base = racine.dataset.racine || '';
    fetch(base + 'assets/relief.json')
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then((d) => {
            donnees = d;
            redimensionner();
            repartir();
            relancer();
        })
        .catch(() => { /* le relief est un ornement : son absence n'empêche rien */ });
})();
