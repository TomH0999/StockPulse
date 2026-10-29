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
- **Archive d'actualités** (Yahoo Finance + Google News, 24 mois reconstitués) : filtres mots-clés, source, sentiment,
  année / mois / jour, tri par date, pertinence, couverture médiatique ou sentiment.
- 4 langues (FR, EN, ES, 中文), thème clair / sombre.

## Développement

```bash
cd backend && pip install -r requirements.txt && python main.py   # API sur :8000
cd frontend && npm install && npm run electron:dev                  # interface + fenêtre Electron
```

Publier une version : incrémenter `version` dans `frontend/package.json`, puis lancer le workflow « Release Windows » (onglet Actions) ou pousser un tag `vX.Y.Z`.
