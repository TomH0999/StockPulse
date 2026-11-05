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

## 3. Clés de données de marché (facultatif) — ⚙ Paramètres → Clés de données

Depuis la v3, **les comptes des entreprises (chiffre d'affaires, free cash-flow, ROIC, dette, dividendes…) sont récupérés sans
clé**, y compris pour les valeurs européennes. Ces clés n'ajoutent plus que les dates des prochains résultats et l'objectif de
cours des analystes.

| Fournisseur | Étapes | Quota gratuit |
|---|---|---|
| **Financial Modeling Prep** | https://site.financialmodelingprep.com/register → confirmer l'e-mail → *Dashboard* → copier l'*API Key* | 250 requêtes / jour |
| **Finnhub** | https://finnhub.io/register → *Dashboard* → copier l'*API key* | 60 requêtes / minute |
| **Alpha Vantage** | https://www.alphavantage.co/support/#api-key → remplir le formulaire → copier la clé affichée | 25 requêtes / jour |

Les offres gratuites couvrent surtout les actions américaines ; pour les valeurs européennes, le bloc « Fondamentaux » peut rester vide.

## 4. Réglages (2 min) — ⚙ Paramètres

- **Langue et thème** : en haut à droite.
- **Frais de courtage** : renseignez ceux de votre courtier (le plafond légal en PEA est de 0,5 % par ordre en ligne ; beaucoup
  de courtiers sont bien en dessous). Les valeurs par défaut (0,5 %, minimum 1,99 €) sont à remplacer.
- **Stop et objectif dans les ordres** : désactivés par défaut. Sur une ligne de long terme, un stop vend souvent au pire moment.
- **Analyses automatiques** : l'analyse locale tourne seule en arrière-plan ; l'analyse IA se lance à la demande avec le bouton « Analyser avec l'IA » (elle tient compte de votre position et de votre PEA).

## 5. Renseigner vos comptes (5 min) — onglet « Mes comptes »

Le PEA existe par défaut. **« + Compte »** ajoute un PEA-PME, un PEA jeune, un compte-titres (CTO) ou une assurance-vie ; chaque
compte a son journal, ses liquidités, son plafond et sa fiscalité (taux 2026 : prélèvements sociaux 18,6 %, flat tax 31,4 % ;
assurance-vie 17,2 %). Le PEA-PME partage le plafond de 225 000 € avec le PEA. Dans un compte-titres, les moins-values sont
reportées 10 ans et l'impôt de l'année est estimé.

Chaque compte fonctionne comme un journal de mouvements : liquidités, PRU, plus-values et plafond sont calculés automatiquement.
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
7. **Performance & dividendes** : rendement réel (TRI, dates des versements comprises) et la question honnête : « avec les mêmes
   versements aux mêmes dates sur un ETF MSCI World dividendes réinvestis (CW8), combien aurais-je ? ».
8. **Ma thèse** (icône carnet sur chaque ligne, ou dans l'Analyse) : pourquoi vous détenez l'entreprise, ce qu'elle vaut selon
   vous, quand vous vendriez. Un rappel vous demande de la relire chaque année.
9. Après chaque ordre réellement passé chez le courtier, cliquez « J'ai passé cet ordre » : quantités, PRU et liquidités se
   mettent à jour partout.

## 6. Passer un ordre avec l'application

Dans l'onglet **Analyse** d'une valeur (ou depuis le rééquilibrage) : **Préparer un ordre d'achat / d'allègement / de vente**.
L'application donne, dans l'ordre, ce qu'il faut saisir chez le courtier :
compte PEA → ISIN → sens → quantité → ordre à cours limité et limite → validité jour → vérification du montant → validation.
L'application indique aussi l'enveloppe adaptée (PEA pour une société européenne, compte-titres avec formulaire W-8BEN pour une
action américaine). Le prix limite est arrondi à un pas de cotation accepté quelle que soit la liquidité du titre. Vérifiez les
avertissements affichés (valeur non éligible, ETF à effet de levier, ligne trop lourde, liquidités insuffisantes).

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

Les opportunités évoluent : consultez **Tableau de bord → Qualité à prix raisonnable** et **Classement** (meilleure qualité,
meilleurs rendements de free cash-flow, les moins chères face à leur historique, ROIC, dividendes réguliers, bilans solides).
Instantané au moment de la publication de la v3.0 (modèle long terme, sans IA), sur 456 grandes valeurs éligibles au PEA :

| Valeur | Secteur | Conseil | Score | Qualité | Rendement FCF | ROIC / ROE moyen | PER / sa médiane | Avantage vs CW8 (1 an) | Devise |
|---|---|---|---|---|---|---|---|---|---|
| Evolution AB (publ) (EVO.ST) | Consumer Cyclical | Achat fort | +88 | 25/25 | 7,2 % | 27 % | 15 / 22 | +0,1 pts | SEK |
| Pandora A/S (PNDORA.CO) | Consumer Cyclical | Achat fort | +85 | 25/25 | 8,2 % | 42 % | 13 / 17 | 0,0 pts | DKK |
| Wolters Kluwer N.V. (WKL.AS) | Industrials | Achat fort | +80 | 25/25 | 6,5 % | 22 % | 16 / 32 | +0,9 pts | EUR |
| Ryanair Holdings plc (RYA.IR) | Industrials | Achat fort | +74 | 25/25 | 6,9 % | 18 % | 12 / 13 | 0,0 pts | EUR |
| Hugo Boss AG (BOSS.DE) | Consumer Cyclical | Achat fort | +72 | 22/25 | 18,7 % | 18 % | 11 / 18 | +1,0 pts | EUR |
| Nemetschek SE (NEM.DE) | Technology | Achat fort | +72 | 25/25 | 5,0 % | 19 % | 36 / 56 | -1,7 pts | EUR |
| TUI AG (TUI1.DE) | Consumer Cyclical | Achat fort | +70 | 17/25 | 34,6 % | 30 % | 6 / 7 | -0,6 pts | EUR |
| Publicis Groupe S.A. (PUB.PA) | Communication Services | Achat fort | +67 | 17/25 | 10,2 % | 12 % | 16 / 16 | 0,0 pts | EUR |
| RATIONAL Aktiengesellschaft (RAA.DE) | Industrials | Achat fort | +66 | 22/25 | 3,0 % | 28 % | 29 / 37 | -8,3 pts | EUR |
| Amadeus IT Group, S.A. (AMS.MC) | Technology | Achat fort | +64 | 11/25 | 5,4 % | 14 % | 20 / 27 | +8,1 pts ✓ | EUR |
| Dassault Systèmes SE (DSY.PA) | Technology | Achat fort | +63 | 13/25 | 4,2 % | 10 % | 29 / 48 | 0,0 pts | EUR |
| Logista Integral, S.A. (LOG.MC) | Industrials | Achat fort | +62 | 22/25 | 7,3 % | 44 % | 16 / 12 | 0,0 pts | EUR |
| Beiersdorf Aktiengesellschaft (BEI.DE) | Consumer Defensive | Achat fort | +61 | 19/25 | 1,7 % | 10 % | 20 / 32 | 0,0 pts | EUR |
| Jerónimo Martins, SGPS, S.A. (JMT.LS) | Consumer Defensive | Achat fort | +61 | 22/25 | 11,2 % | 24 % | 19 / 19 | 0,0 pts | EUR |
| Kongsberg Maritime ASA (KMAR.OL) | Industrials | Achat fort | +61 | 22/25 | 8,4 % | 38 % | 14 / – | – | NOK |

Lecture honnête :
- 165 valeurs sur 456 ressortent « Achat » ou « Achat fort » : ce sont des entreprises rentables, peu endettées et pas
  plus chères que leur propre historique. Ce n'est pas une prédiction de hausse.
- La colonne « Avantage vs CW8 » mesure si ce même modèle, rejoué chaque mois depuis la publication des comptes disponibles
  (2023-2025), a fait mieux que le MSCI World : en moyenne **non** (−3,5 points sur toutes les valeurs testées). ✓ = avantage d'au
  moins 5 points sur la valeur ; avec si peu d'années, une partie de ces ✓ relève du hasard.
- Plusieurs valeurs sont cotées en couronnes (SEK, DKK, NOK) : vérifiez que votre courtier y donne accès dans le PEA.
- Pour la majorité des investisseurs, un ETF MSCI World (CW8, WPEA, DCAM) en socle reste la base la plus robuste ; les actions
  en direct se justifient si vous savez écrire pourquoi vous les détenez (onglet « Ma thèse »).

## 9. Utilisation au quotidien

- **Tableau de bord** : état de l'application, comptes, alertes, qualité à prix raisonnable, thèses à relire, fiabilité mesurée.
- **Analyse** : verdict long terme (fondamentaux et valorisation 60 %, qualité 25 %, tendance 200 jours 15 %), fiabilité mesurée
  face au MSCI World, chiffres de l'entreprise, risque et taille de ligne, enveloppe conseillée. L'IA donne une lecture à part :
  elle explique, elle ne décide pas.
- **Alertes** : seulement vos alertes de prix (cloche 🔔) et la revue annuelle de vos thèses ; plus d'alerte sur les variations du
  jour ni sur les changements de verdict.
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
