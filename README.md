# StockPulse

Centrale bourse & actualités pour ordinateur : cours en direct, graphiques, archive d'articles et conseil d'investissement.

## Installer (Windows)

Télécharger `StockPulse-Setup-x.y.z.exe` depuis la page [Releases](https://github.com/TomH0999/StockPulse/releases) et l'exécuter.
Windows SmartScreen peut afficher un avertissement (application non signée) : « Informations complémentaires » → « Exécuter quand même ».

## Fonctionnalités

- **Favoris** : épingler des actions (☆), cours et verdict en un coup d'œil, réorganisation par glisser-déposer.
- **Recherche** sur tous les marchés (actions, ETF, indices) par nom ou ticker.
- **Graphique** de 1 jour à l'historique complet, repère de la date d'un article.
- **Conseil** Achat fort / Achat / Conserver / Alléger / Vendre avec opportunités, menaces, patterns historiques
  (réaction de l'action après ses chocs passés, saisonnalité, tendance) et rebondissements majeurs reliés aux articles.
  Moteur local sans clé ; analyse IA de chaque article avec une clé gratuite Google Gemini ou Groq (Paramètres ⚙).
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

## Agrandir le catalogue

Ajouter des entrées `{"symbol": "ORA.PA", "name": "Orange SA"}` (symboles Yahoo Finance) dans `backend/catalog/*.json`,
ou créer un nouveau fichier par marché. Pays et éligibilité PEA sont déduits du suffixe (`.PA`, `.DE`, `.AS`…).

## Développement

```bash
cd backend && pip install -r requirements.txt && python main.py   # API sur :8000
cd frontend && npm install && npm run electron:dev                  # interface + fenêtre Electron
```

Publier une version : incrémenter `version` dans `frontend/package.json`, puis lancer le workflow « Release Windows » (onglet Actions) ou pousser un tag `vX.Y.Z`.
