# StockPulse

Centrale bourse & actualités : cours en direct, graphiques, archive d'articles, portefeuilles.

## Tester en un clic (site web)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/TomH0999/StockPulse)

Plan gratuit : le service se met en veille après 15 min d'inactivité et la base SQLite repart de zéro à chaque redéploiement.

**Ajouter au PC portable** : ouvrir le site dans Chrome ou Edge → icône « Installer » dans la barre d'adresse.

## Lancer en local (Windows)

Prérequis : Python 3.11+ et Node.js. Double-cliquer sur `StockPulse.bat` → http://127.0.0.1:8000

## Développement

```bash
cd backend && python main.py          # API sur :8000
cd frontend && npm run dev            # interface sur :5173
```
