/* =====================================================================
   LE CADASTRE - le carnet de relevé
   Un géomètre note les parcelles qu'il a déjà arpentées. Le carnet
   fait la même chose pour le visiteur : il retient quelles fiches ont
   été ouvertes, et le montre : dans l'en-tête (« RELEVÉ 4/9 »), dans
   le panneau dépliant, et par une marque discrète sur le plan.

   Pourquoi c'est utile, et pas décoratif : un membre de la commission
   qui revient sur le portfolio voit immédiatement ce qu'il lui reste
   à consulter. Et moi, en relisant, je vois ce que je n'ai pas encore
   rempli.

   Tout est local au navigateur (localStorage) : rien n'est envoyé
   nulle part, aucune donnée personnelle n'est collectée. C'est ce que
   dit la page « Mentions légales », et c'est vrai.
   ===================================================================== */

(() => {
    'use strict';

    const PARCELLES = window.CADASTRE_PARCELLES || [];
    if (!PARCELLES.length) return;

    const CLE = 'cadastre.arpentage';
    const racine = document.documentElement.dataset.racine || '';

    /* -----------------------------------------------------------------
       Lecture / écriture tolérantes aux pannes.
       En navigation privée, ou avec les données de site bloquées,
       localStorage lève une exception : le carnet doit alors se
       contenter de ne rien retenir, sans casser la page.
       ----------------------------------------------------------------- */
    function lire() {
        try {
            const brut = localStorage.getItem(CLE);
            const liste = brut ? JSON.parse(brut) : [];
            return Array.isArray(liste) ? liste : [];
        } catch (e) {
            return [];
        }
    }

    function ecrire(liste) {
        try { localStorage.setItem(CLE, JSON.stringify(liste)); } catch (e) { /* sans effet */ }
    }

    /* =================================================================
       ┌───────────────────────────────────────────────────────────────────┐
       │ À TOI DE TRANCHER, Maël                                           │
       │                                                                   │
       │ Question : qu'est-ce qui compte comme « parcelle arpentée » ?     │
       │ Ce n'est pas une question technique, c'est une question de sens.  │
       │ Trois réponses défendables :                                      │
       │                                                                   │
       │ 1. OUVRIR SUFFIT (le défaut retenu ci-dessous)                    │
       │    Simple, immédiat, jamais frustrant. Mais un clic parti de      │
       │    travers compte autant qu'une vraie lecture.                    │
       │                                                                   │
       │ 2. IL FAUT ATTEINDRE LE BAS DE LA FICHE                           │
       │    Le compteur devient honnête : il mesure une lecture, pas un    │
       │    passage. Mais sur mobile, une fiche longue décourage, et le    │
       │    compteur stagne. Poser un IntersectionObserver sur le dernier  │
       │    bloc de la fiche.                                              │
       │                                                                   │
       │ 3. IL FAUT Y RESTER UN TEMPS MINIMUM (8 secondes par exemple)     │
       │    Bon compromis, mais invisible : le visiteur ne comprend pas    │
       │    pourquoi la marque apparaît toute seule.                       │
       │                                                                   │
       │ Remplace le corps de estArpentee() ci-dessous. La fonction reçoit │
       │ le slug de la fiche courante et doit appeler marquer(slug) au     │
       │ moment où tu considères la parcelle comme lue.                    │
       └───────────────────────────────────────────────────────────────────┘
       ================================================================= */
    function estArpentee(slug, marquer) {
        // Défaut retenu : option 1, ouvrir la fiche suffit.
        marquer(slug);
    }
    /* ================================================================= */

    function marquer(slug) {
        const liste = lire();
        if (liste.includes(slug)) return;
        liste.push(slug);
        ecrire(liste);
        rafraichir();
    }

    /* -----------------------------------------------------------------
       Affichage : le compteur, le panneau, et les marques sur le plan.
       ----------------------------------------------------------------- */
    const bouton = document.querySelector('[data-role="carnet"]');
    const compteur = document.querySelector('[data-role="carnet-compte"]');
    const panneau = document.querySelector('[data-role="carnet-panneau"]');
    const liste = document.querySelector('[data-role="carnet-liste"]');
    const vider = document.querySelector('[data-role="carnet-vider"]');

    function rafraichir() {
        const vues = lire();

        if (compteur) compteur.textContent = `${vues.length} / ${PARCELLES.length}`;

        if (liste) {
            liste.innerHTML = PARCELLES.map((p) => {
                const vue = vues.includes(p.slug);
                return `<li data-arpentee="${vue ? 'oui' : 'non'}">
                    <a href="${racine}${p.href}">
                        <span class="carnet__marque" aria-hidden="true">${vue ? '⊗' : '··'}</span>
                        <span>${p.num} · ${p.titre}</span>
                        <span class="sr">${vue ? 'déjà consultée' : 'non consultée'}</span>
                    </a>
                </li>`;
            }).join('');
        }

        // Marque discrète sur les lignes du plan, en page d'accueil.
        document.querySelectorAll('.plan__ligne[data-slug]').forEach((tr) => {
            tr.dataset.arpentee = vues.includes(tr.dataset.slug) ? 'oui' : 'non';
        });
    }

    if (bouton && panneau) {
        bouton.addEventListener('click', () => {
            const ouvert = !panneau.hidden;
            panneau.hidden = ouvert;
            bouton.setAttribute('aria-expanded', String(!ouvert));
        });

        // Refermer au clic extérieur ou à Échap : comportement attendu d'un panneau.
        document.addEventListener('click', (e) => {
            if (panneau.hidden) return;
            if (bouton.contains(e.target) || panneau.contains(e.target)) return;
            panneau.hidden = true;
            bouton.setAttribute('aria-expanded', 'false');
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !panneau.hidden) {
                panneau.hidden = true;
                bouton.setAttribute('aria-expanded', 'false');
                bouton.focus();
            }
        });
    }

    if (vider) {
        vider.addEventListener('click', () => {
            ecrire([]);
            rafraichir();
        });
    }

    rafraichir();

    // Si la page courante est une fiche de parcelle, on applique la règle.
    const slugCourant = document.body.dataset.parcelle;
    if (slugCourant) estArpentee(slugCourant, marquer);
})();
