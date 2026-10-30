# StockPulse — Guide de démarrage de zéro

> StockPulse est un outil d'aide à la décision, pas un conseiller financier. Ses conseils, rejoués sur le passé, ont eu
> raison environ une fois sur deux (voir « Fiabilité des conseils ») : vérifiez toujours avant d'investir.

## 1. Installer l'application (10 min)

Téléchargez la dernière version sur https://github.com/TomH0999/StockPulse/releases/latest

| Système | Fichier | Installation |
|---|---|---|
| Windows 10/11 | `StockPulse-Setup-x.y.z.exe` | Double-clic. Si SmartScreen s'affiche : « Informations complémentaires » → « Exécuter quand même ». |
| macOS (puce Apple M1 et plus) | `StockPulse-x.y.z-mac-arm64.dmg` | Ouvrir le .dmg, glisser StockPulse dans Applications. Premier lancement : clic droit sur l'app → « Ouvrir » → « Ouvrir » (application non signée). Si macOS refuse : `xattr -cr /Applications/StockPulse.app` dans le Terminal. |
| Linux | `StockPulse-x.y.z-linux-x86_64.AppImage` ou `.deb` | AppImage : `chmod +x StockPulse-*.AppImage` puis double-clic. Debian/Ubuntu : `sudo apt install ./StockPulse-*.deb`. |

Vérification facultative de l'intégrité : comparer l'empreinte du fichier (`certutil -hashfile <fichier> SHA256` sous Windows,
`shasum -a 256 <fichier>` sous macOS / Linux) avec `SHA256SUMS-<système>.txt` de la release.

Les mises à jour s'installent ensuite toutes seules (Windows et Linux AppImage ; sur macOS, retéléchargez le .dmg).

Au premier lancement, la fenêtre « État de l'application » s'affiche : « Fraîcheur des analyses » est orange pendant
la première heure, le temps que l'application analyse les ~870 valeurs principales en arrière-plan. C'est normal.

## 2. Clés IA gratuites (15 min) — ⚙ Paramètres → Clés IA

Une clé = une capacité d'analyse supplémentaire. Chaque fournisseur a son propre quota : en combiner plusieurs est le plus
efficace. Collez chaque clé : elle est testée avant d'être enregistrée (chiffrée sur Windows).

| Fournisseur | Étapes | Capacité indicative |
|---|---|---|
| **Groq** (recommandé) | https://console.groq.com/keys → se connecter avec Google ou GitHub → *Create API Key* → nommer « StockPulse » → copier la clé `gsk_…` | ~300 analyses / jour |
| **Google Gemini** (recommandé) | https://aistudio.google.com/apikey → compte Google → accepter les conditions → *Create API key* → *Create API key in new project* → copier `AIza…` | ~200 / jour |
| **Cerebras** | https://cloud.cerebras.ai → *Sign up* (e-mail ou Google) → menu *API Keys* → *Generate API Key* → copier `csk-…` | ~400 / jour |
| **Mistral** | https://console.mistral.ai → créer un compte → *Choose a plan* → **Experiment** (gratuit, vérification par SMS) → *API Keys* → *Create new key* → copier | ~300 / jour |
| **OpenRouter** (appoint) | https://openrouter.ai → *Sign in* → https://openrouter.ai/settings/keys → *Create Key* (laisser la limite de crédit vide) → copier `sk-or-…` | ~45 / jour, modèles gratuits souvent saturés |

Règles importantes :
- Les quotas sont **par compte** : deux clés d'un même compte partagent le même quota, et créer plusieurs comptes chez un même
  fournisseur est en général interdit par ses conditions d'utilisation.
- L'application garde 30 % de chaque quota pour vos propres demandes et limite l'analyse IA automatique à votre PEA et vos
  favoris. La case « Utiliser aussi l'IA sur tout le catalogue » consomme beaucoup plus de quota : à éviter avec des clés gratuites.
- Une clé « en pause » affiche la raison (limite de débit ou quota du jour atteint) et l'heure de reprise.
- Ne partagez jamais vos clés. Si une clé a été exposée, supprimez-la sur le site du fournisseur et créez-en une autre.

## 3. Clés de données de marché (5 min) — ⚙ Paramètres → Clés de données

Elles ajoutent PER, marge, dette, rentabilité et les dates des prochains résultats / dividendes (cache de 7 jours par valeur,
récupérées seulement pour votre PEA, vos favoris et les valeurs que vous ouvrez).

| Fournisseur | Étapes | Quota gratuit |
|---|---|---|
| **Financial Modeling Prep** | https://site.financialmodelingprep.com/register → confirmer l'e-mail → *Dashboard* → copier l'*API Key* | 250 requêtes / jour |
| **Finnhub** | https://finnhub.io/register → *Dashboard* → copier l'*API key* | 60 requêtes / minute |
| **Alpha Vantage** | https://www.alphavantage.co/support/#api-key → remplir le formulaire → copier la clé affichée | 25 requêtes / jour |

Les offres gratuites couvrent surtout les actions américaines ; pour les valeurs européennes, le bloc « Fondamentaux » peut rester vide.

## 4. Réglages (2 min) — ⚙ Paramètres

