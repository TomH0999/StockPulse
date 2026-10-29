import { ScreenerRow } from '../services/api';
import { useI18n } from '../context';

export interface Filters { pea: boolean; country: string }

export const applyFilters = (rows: ScreenerRow[], f: Filters) =>
  rows.filter((r) => (!f.pea || r.pea) && (!f.country || r.country === f.country));

export function MarketFilters({ rows, value, onChange }: { rows: ScreenerRow[]; value: Filters; onChange: (f: Filters) => void }) {
  const { t } = useI18n();
  const countries = [...new Set(rows.map((r) => r.country))].sort();
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input type="checkbox" checked={value.pea} onChange={(e) => onChange({ ...value, pea: e.target.checked })} className="accent-sky-600" />
        {t.peaOnly}
      </label>
      <select className="input !w-auto !py-1.5" value={value.country} onChange={(e) => onChange({ ...value, country: e.target.value })} aria-label={t.country}>
        <option value="">{t.allCountries}</option>
        {countries.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
    </div>
  );
}
