// Attendre que le DOM soit prêt avant de manipuler quoi que ce soit
document.addEventListener('DOMContentLoaded', () => {

    // Exemple : log dans la console pour vérifier que ça marche
    console.log('Script chargé');

    // Exemple : sélectionner tous les liens de nav et écouter les clics
    const liensNav = document.querySelectorAll('nav a');

    liensNav.forEach(lien => {
        lien.addEventListener('click', (event) => {
            // Pour l'instant on laisse le comportement par défaut (ancre)
            // Plus tard tu pourras ajouter du smooth scroll ici
        });
    });

});