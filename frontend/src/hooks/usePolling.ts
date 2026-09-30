import { useEffect, useRef } from 'react';

/**
 * Hook personnalisé pour gérer le polling (rafraîchissement automatique)
 * @param callback Fonction à exécuter à chaque intervalle
 * @param delay Intervalle en millisecondes (ex: 5000 pour 5 secondes)
 */
export function usePolling(callback: () => void, delay: number | null) {
    const savedCallback = useRef(callback);

    // Mémorise le dernier callback pour éviter des re-rendus inutiles
    useEffect(() => {
        savedCallback.current = callback;
    }, [callback]);

    useEffect(() => {
        if (delay === null) return;

        const tick = () => {
            savedCallback.current();
        };

        const id = setInterval(tick, delay);
        return () => clearInterval(id);
    }, [delay]);
}