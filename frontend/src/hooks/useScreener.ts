import { useEffect, useMemo, useState } from 'react';
import { api, InstrumentKind, ScreenerRow } from '../services/api';

/** Données du catalogue (par défaut : actions seulement), rafraîchies chaque minute. */
export function useScreener(kinds: InstrumentKind[] = ['stock']) {
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

  const key = kinds.join();
  const filtered = useMemo(() => rows.filter((r) => kinds.includes(r.kind ?? 'stock')), [rows, key]); // eslint-disable-line react-hooks/exhaustive-deps
  return { rows: filtered, updated, loading };
}
