import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { Account, AccountType, api, errorMessage, getAccount, onPortfolioChanged, setAccount } from '../services/api';
import { useI18n } from '../context';

const TYPES: AccountType[] = ['PEA', 'PEA_PME', 'PEA_JEUNE', 'CTO', 'AV'];

/** Choix du compte affiché (PEA, PEA-PME, compte-titres, assurance-vie) et ouverture d'un nouveau compte. */
export function AccountBar() {
  const { t } = useI18n();
  const [list, setList] = useState<Account[]>([]);
  const [current, setCurrent] = useState(getAccount());
  const [adding, setAdding] = useState(false);
  const [type, setType] = useState<AccountType>('CTO');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const load = () => api.accounts().then((r) => {
    setList(r.accounts);
    if (!r.accounts.some((a) => a.id === getAccount())) setAccount('pea');
    setCurrent(getAccount());
  }).catch(() => {});
  useEffect(() => { load(); return onPortfolioChanged(() => setCurrent(getAccount())); }, []);

  const create = () => api.createAccount(type, name).then((a) => { setAdding(false); setName(''); setError(null); load().then(() => setAccount(a.id)); })
    .catch((e) => setError(errorMessage(e)));
  return (
    <div className="flex flex-wrap items-center gap-2">
      {list.map((a) => (
        <button key={a.id} onClick={() => setAccount(a.id)}
          className={`px-3 py-1.5 rounded-lg text-sm border cursor-pointer ${current === a.id ? 'bg-sky-600 text-white border-sky-600' : 'border-slate-300 dark:border-slate-700 hover:border-sky-500'}`}>
          {a.name} <span className="text-[10px] opacity-75">{a.label}</span>
        </button>
      ))}
      {adding ? (
        <span className="flex flex-wrap items-center gap-2">
          <select className="input !w-auto !py-1.5" value={type} onChange={(e) => setType(e.target.value as AccountType)}>
            {TYPES.map((x) => <option key={x} value={x}>{t[`acc_${x}`]}</option>)}
          </select>
          <input className="input !w-44 !py-1.5" value={name} onChange={(e) => setName(e.target.value)} placeholder={t.accName} />
          <button className="btn-primary" onClick={create}>{t.accCreate}</button>
          <button className="btn" onClick={() => setAdding(false)}>{t.cancel}</button>
          {error && <span className="text-xs text-rose-500">{error}</span>}
        </span>
      ) : <button className="btn !py-1.5" onClick={() => setAdding(true)}><Plus className="w-3.5 h-3.5" />{t.accAdd}</button>}
    </div>
  );
}
