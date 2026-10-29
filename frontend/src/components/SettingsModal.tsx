import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { AiSettings, api, errorMessage, Lang } from '../services/api';
import { useI18n } from '../context';

const KEY_LINKS: Record<string, string> = {
  gemini: 'https://aistudio.google.com/apikey',
  groq: 'https://console.groq.com/keys',
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
  const [current, setCurrent] = useState<AiSettings | null>(null);
  const [provider, setProvider] = useState('local');
  const [key, setKey] = useState('');
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.aiSettings().then((s) => { setCurrent(s); setProvider(s.provider); }).catch(() => {});
  }, []);

  const save = () => {
    setSaving(true);
    setStatus(null);
    api.saveAiSettings(provider, key)
      .then((s) => { setCurrent(s); setKey(''); setStatus({ ok: true, msg: t.saved }); onSaved(); })
      .catch((e) => setStatus({ ok: false, msg: errorMessage(e) }))
      .finally(() => setSaving(false));
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="card !bg-white dark:!bg-slate-900 w-full max-w-md p-6 space-y-5" onClick={(e) => e.stopPropagation()}>
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

        <div className="space-y-3">
          <div>
            <label className="label">{t.aiProvider}</label>
            <select className="input" value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="local">{t.providerLocal}</option>
              <option value="gemini">Google Gemini 2.5 Flash</option>
              <option value="groq">Groq · Llama 3.3 70B</option>
            </select>
          </div>
          {provider !== 'local' && (
            <div>
              <label className="label">{t.apiKey}</label>
              <input className="input font-mono" type="password" value={key} onChange={(e) => setKey(e.target.value)}
                placeholder={current?.has_key && current.provider === provider ? `${t.keyStored} ${current.key_hint}` : ''} />
              <a href={KEY_LINKS[provider]} target="_blank" rel="noreferrer" className="text-xs text-sky-600 dark:text-sky-400 hover:underline">{t.getKey} ↗</a>
            </div>
          )}
          {status && <p className={`text-sm ${status.ok ? 'up' : 'down'}`}>{status.msg}</p>}
        </div>

        <div className="flex justify-end gap-2">
          <button className="btn" onClick={onClose}>{t.cancel}</button>
          <button className="btn-primary" onClick={save} disabled={saving || (provider !== 'local' && !key && !(current?.has_key && current.provider === provider))}>
            {saving ? '…' : t.save}
          </button>
        </div>
      </div>
    </div>
  );
}