- **Langue et thème** : en haut à droite.
- **Frais de courtage** : renseignez ceux de votre courtier pour des ordres justes. Exemples courants (à vérifier sur la grille
  tarifaire de votre courtier) : 0,5 % avec un minimum autour de 2 € chez les banques en ligne, frais fixes de quelques euros
  chez les courtiers à bas coût.
- **Analyses automatiques** : laissez-les activées ; renouvellement IA toutes les 12 h par défaut.

## 5. Renseigner votre PEA (5 min) — onglet « Mon PEA »

1. **Total des versements** : la somme versée depuis l'ouverture (sert au plafond de 150 000 € et à la performance).
2. **Liquidités** : le solde espèces disponible sur le PEA.
3. **Lignes** : pour chaque action détenue, recherchez-la, saisissez la quantité et le prix de revient unitaire (PRU) indiqués
   par votre courtier.
4. Consultez **Suggestions de rééquilibrage** : chaque action proposée a sa raison et un bouton « Préparer l'ordre ».
5. Après chaque ordre réellement passé chez le courtier, cliquez « J'ai passé cet ordre » : quantités, PRU et liquidités se
   mettent à jour partout.

## 6. Passer un ordre avec l'application

Dans l'onglet **Analyse** d'une valeur (ou depuis le rééquilibrage) : **Préparer un ordre d'achat / d'allègement / de vente**.
L'application donne, dans l'ordre, ce qu'il faut saisir chez le courtier :
compte PEA → ISIN → sens → quantité → ordre à cours limité et limite → validité jour → vérification du montant → validation.
Un ordre « stop » facultatif est proposé pour limiter les pertes. Vérifiez les avertissements affichés (valeur non éligible au
PEA, conseil défavorable, ligne trop lourde, liquidités insuffisantes).

## 7. Favoris de départ

Une base diversifiée (secteurs, pays) pour suivre le marché européen éligible PEA. Ajoutez-les avec ☆ dans l'onglet Analyse
ou « Ajouter aux favoris » dans l'onglet Entreprises.

| Rôle | Valeurs |
|---|---|
| Socle diversifié (ETF éligibles PEA) | CW8.PA (MSCI World), ESE.PA (S&P 500), PUST.PA (Nasdaq-100), C40.PA (CAC 40) |
| Luxe / consommation | MC.PA (LVMH), OR.PA (L'Oréal), RMS.PA (Hermès) |
| Énergie / industrie | TTE.PA (TotalEnergies), SU.PA (Schneider Electric), AI.PA (Air Liquide), AIR.PA (Airbus), SAF.PA (Safran) |
| Technologie | ASML.AS (ASML), SAP.DE (SAP), CAP.PA (Capgemini) |
| Santé | SAN.PA (Sanofi), EL.PA (EssilorLuxottica) |
| Finance / télécoms | BNP.PA (BNP Paribas), ALV.DE (Allianz), ORA.PA (Orange) |

Pour beaucoup d'investisseurs, un ETF Monde éligible PEA constitue le cœur du portefeuille, les actions individuelles venant
en complément. Diversifiez : au moins 5 lignes, aucune au-dessus de 20 %, aucun secteur au-dessus de 35 % (l'application
vous alerte).

## 8. Opportunités du moment

Les opportunités évoluent chaque jour : consultez **Tableau de bord → Opportunités PEA** et **Classement → Meilleur score
d'achat / Achats les plus fiables / Qualité en solde** (filtre « Éligibles PEA uniquement »). Instantané au moment de la
publication de cette version (analyse locale, sans IA) :

OPPORTUNITIES_TABLE

Avant d'acheter : ouvrez l'analyse, lisez les menaces, la fiabilité passée de la valeur et les articles récents ; préférez
plusieurs achats échelonnés à un achat unique.

## 9. Utilisation au quotidien

- **Tableau de bord** : état de l'application, PEA, alertes, opportunités, mouvements du jour, fiabilité des conseils.
- **Alertes** : la cloche 🔔 de l'onglet Analyse crée une alerte de prix ; les changements de conseil et les baisses de plus de
  5 % de vos lignes déclenchent une notification de l'ordinateur.
- **Classement / Entreprises** : 2 900 valeurs (1 740 éligibles PEA), mises à jour chaque jour ; les valeurs suspendues ou
  radiées sont étiquetées et exclues des classements.
- **État de l'application** (icône en haut) : si un point devient rouge, l'application vous prévient par notification.

## 10. Dépannage

| Problème | Solution |
|---|---|
| L'analyse reste « locale » | Vérifiez Paramètres → Clés IA : clé en pause (quota du jour) ou en erreur. Ajoutez un autre fournisseur. |
| « Fondamentaux » vide | Valeur non couverte par l'offre gratuite du fournisseur de données. |
| Pas de cours | Marché fermé ou source momentanément indisponible : l'état de l'application l'indique. |
| Données à réinitialiser | Fermer l'application et supprimer le dossier de données : `%APPDATA%\stockpulse-frontend` (Windows), `~/Library/Application Support/stockpulse-frontend` (macOS), `~/.config/stockpulse-frontend` (Linux). |
