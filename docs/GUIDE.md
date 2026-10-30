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
- L'IA n'est utilisée que lorsque vous cliquez sur « Analyser avec l'IA » (1 requête par clic) : aucun quota n'est consommé en arrière-plan.
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
- **Analyses automatiques** : l'analyse locale tourne seule en arrière-plan ; l'analyse IA se lance à la demande avec le bouton « Analyser avec l'IA » (elle tient compte de votre position et de votre PEA).

## 5. Renseigner votre PEA (5 min) — onglet « Mon PEA »

Le PEA fonctionne comme un journal de mouvements : liquidités, PRU, plus-values et plafond sont calculés automatiquement.
1. **Versement** : saisissez vos versements (date, montant) ; c'est la seule façon d'alimenter le PEA.
2. **Achat** : pour chaque action détenue, saisissez vos achats (date, quantité, prix unitaire, frais) tels qu'indiqués par
   votre courtier ; le PRU est calculé (frais inclus). Pour une reprise rapide, un seul achat au PRU affiché par votre courtier suffit.
3. **Vente / Dividende / Retrait** : à saisir au fil de l'eau ; la plus-value réalisée est calculée à chaque vente.
4. Plus rapide : **Journal & import → Import depuis votre courtier (CSV)** : exportez l'historique de votre PEA depuis le site du
   courtier, chargez le fichier, vérifiez l'aperçu puis importez.
5. **Objectifs** : date d'ouverture du PEA (échéance des 5 ans, impôt estimé en cas de retrait), versement mensuel programmé,
   part d'ETF souhaitée, plafonds par ligne / secteur, frais de change de votre courtier.
6. **Vue d'ensemble → Plan d'ensemble** : toutes les suggestions combinées (aucune vente pour financer un autre achat, pas
   d'allègement d'une ligne récente) ; **Conseil ligne par ligne** : que faire de chaque ligne prise isolément.
7. **Performance & dividendes** : vraie performance du PEA comparée au CAC 40 et au MSCI World, dividendes reçus et attendus.
8. Après chaque ordre réellement passé chez le courtier, cliquez « J'ai passé cet ordre » : quantités, PRU et liquidités se
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

Analyse du 30/10/2026 ; filtre : éligible PEA, conseil « Achat » ou « Achat fort » (score ≥ 25), fiabilité passée à 3 mois ≥ 55 %.

| Valeur | Secteur | Conseil | Score | Fiabilité 3 mois | Hausse 3 mois | Devise |
|---|---|---|---|---|---|---|
| Lottomatica Group S.p.A. (LTMC.MI) | Consumer Cyclical | Achat fort | +62 | 59 % | +8.6 % | EUR |
| Frontline plc (FRO.OL) | Energy | Achat fort | +55 | 63 % | +37.1 % | NOK |
| Klaveness Combination Carriers ASA (KCC.OL) | Industrials | Achat fort | +53 | 61 % | +11.9 % | NOK |
| Eni S.p.A. (ENI.MI) | Energy | Achat fort | +51 | 58 % | +12.1 % | EUR |
| Evonik Industries AG (EVK.DE) | Basic Materials | Achat fort | +49 | 56 % | +21.2 % | EUR |
| Technoprobe S.p.A. (TPRO.MI) | Technology | Achat fort | +47 | 57 % | -5.1 % | EUR |
| Smartoptics Group ASA (SMOP.OL) | Technology | Achat fort | +45 | 58 % | +17.0 % | NOK |
| Iberdrola, S.A. (IBE.MC) | Utilities | Achat fort | +45 | 65 % | +6.7 % | EUR |
| Höegh Autoliners ASA (HAUTO.OL) | Industrials | Achat fort | +45 | 57 % | +7.4 % | NOK |
| Jyske Bank A/S (JYSK.CO) | Financial Services | Achat fort | +44 | 56 % | +5.2 % | DKK |

Ces signaux reposent surtout sur la tendance des cours (aucune analyse IA ni fondamentaux dans cet instantané) ; plusieurs valeurs sont cotées en couronnes (NOK, DKK) : vérifiez que votre courtier y donne accès dans le PEA.

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
