# StockPulse

Centrale bourse & actualités pour ordinateur : cours en direct, graphiques, archive d'articles et conseil d'investissement.

## Installer (Windows)

Télécharger `StockPulse-Setup-x.y.z.exe` depuis la page [Releases](https://github.com/TomH0999/StockPulse/releases) et l'exécuter.
Vérifier l'intégrité (facultatif) : `certutil -hashfile StockPulse-Setup-x.y.z.exe SHA256` doit correspondre à `SHA256SUMS.txt` de la release.
Windows SmartScreen peut afficher un avertissement (application non signée) : « Informations complémentaires » → « Exécuter quand même ».

Feuille de route : [ROADMAP.md](ROADMAP.md)

## Fonctionnalités

- **Tableau de bord** (accueil) : PEA, alertes, état de l'application, opportunités PEA, mouvements du jour, favoris.
- **Mon PEA** : diversification, suggestions de rééquilibrage, comparaison au CAC 40, lignes détenues, valeur et plus-value en direct, poids, conseil et alertes par ligne, plafond de versements.
- **Vérificateur d'état** au lancement (cours, sources, clés IA, base, fraîcheur, version) avec notification Windows si un contrôle se dégrade ;
  contrôle anti-hallucination des analyses IA (chiffres cités confrontés aux données, cohérence du verdict).
- **Sécurité** : clés IA chiffrées (Windows DPAPI), API locale réservée à l'application, empreinte SHA-256 publiée, mises à jour automatiques.

- **Favoris** : épingler des actions (☆), cours et verdict en un coup d'œil, réorganisation par glisser-déposer.
- **Recherche** sur tous les marchés (actions, ETF, indices) par nom ou ticker.
- **Graphique** de 1 jour à l'historique complet, repère de la date d'un article.
- **Conseil** Achat fort / Achat / Conserver / Alléger / Vendre avec opportunités, menaces, patterns historiques
  (réaction de l'action après ses chocs passés, saisonnalité, tendance) et rebondissements majeurs reliés aux articles.
  Moteur local sans clé ; analyse IA de chaque article avec une clé gratuite Google Gemini ou Groq (Paramètres ⚙).
- **Fiabilité des conseils** : analyse rejouée sur 5 ans, taux de réussite affiché ; **alertes** de prix et de changement de conseil.
- **Classement** : plus fortes hausses / baisses (jour, semaine, mois, 3 mois, depuis janvier, 1 an), meilleur score
  d'achat, achats les plus fiables, qualité en solde, moins volatiles, plus à risque, prix ; filtre PEA et pays.
- **Entreprises** : liste complète du catalogue avec tri, recherche, filtres et aperçu (mini-graphique, performances, conseil).
- **Analyses automatiques** : tout le catalogue est analysé en arrière-plan (local), puis par IA selon la capacité des clés.
- **Archive d'actualités** (Yahoo Finance + Google News, 24 mois reconstitués) : filtres mots-clés, source, sentiment,
  année / mois / jour, tri par date, pertinence, couverture médiatique ou sentiment.
- 4 langues (FR, EN, ES, 中文), thème clair / sombre.

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

`cd backend && pip install -r requirements-dev.txt && python -m pytest -q tests` (86 tests, sans réseau).

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
