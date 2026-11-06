# StockPulse

Centrale bourse & actualités pour ordinateur : cours en direct, graphiques, archive d'articles et conseil d'investissement.

## Démarrer

**Guide complet de mise en place : [docs/GUIDE.md](docs/GUIDE.md)** (installation, clés gratuites, PEA, favoris de départ).

## Installer (Windows, macOS, Linux)

Télécharger depuis [Releases](https://github.com/TomH0999/StockPulse/releases) : `StockPulse-Setup-x.y.z.exe` (Windows), `.dmg` (macOS Apple Silicon), `.AppImage` / `.deb` (Linux).
Vérifier l'intégrité (facultatif) : `certutil -hashfile StockPulse-Setup-x.y.z.exe SHA256` doit correspondre à `SHA256SUMS.txt` de la release.
Windows SmartScreen peut afficher un avertissement (application non signée) : « Informations complémentaires » → « Exécuter quand même ».

Feuille de route : [ROADMAP.md](ROADMAP.md)

## Fonctionnalités

Pensé pour l'investisseur de long terme (10 à 30 ans) : comprendre des entreprises et tenir une discipline, pas suivre les cours.

- **Conseil long terme** : fondamentaux et valorisation (60 pts : rendement du free cash-flow, PER face à l'historique de la
  société, VE/EBIT, dette nette/EBITDA, croissance), qualité et régularité (25 pts : ROIC, régularité des marges, dilution,
  historique du dividende), tendance de fond (15 pts : moyenne 200 jours). Seuils propres aux banques, assurances et foncières.
  Comptes publiés récupérés **sans clé**, y compris pour les valeurs européennes (4 derniers exercices).
- **Fiabilité prouvée ou non** : chaque mois, toutes les valeurs sont classées par le moteur affiché (comptes connus à la date) ;
  corrélation de rang avec le rendement des 12 mois suivants, quintiles, face au STOXX Europe 600 et au MSCI World, avec un
  intervalle de confiance honnête. Gris « non mesurable » tant que l'intervalle contient 0 (c'est le cas aujourd'hui).
- **Actualités en faits** : événements classés (résultats, prévisions, rachats, dividende, litiges…), étude d'événements sur
  l'archive et test « déjà dans les prix ? » ; surprises de résultats, révisions d'analystes et achats des dirigeants (clé Finnhub).
- **L'IA explique, elle ne décide pas** : lecture séparée (avec contrôle des chiffres cités), analyses groupées, scénarios corrigés.
- **Comptes** : PEA, PEA-PME (plafond commun 225 000 €), PEA jeune, compte-titres, assurance-vie ; fiscalité 2026 simulée
  (prélèvements sociaux 18,6 %, PFU 31,4 %, moins-values reportables 10 ans), échéance des 5 ans, enveloppe conseillée par titre.
- **Performance** : TRI (dates des versements comprises), rendement pondéré dans le temps et comparaison « si tout sur CW8 ».
- **Journal de thèse** par ligne (thèse, valeur estimée, conditions de vente) avec revue annuelle.
- **Diversification réelle** : exposition par pays et secteur à travers les ETF ; un ETF Monde n'est plus « une ligne trop lourde ».
- **Ordres à cours limité** avec pas de cotation sûrs, frais, TTF et change ; stop facultatif (désactivé par défaut).
- **Classements long terme** (qualité, free cash-flow, valorisation vs historique, ROIC, dividende, bilan), ETF & marchés,
  onglet News, archive d'actualités, alertes de prix.
- Français et anglais, thème clair / sombre ; données personnelles propres à chaque installation.

## Clés IA gratuites

Aucune modification de code : les clés se collent dans l'application, **⚙ Paramètres → Clés IA → Fournisseur + Clé → Ajouter la clé**.
Chaque clé est testée avant d'être enregistrée (base locale du PC), puis les analyses sont réparties sur toutes les clés disponibles.
Une analyse consomme environ 5 000 jetons. Les quotas gratuits changent souvent : vérifiez-les sur la console de chaque fournisseur.

| Fournisseur | Où créer la clé | Étapes |
|---|---|---|
| Groq | https://console.groq.com/keys | Se connecter (Google/GitHub) → *Create API Key* → copier `gsk_…` |
| Google Gemini | https://aistudio.google.com/apikey | Compte Google → *Create API key* → choisir/créer un projet → copier `AIza…` |
| Cerebras | https://cloud.cerebras.ai | Créer un compte → menu *API Keys* → *Generate API Key* → copier `csk-…` |
| OpenRouter | https://openrouter.ai/settings/keys | Créer un compte → *Create Key* (sans crédit : modèles `:free` uniquement) → copier `sk-or-…` |
| Mistral | https://console.mistral.ai/api-keys | Créer un compte → choisir l'offre gratuite *Experiment* (vérification par téléphone) → *Create new key* |

Les limites s'appliquent par compte : plusieurs clés d'un même compte partagent le même quota. Pour aller plus vite,
combinez des fournisseurs différents (créer plusieurs comptes chez un même fournisseur est en général interdit par ses conditions).

## Clés de données (fondamentaux, calendrier)

**⚙ Paramètres → Clés de données de marché** : Financial Modeling Prep (https://site.financialmodelingprep.com/developer/docs/dashboard),
Finnhub (https://finnhub.io/dashboard) ou Alpha Vantage (https://www.alphavantage.co/support/#api-key). Inscription gratuite, la clé
s'affiche sur le tableau de bord du site. Les offres gratuites couvrent surtout les actions américaines.

## Ordres

Dans l'analyse d'une valeur : **Préparer un ordre d'achat / d'allègement / de vente**. L'application donne chaque champ à saisir
chez votre courtier (ISIN, quantité, limite, validité, stop facultatif), puis met à jour Mon PEA quand vous confirmez l'exécution.

## Tests

`cd backend && pip install -r requirements-dev.txt && python -m pytest -q tests` (150 tests, sans réseau).

## Catalogue

2 904 valeurs (1 742 éligibles PEA selon le pays du siège), mises à jour automatiquement chaque jour par l'application. Régénérer depuis les sources publiques : `python tools/build_catalog.py`
(cote Euronext, composants d'indices dans `tools/index_constituents.json`, grandes valeurs US, validation Yahoo).
Ajout manuel : ajouter des entrées `{"symbol": "ORA.PA", "name": "Orange SA"}` (symboles Yahoo Finance) dans `backend/catalog/*.json`,
ou créer un nouveau fichier par marché. Pays et éligibilité PEA sont déduits du suffixe (`.PA`, `.DE`, `.AS`…).

## Développement

```bash
cd backend && pip install -r requirements.txt && python main.py   # API sur :8000
cd frontend && npm install && npm run electron:dev                  # interface + fenêtre Electron
```

Publier une version : incrémenter `version` dans `frontend/package.json`, puis lancer le workflow « Release Windows » (onglet Actions) ou pousser un tag `vX.Y.Z`.
