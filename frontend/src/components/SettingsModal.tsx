import { useEffect, useState } from 'react';
import { Trash2, X } from 'lucide-react';
import { AiSettings, api, errorMessage, Lang } from '../services/api';
import { useI18n } from '../context';

const KEY_LINKS: Record<string, string> = {
  groq: 'https://console.groq.com/keys',
  gemini: 'https://aistudio.google.com/apikey',
  cerebras: 'https://cloud.cerebras.ai',
  openrouter: 'https://openrouter.ai/settings/keys',
  mistral: 'https://console.mistral.ai/api-keys',
};

interface Props {
  onClose: () => void;
  lang: Lang;
  setLang: (l: Lang) => void;
  dark: boolean;
  setDark: (d: boolean) => void;
  onSaved: () => void;
}

export function SettingsModal({ onClose, lang, setLang, dark, setDark, onSaved }: Props) {
  const { t } = useI18n();
  const [settings, setSettings] = useState<AiSettings | null>(null);
  const [provider, setProvider] = useState('groq');
  const [key, setKey] = useState('');
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const load = () => api.aiSettings().then(setSettings).catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const run = (p: Promise<AiSettings>, done?: () => void) => {
    setBusy(true);
    setStatus(null);
    p.then((s) => { setSettings(s); setStatus({ ok: true, msg: t.saved }); done?.(); onSaved(); })
      .catch((e) => setStatus({ ok: false, msg: errorMessage(e) }))
      .finally(() => setBusy(false));
  };

  const auto = settings?.auto;
  const [data, setData] = useState<Awaited<ReturnType<typeof api.dataSettings>> | null>(null);
  const [dProvider, setDProvider] = useState('fmp');
  const [dKey, setDKey] = useState('');
  const [fees, setFees] = useState({ pct: '0.5', min: '1.99' });
  useEffect(() => { api.dataSettings().then(setData).catch(() => {}); }, []);
  const runData = (p: Promise<unknown>, done?: () => void) => {
    setBusy(true); setStatus(null);
    p.then(() => api.dataSettings()).then((d) => { setData(d); setStatus({ ok: true, msg: t.saved }); done?.(); })
      .catch((e) => setStatus({ ok: false, msg: errorMessage(e) })).finally(() => setBusy(false));
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="card !bg-white dark:!bg-slate-900 w-full max-w-xl p-6 space-y-5 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">{t.settings}</h2>
          <button onClick={onClose} className="muted hover:text-rose-500 cursor-pointer"><X className="w-5 h-5" /></button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">{t.language}</label>
            <select className="input" value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
              <option value="fr">Français</option><option value="en">English</option><option value="es">Español</option><option value="zh">中文</option>
            </select>
          </div>
          <div>
            <label className="label">{t.theme}</label>
            <select className="input" value={dark ? 'dark' : 'light'} onChange={(e) => setDark(e.target.value === 'dark')}>
              <option value="dark">🌙</option><option value="light">☀️</option>
            </select>
          </div>
        </div>

        <section className="space-y-2">
          <h3 className="font-bold">{t.keysTitle}</h3>
          <p className="text-xs muted">{t.keysHelp}</p>
          {!settings?.keys.length ? <p className="text-sm muted">{t.noKeys}</p> : (
            <ul className="space-y-1.5">
              {settings.keys.map((k) => (
                <li key={k.id} className="flex items-center gap-2 text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-800">
                  <b className="w-20">{k.provider}</b>
                  <span className="font-mono">{k.hint}</span>
                  <span className="muted truncate flex-1">{k.model ?? ''} · ✓ {k.ok}{k.errors ? ` · ✗ ${k.errors}` : ''}
                    {k.cooldown > 0 && ` · ${t.cooldown} ${k.cooldown}s`}</span>
                  {k.last_error && <span className="text-amber-500 truncate max-w-[120px]" title={k.last_error}>⚠</span>}
                  <button className="muted hover:text-rose-500 cursor-pointer" title={t.remove} onClick={() => run(api.removeAiKey(k.id))}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex gap-2 items-end">
            <div className="w-36">
              <label className="label">{t.provider}</label>
              <select className="input" value={provider} onChange={(e) => setProvider(e.target.value)}>
                {(settings?.providers ?? Object.keys(KEY_LINKS)).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="label">{t.apiKey}</label>
              <input className="input font-mono" type="password" value={key} onChange={(e) => setKey(e.target.value)} />
            </div>
            <button className="btn-primary !py-2" disabled={busy || !key.trim()} onClick={() => run(api.addAiKey(provider, key), () => setKey(''))}>
              {busy ? '…' : t.addKey}
            </button>
          </div>
          <a href={KEY_LINKS[provider]} target="_blank" rel="noreferrer" className="text-xs text-sky-600 dark:text-sky-400 hover:underline">{t.getKey} ({provider}) ↗</a>
          {status && <p className={`text-sm ${status.ok ? 'up' : 'down'}`}>{status.msg}</p>}
        </section>

        <section className="space-y-2">
          <h3 className="font-bold">{t.dataKeysTitle}</h3>
          <p className="text-xs muted">{t.dataKeysHelp}</p>
          {data?.keys.map((k) => (
            <div key={k.id} className="flex items-center gap-2 text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-800">
              <b className="w-24">{k.provider}</b><span className="font-mono flex-1">{k.hint}</span>
              <button className="muted hover:text-rose-500 cursor-pointer" title={t.remove} onClick={() => runData(api.removeDataKey(k.id))}><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          ))}
          <div className="flex gap-2 items-end">
            <div className="w-36"><label className="label">{t.provider}</label>
              <select className="input" value={dProvider} onChange={(e) => setDProvider(e.target.value)}>
                {Object.keys(data?.providers ?? { fmp: '', finnhub: '', alphavantage: '' }).map((p) => <option key={p} value={p}>{p}</option>)}
              </select></div>
            <div className="flex-1"><label className="label">{t.apiKey}</label>
              <input className="input font-mono" type="password" value={dKey} onChange={(e) => setDKey(e.target.value)} /></div>
            <button className="btn-primary !py-2" disabled={busy || !dKey.trim()} onClick={() => runData(api.addDataKey(dProvider, dKey), () => setDKey(''))}>{t.addKey}</button>
          </div>
          {data?.providers[dProvider] && <a href={data.providers[dProvider]} target="_blank" rel="noreferrer" className="text-xs text-sky-600 dark:text-sky-400 hover:underline">{t.getKey} ({dProvider}) ↗</a>}
        </section>

        <section className="space-y-2">
          <h3 className="font-bold">{t.feesTitle}</h3>
          <div className="flex gap-2 items-end">
            <div className="w-28"><label className="label">{t.feePct}</label><input className="input" inputMode="decimal" value={fees.pct} onChange={(e) => setFees({ ...fees, pct: e.target.value })} /></div>
            <div className="w-28"><label className="label">{t.feeMin}</label><input className="input" inputMode="decimal" value={fees.min} onChange={(e) => setFees({ ...fees, min: e.target.value })} /></div>
            <button className="btn !py-2" onClick={() => runData(api.setFees(Number(fees.pct.replace(',', '.')), Number(fees.min.replace(',', '.'))))}>{t.save}</button>
          </div>
        </section>

        {auto && (
          <section className="space-y-2">
            <h3 className="font-bold">{t.autoTitle}</h3>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" className="accent-sky-600" checked={auto.enabled} onChange={(e) => run(api.setAuto(e.target.checked, auto.ai_hours))} />
              {t.autoEnabled}
            </label>
            <div className="flex items-center gap-2 text-sm">
              <span>{t.aiHours}</span>
              <input type="number" min={1} max={168} className="input !w-20 !py-1" defaultValue={auto.ai_hours}
                onBlur={(e) => Number(e.target.value) !== auto.ai_hours && run(api.setAuto(auto.enabled, Number(e.target.value) || 12))} />
            </div>
            <div className="text-xs muted">
              {t.progress} : {auto.analysed}/{auto.total} {t.analysedLocal} · {auto.ai_analysed} {t.analysedAi} · {auto.keys_available}/{settings?.keys.length ?? 0} {t.keysReady}
            </div>
            <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden flex">
              <div className="bg-sky-600" style={{ width: `${(auto.ai_analysed / auto.total) * 100}%` }} />
              <div className="bg-sky-600/40" style={{ width: `${((auto.analysed - auto.ai_analysed) / auto.total) * 100}%` }} />
            </div>
            {auto.last_error && <p className="text-[11px] text-amber-500 truncate" title={auto.last_error}>⚠ {auto.last_error}</p>}
          </section>
        )}
      </div>
    </div>
  );
}
