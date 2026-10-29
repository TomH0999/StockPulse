// Service worker minimal : rend l'application installable (PWA). Données toujours récupérées en ligne.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
