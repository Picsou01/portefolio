/* =====================================================================
   LE CADASTRE - noyau commun
   Thème, en-tête, révélation au défilement, page courante.

   Principe : ce fichier n'AJOUTE que du confort. JavaScript bloqué,
   chaque page reste entièrement lisible et navigable, c'est la
   condition pour ne jamais tomber sous le coup de la pénalité
   « portfolio inaccessible ».
   ===================================================================== */

(() => {
    'use strict';

    const racine = document.documentElement;

    /* -----------------------------------------------------------------
       1. LE THÈME
       Le site est pensé de nuit ; le mode papier existe pour qui
       préfère, et pour l'impression.

       Trois états, et pas deux :
         · aucun choix mémorisé  -> on suit la préférence du système, et
           on continue de la suivre si elle change en cours de route ;
         · « papier » ou « nuit » mémorisé -> le choix de la personne
           l'emporte, et le système ne le contredit plus.

       Le thème est appliqué par un script en tête de page, avant le
       premier rendu, pour éviter le clignotement. Ici on ne gère que la
       bascule et le suivi du système.
       ----------------------------------------------------------------- */
    const CLE_THEME = 'cadastre.theme';
    const systemeClair = matchMedia('(prefers-color-scheme: light)');

    function choixMemorise() {
        try {
            const t = localStorage.getItem(CLE_THEME);
            return (t === 'papier' || t === 'nuit') ? t : null;
        } catch (e) {
            return null;   // navigation privée, ou données de site bloquées
        }
    }

    function themeActuel() {
        return racine.dataset.theme === 'papier' ? 'papier' : 'nuit';
    }

    // Tant que rien n'a été choisi, le site suit le système en direct.
    systemeClair.addEventListener('change', (e) => {
        if (choixMemorise()) return;
        const suivant = e.matches ? 'papier' : 'nuit';
        racine.dataset.theme = suivant;
        majBouton(suivant);
    });

    function majBouton(theme) {
        const bouton = document.querySelector('[data-role="theme"]');
        if (!bouton) return;
        const versPapier = theme === 'nuit';
        bouton.setAttribute('aria-label', versPapier ? 'Passer en mode papier' : 'Passer en mode nuit');
        const libelle = bouton.querySelector('[data-role="theme-libelle"]');
        if (libelle) libelle.textContent = versPapier ? 'Papier' : 'Nuit';
    }

    const boutonTheme = document.querySelector('[data-role="theme"]');
    if (boutonTheme) {
        majBouton(themeActuel());
        boutonTheme.addEventListener('click', () => {
            const suivant = themeActuel() === 'nuit' ? 'papier' : 'nuit';
            racine.dataset.theme = suivant;
            try { localStorage.setItem(CLE_THEME, suivant); } catch (e) { /* navigation privée */ }
            majBouton(suivant);
        });
    }

    /* -----------------------------------------------------------------
       2. L'EN-TÊTE
       Transparente en haut de page, elle se pose sur un fond flouté dès
       que l'on défile, même mécanisme que la navigation fixe du site
       de Douvres.
       ----------------------------------------------------------------- */
    const entete = document.querySelector('.entete');
    if (entete) {
        let dernier = null;
        const maj = () => {
            const etat = scrollY > 12 ? 'oui' : 'non';
            if (etat !== dernier) { entete.dataset.defile = etat; dernier = etat; }
        };
        maj();
        addEventListener('scroll', maj, { passive: true });
    }

    /* -----------------------------------------------------------------
       3. RÉVÉLATION AU DÉFILEMENT
       IntersectionObserver plutôt qu'un écouteur de scroll : le
       navigateur fait le calcul lui-même, hors du fil principal.
       ----------------------------------------------------------------- */
    const aReveler = document.querySelectorAll('.revele');
    if (aReveler.length && 'IntersectionObserver' in window) {
        const guetteur = new IntersectionObserver((entrees) => {
            entrees.forEach((entree) => {
                if (!entree.isIntersecting) return;
                entree.target.classList.add('est-visible');
                guetteur.unobserve(entree.target);
            });
        }, { rootMargin: '0px 0px -6% 0px', threshold: 0.05 });
        aReveler.forEach((el) => guetteur.observe(el));
    } else {
        aReveler.forEach((el) => el.classList.add('est-visible'));
    }

    /* -----------------------------------------------------------------
       4. LA PAGE COURANTE
       On compare le dernier segment de l'URL : cela fonctionne aussi
       bien en ligne qu'en local, en file://.
       ----------------------------------------------------------------- */
    const ici = location.pathname.split('/').filter(Boolean).pop() || 'index.html';
    const liens = Array.from(document.querySelectorAll('.nav__lien'));
    liens.forEach((lien) => {
        const cible = lien.getAttribute('href').split('#')[0].split('/').filter(Boolean).pop()
            || 'index.html';
        if (cible === ici) lien.setAttribute('aria-current', 'page');
    });

    /* -----------------------------------------------------------------
       5. LA SECTION COURANTE
       Sur la page d'accueil, la navigation devient un sommaire vivant :
       le lien de la section traversée s'allume. C'est ce qui répond au
       « je ne sais plus où je suis ».

       On observe les en-têtes de section avec une fenêtre resserrée sur
       le haut de l'écran, plutôt que de recalculer des positions à
       chaque cran de molette.
       ----------------------------------------------------------------- */
    const reperes = Array.from(document.querySelectorAll('.section-tete[id], [id="entrees"]'));
    const parAncre = new Map();
    liens.forEach((l) => {
        const h = l.getAttribute('href');
        if (h && h.includes('#')) parAncre.set(h.split('#')[1], l);
    });

    if (reperes.length && parAncre.size && 'IntersectionObserver' in window) {
        let courante = null;
        const marquer = (id) => {
            if (id === courante) return;
            courante = id;
            parAncre.forEach((lien, ancre) => {
                lien.classList.toggle('est-courant', ancre === id);
            });
        };
        const vus = new Set();
        const veille = new IntersectionObserver((entrees) => {
            entrees.forEach((e) => {
                if (e.isIntersecting) vus.add(e.target.id); else vus.delete(e.target.id);
            });
            // La dernière section franchie l'emporte : c'est celle qu'on lit.
            const ordonnes = reperes.filter((r) => vus.has(r.id));
            marquer(ordonnes.length ? ordonnes[ordonnes.length - 1].id : null);
        }, { rootMargin: '-15% 0px -70% 0px', threshold: 0 });
        reperes.forEach((r) => veille.observe(r));
    }
})();
