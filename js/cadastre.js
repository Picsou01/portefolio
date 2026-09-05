/* =====================================================================
   LE CADASTRE - mécaniques du plan et de l'instrument
   La visée, le filtre, le clavier, les compteurs, l'altimètre.

   POINT D'ARCHITECTURE
   Ce fichier ne CONSTRUIT rien. Le tableau existe en HTML statique
   dans la page ; on se contente de le lire et de l'enrichir. Une seule
   source de vérité, donc jamais de désaccord entre ce que voit un
   humain, un lecteur d'écran ou un robot d'indexation.
   ===================================================================== */

(() => {
    'use strict';

    const mouvementReduit = matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* =================================================================
       1. LE PLAN
       ================================================================= */
    const plan = document.querySelector('[data-role="plan"]');

    if (plan) {
        const defile = document.querySelector('[data-role="plan-defile"]');
        const viseeH = document.querySelector('[data-role="visee-h"]');
        const viseeV = document.querySelector('[data-role="visee-v"]');

        const enTetes = new Map();
        plan.querySelectorAll('.plan__col').forEach((th) => enTetes.set(th.dataset.comp, th));

        let ligneVisee = null;
        let colonneVisee = null;

        /* --- La visée -------------------------------------------------
           Survoler une case allume sa ligne ET sa colonne, et fait
           courir deux fils lumineux jusqu'aux bords du plan. C'est le
           geste du géomètre qui aligne sa lunette : on lit d'un coup
           « quelle réalisation × quelle compétence ».
           ------------------------------------------------------------- */
        function effacerVisee() {
            if (ligneVisee) ligneVisee.classList.remove('est-visee');
            if (colonneVisee) {
                plan.querySelectorAll(`[data-col="${colonneVisee}"]`)
                    .forEach((c) => c.classList.remove('est-visee'));
                const th = enTetes.get(colonneVisee);
                if (th) th.classList.remove('est-visee');
            }
            ligneVisee = colonneVisee = null;
            if (defile) defile.dataset.visee = 'non';
        }

        function placerFils(cellule) {
            if (!defile || !viseeH || !viseeV) return;
            const c = cellule.getBoundingClientRect();
            const d = defile.getBoundingClientRect();
            // Coordonnées dans le contenu défilant, pas dans la fenêtre.
            const y = c.top - d.top + defile.scrollTop + c.height / 2;
            const x = c.left - d.left + defile.scrollLeft + c.width / 2;

            viseeH.style.width = defile.scrollWidth + 'px';
            viseeV.style.height = defile.scrollHeight + 'px';
            viseeH.style.transform = `translateY(${Math.round(y)}px)`;
            viseeV.style.transform = `translateX(${Math.round(x)}px)`;
            defile.dataset.visee = 'oui';
        }

        function viser(cellule) {
            const ligne = cellule.closest('.plan__ligne');
            const colonne = cellule.dataset.col;
            if (ligne === ligneVisee && colonne === colonneVisee) {
                placerFils(cellule);
                return;
            }
            effacerVisee();

            if (ligne) { ligne.classList.add('est-visee'); ligneVisee = ligne; }
            if (colonne) {
                plan.querySelectorAll(`[data-col="${colonne}"]`)
                    .forEach((c) => c.classList.add('est-visee'));
                const th = enTetes.get(colonne);
                if (th) th.classList.add('est-visee');
                colonneVisee = colonne;
            }
            placerFils(cellule);
        }

        plan.addEventListener('pointerover', (e) => {
            const cellule = e.target.closest('.plan__case, .plan__ligne-titre');
            if (cellule) viser(cellule); else effacerVisee();
        });
        plan.addEventListener('pointerleave', effacerVisee);

        // Le clavier doit produire exactement le même effet que la souris.
        plan.addEventListener('focusin', (e) => {
            const cellule = e.target.closest('.plan__case, .plan__ligne-titre');
            if (cellule) viser(cellule);
        });
        plan.addEventListener('focusout', (e) => {
            if (!plan.contains(e.relatedTarget)) effacerVisee();
        });

        /* --- Déplacement au clavier entre les bornes -------------------
           Les bornes sont dispersées dans la matrice : les parcourir à
           la flèche est bien plus rapide que de tabuler à travers les
           quarante-cinq cases vides.
           ------------------------------------------------------------- */
        const bornes = Array.from(plan.querySelectorAll('.borne'));
        plan.addEventListener('keydown', (e) => {
            const courante = e.target.closest('.borne');
            if (!courante) return;
            const i = bornes.indexOf(courante);
            let cible = null;
            if (e.key === 'ArrowDown' || e.key === 'ArrowRight') cible = bornes[i + 1];
            else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') cible = bornes[i - 1];
            else if (e.key === 'Home') cible = bornes[0];
            else if (e.key === 'End') cible = bornes[bornes.length - 1];
            else return;
            if (cible) { e.preventDefault(); cible.focus(); }
        });

        /* --- Le basculement de vue -------------------------------------
           Le tableau officiel et le plan de bornage montrent les mêmes
           données. Les deux sont écrits dans la page ; on n'en cache un
           que parce que le script est là pour le rendre à la demande.
           ------------------------------------------------------------- */
        const conteneur = document.querySelector('[data-role="vues"]');
        const boutonsVue = document.querySelectorAll('[data-vue]');
        const vues = document.querySelectorAll('[data-vue-contenu]');

        function afficherVue(nom) {
            vues.forEach((v) => { v.hidden = v.dataset.vueContenu !== nom; });
            boutonsVue.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.vue === nom)));
            if (nom === 'tableau') effacerVisee();
        }
        if (boutonsVue.length) {
            afficherVue('tableau');
            boutonsVue.forEach((b) => b.addEventListener('click', () => afficherVue(b.dataset.vue)));
        }

        /* --- Le filtre par compétence ----------------------------------
           On pose un attribut sur le conteneur de la section, pas sur le
           tableau : c'est ce qui permet aux DEUX vues d'y réagir. Le CSS
           fait le reste, aucune classe posée ligne par ligne, et l'état
           du filtre reste lisible dans l'inspecteur.
           ------------------------------------------------------------- */
        const boutonsFiltre = document.querySelectorAll('[data-filtre-comp]');
        const etatPlan = document.querySelector('[data-role="plan-etat"]');
        const etatInitial = etatPlan ? etatPlan.innerHTML : '';
        const cible = conteneur || plan;

        function appliquerFiltre(code) {
            if (!code || cible.dataset.filtre === code) {
                delete cible.dataset.filtre;
                code = null;
            } else {
                cible.dataset.filtre = code;
            }
            boutonsFiltre.forEach((b) => {
                b.setAttribute('aria-pressed', String(b.dataset.filtreComp === code));
            });
            if (!etatPlan) return;
            if (!code) {
                etatPlan.innerHTML = etatInitial;
            } else {
                const n = plan.querySelectorAll(`.plan__ligne[data-comp~="${code}"]`).length;
                etatPlan.innerHTML = `Compétence <strong>${code}</strong> &nbsp;·&nbsp; `
                    + `<strong>${n}</strong> réalisation${n > 1 ? 's' : ''} sur 9`;
            }
        }

        boutonsFiltre.forEach((b) => {
            b.addEventListener('click', () => appliquerFiltre(b.dataset.filtreComp));
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && cible.dataset.filtre) appliquerFiltre(null);
        });

        if (defile) {
            defile.addEventListener('scroll', effacerVisee, { passive: true });
            addEventListener('resize', effacerVisee, { passive: true });
        }
    }

    /* =================================================================
       2. LES COMPTEURS
       Les chiffres du relevé montent jusqu'à leur valeur. On préserve
       les séparateurs de milliers : « 13 500 » ne doit jamais devenir
       « 13500 » en cours de route.
       ================================================================= */
    function animerCompteur(el) {
        const cible = el.dataset.compteur || el.textContent;
        const chiffres = cible.replace(/[^\d]/g, '');
        if (!chiffres) return;
        const fin = parseInt(chiffres, 10);
        if (!fin || mouvementReduit) return;

        const separe = /\s/.test(cible);
        const duree = 1100;
        const t0 = performance.now();

        function pas(t) {
            const k = Math.min(1, (t - t0) / duree);
            // Sortie cubique : démarre vite, se pose doucement.
            const v = Math.round(fin * (1 - Math.pow(1 - k, 3)));
            el.textContent = separe ? v.toLocaleString('fr-FR').replace(/ | /g, ' ') : String(v);
            if (k < 1) requestAnimationFrame(pas);
            else el.textContent = cible;
        }
        el.textContent = '0';
        requestAnimationFrame(pas);
    }

    const compteurs = document.querySelectorAll('[data-compteur]');
    if (compteurs.length && 'IntersectionObserver' in window) {
        const oc = new IntersectionObserver((entrees) => {
            entrees.forEach((e) => {
                if (!e.isIntersecting) return;
                animerCompteur(e.target);
                oc.unobserve(e.target);
            });
        }, { threshold: 0.5 });
        compteurs.forEach((c) => oc.observe(c));
    }

    /* =================================================================
       3. L'ALTIMÈTRE
       Le rail de gauche indique la profondeur atteinte dans la page.
       Une seule écriture par image : jamais de calcul de mise en page
       dans l'écouteur de défilement lui-même.
       ================================================================= */
    const curseur = document.querySelector('[data-role="rail-curseur"]');
    const cote = document.querySelector('[data-role="rail-cote"]');

    if (curseur) {
        let enAttente = false;
        const majRail = () => {
            if (enAttente) return;
            enAttente = true;
            requestAnimationFrame(() => {
                const total = document.documentElement.scrollHeight - innerHeight;
                const part = total > 0 ? Math.min(1, Math.max(0, scrollY / total)) : 0;
                const haut = innerHeight * 0.12;
                const bas = innerHeight * 0.88;
                const y = haut + (bas - haut) * part;
                curseur.style.top = y + 'px';
                if (cote) {
                    cote.style.top = y + 'px';
                    cote.textContent = String(Math.round(part * 100)).padStart(3, '0');
                }
                enAttente = false;
            });
        };
        majRail();
        addEventListener('scroll', majRail, { passive: true });
        addEventListener('resize', majRail, { passive: true });
    }

    /* =================================================================
       4. L'ORDRE D'APPARITION
       Les grilles révélées en cascade ont besoin de connaître le rang
       de chaque enfant. On le pose en variable CSS plutôt que de gérer
       des délais en JavaScript.
       ================================================================= */
    document.querySelectorAll('.revele--decale').forEach((grille) => {
        Array.from(grille.children).forEach((enfant, i) => {
            if (!enfant.style.getPropertyValue('--i')) {
                enfant.style.setProperty('--i', i);
            }
        });
    });
})();
