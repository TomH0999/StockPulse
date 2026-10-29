import { useEffect, useState } from 'react';
import { api, ScreenerRow } from '../services/api';

/** Données de toutes les entreprises du catalogue, rafraîchies chaque minute. */
export function useScreener() {
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [updated, setUpdated] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = () => api.screener()
      .then((d) => { if (alive) { setRows(d.rows); setUpdated(d.updated); } })
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    load();
    const id = setInterval(load, 60000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return { rows, updated, loading };
}
