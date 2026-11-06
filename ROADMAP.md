# Feuille de route StockPulse

Ordre choisi pour livrer d'abord la sécurité et la fiabilité, puis ce qui sert directement la gestion du PEA,
et regrouper les travaux qui touchent les mêmes fichiers.

## ✅ v1.0 — Base
Favoris, conseil local + IA, archive d'articles, installateur Windows.

## ✅ v1.1 — Exploration du marché
Classement, liste des entreprises, analyses automatiques, pool de clés IA multi-fournisseurs, catalogue extensible.

## ✅ v1.2 — Fiabilité, sécurité, PEA
- [x] Sécurité : clés IA chiffrées (Windows DPAPI), empreinte SHA-256 publiée avec l'installateur,
      mises à jour automatiques de l'application (GitHub Releases)
- [x] Vérificateur d'état : sources de données, fraîcheur des cours, clés IA, base de données, version à jour ;
      résumé au lancement et notification Windows en cas de dégradation
- [x] Anti-hallucination : chiffres cités par l'IA comparés aux données calculées, cohérence verdict / score,
      écart IA / analyse locale signalé
- [x] Mon PEA : lignes détenues (quantité, prix de revient), valeur et plus-value en direct, poids, conseil et
      alertes par ligne, suivi du plafond de versements (150 000 €)
- [x] Page d'accueil « Tableau de bord » : état de l'app, PEA, favoris, opportunités, alertes

## ✅ v1.3 — Catalogue élargi et fondamentaux
- [x] 2 904 valeurs : toute la cote Euronext (Paris, Amsterdam, Bruxelles, Lisbonne, Dublin, Milan, Oslo),
      DAX / MDAX / SDAX, IBEX 35, OMX Stockholm / Copenhague / Helsinki, ATX, WIG20, ETF PEA courants,
      SMI, FTSE 100, ~980 grandes valeurs américaines (> 10 Md$), grandes valeurs Asie / Canada / Australie
- [x] 1 814 valeurs éligibles PEA, 868 valeurs principales analysées automatiquement, secteurs (2 812 valeurs)
- [x] Rendement du dividende intégré au conseil
- [x] Générateur reproductible : `python tools/build_catalog.py`
- [x] PER, marge, dette, ROE via clés gratuites (Financial Modeling Prep, Finnhub, Alpha Vantage) — v1.6

## ✅ v1.4 — Qualité des conseils et alertes
- [x] Fiabilité passée : analyse rejouée chaque mois sur 5 ans, taux de réussite à 1 / 3 / 6 mois par valeur et global
- [x] Historique quotidien des conseils
- [x] Alertes Windows : seuils de prix, changement de conseil (favoris / PEA), baisse > 5 % d'une ligne
- [x] Prochains résultats et dividendes (mêmes clés) — v1.6

## ✅ v1.5 — Gestion de portefeuille avancée
- [x] Diversification par secteur et pays, alertes de concentration (ligne > 20 %, secteur > 35 %, < 5 lignes)
- [x] Suggestions de rééquilibrage (titres à vendre, lignes à réexaminer, idées dans les secteurs absents)
- [x] Comparaison au CAC 40 (lignes actuelles rejouées sur 1 an)

## ✅ v1.6 — Ordres, catalogue vivant, fiabilité
- [x] Générateur d'ordres (achat, allègement, vente) : champs à saisir chez le courtier, stop et objectif, frais, mise à jour de Mon PEA
- [x] Catalogue mis à jour chaque jour (sources publiques, aucun jeton IA) : nouvelles valeurs, étiquettes « Suspendue » / « Radiée »
- [x] Éligibilité PEA selon le pays du siège (ISIN) au lieu de la place de cotation
- [x] 86 tests automatiques (moteur, API, sécurité, ordres, alertes, catalogue) lancés sous Windows avant chaque publication

## ✅ v1.6.1 — Clés IA
- [x] Analyse automatique limitée à 70 % du quota quotidien, priorité aux demandes de l'utilisateur, quota du jour détecté

## ✅ v2.0 — Version finale multi-plateforme
- [x] Rééquilibrage par allocation cible (conviction × fiabilité / volatilité, plafonds ligne et secteur), ordres préparés
- [x] Mise à jour immédiate de tous les écrans après un ordre ou une modification du PEA
- [x] Installateurs Windows, macOS (Apple Silicon) et Linux (AppImage, deb), empreintes SHA-256
- [x] Guide de démarrage complet : docs/GUIDE.md
- [ ] Signature de code Windows / macOS (certificat payant)

## ✅ v2.1 — PEA tenu comme un journal
- [x] Versements, retraits, achats, ventes, dividendes ; liquidités, PRU (frais inclus), plus-values réalisées et plafond calculés
- [x] Données des versions précédentes converties automatiquement ; mouvements incohérents refusés
- [x] Lignes hors euro converties ; poids calculés sur la valeur totale du PEA
- [x] L'agent IA tient compte de la position et du PEA ; IA uniquement à la demande (plus d'analyse IA automatique)
- [ ] Clés chiffrées sur macOS / Linux (trousseau du système)

## ✅ v2.2 — Suggestions de long terme et outils de gestion du PEA
- [x] Suggestions sans aller-retour : « Plan d'ensemble » (toutes les suggestions combinées, vérifiées) et « Conseil ligne par ligne »
- [x] Import CSV des opérations du courtier, modification d'un mouvement
- [x] Date d'ouverture : échéance des 5 ans et impôt estimé en cas de retrait
- [x] Historique reconstitué et performance réelle (pondérée dans le temps) vs CAC 40 et MSCI World
- [x] TTF (0,4 %) et frais de change calculés ; objectifs (versement programmé, part d'ETF, plafonds) ; plan du prochain versement
- [x] Calendrier des dividendes reçus / attendus et rendement du portefeuille
- [x] Outil de calibration du modèle local (tools/calibrate.py) : aucune pondération ne bat l'actuelle hors échantillon, modèle inchangé

## ✅ v2.3 — Analyses groupées, historique IA, ETF & marchés, News
- [x] Analyses IA groupées (1, 10, 25, 50, 100) : verdict de synthèse, accord, dispersion, intervalle de confiance, fréquence des idées
- [x] Analyses IA enregistrées (détail dépliable, date) avec indice de renouvellement (âge, variation du cours, nouveaux articles)
- [x] Page « ETF & marchés » : 101 ETF, indices, matières premières, devises, crypto ; filtre par type dans la recherche
- [x] Onglet News : actualités les plus couvertes et sujets récurrents, par jour / semaine / mois / année ou historique (année, mois)

## ✅ v2.4 — Conseils plus fiables et page Analyse en onglets
- [x] Fiabilité : « Pas de signal fiable » quand les conseils passés (rejoués sur 5 ans + réellement émis, comptés double) ne dépassent pas 55 % de justes
- [x] Risque : volatilité, bêta, pire baisse, mauvaise année, taille de ligne maximale conseillée
- [x] Force relative : écart à l'indice (6 et 12 mois), tendance 12 mois hors dernier mois, rang dans le secteur
- [x] Chiffres de l'entreprise : chiffre d'affaires, bénéfice, marges, croissance, BPA, capitalisation, comptes annuels, note de santé financière
- [x] IA : raisonnement plus poussé, chiffres et risque fournis, ancrage sur le modèle local, scénarios et probabilité corrigés vers la moyenne du marché
- [x] IA groupée : conseil retenu seulement à partir de 10 analyses et 70 % d'accord
- [x] Page Analyse : carte « Décision » à côté du graphique et onglets Entreprise / Risque & force / Fiabilité / IA groupée / Historique IA / Rebondissements / Actualités

## ✅ v3.0 — Investisseur long terme
- [x] Moteur refondu : fondamentaux et valorisation 60, qualité et régularité 25, tendance 200 jours 15 ; RSI, croisements, paris sur rebond, saisonnalité et sentiment des articles retirés du score
- [x] Comptes publiés sans clé (Yahoo, 4 exercices) : free cash-flow, ROIC, marges, dette nette / EBITDA, couverture, dilution, dividende (croissance, années sans baisse, taux de distribution), PER face à l'historique ; conversion de devise comptes / cotation
- [x] Seuils sectoriels (banques, assurances, foncières : ROE, pas de ratio de dette) ; rendement total (dividendes réinvestis)
- [x] Backtest honnête : même moteur, comptes connus à la date, comparaison à CW8, taux de base, horizons 1 / 3 / 5 ans
- [x] L'IA n'a plus le dernier mot : lecture séparée, verdict inchangé
- [x] Plusieurs comptes (PEA, PEA-PME, PEA jeune, CTO, assurance-vie), plafonds, fiscalité 2026 (LFSS 2026), moins-values reportables, enveloppe conseillée
- [x] TRI et comparaison « si tout sur CW8 » ; ancien comparatif « portefeuille actuel rejoué » retiré (biais rétrospectif)
- [x] Journal de thèse avec revue annuelle
- [x] Diversification à travers les ETF ; ETF larges exemptés de la règle des 20 % ; ETF à levier signalés et exclus des suggestions
- [x] Stop facultatif (désactivé par défaut), pas de cotation sûrs, alertes réduites (ni variations du jour ni changements de verdict)
- [x] Classements et tableau de bord long terme (plus de « plus fortes hausses du jour ») ; langues réduites au français et à l'anglais
- [x] Liechtenstein retiré par prudence des pays éligibles ; éligibilité « à confirmer » pour les valeurs sans ISIN

## ✅ v3.1 — Prouver avant d'affirmer
- [x] Fiabilité du modèle mesurée en coupe transversale (toutes les valeurs classées chaque mois, corrélation de rang à 12 mois, quintiles, face au STOXX Europe 600 et au MSCI World), intervalle de confiance de Student sur les années indépendantes ; état gris « non mesurable » quand l'intervalle contient 0, rouge seulement si négatif prouvé
- [x] Mesure du 06/11/2026 sur 292 valeurs PEA, 31 mois : IC +0,12 [−0,41 ; +0,64] → non mesurable ; ordre des verdicts cohérent (Achat fort +4,0 pts, Vendre −8,2 pts face à l'univers) ; tendance (+0,12) et force 12-1 (+0,18) restent les signaux les plus utiles
- [x] Outil de calibration walk-forward (tools/validate.py) : pondérations inchangées (gain de test non significatif, surajustement probable)
- [x] Garde-fou « valeur + tendance », force relative 12-1 dans le score, bénéfices normalisés pour les cycliques, verdict symétrique (thèse fragilisée → « Alléger »)
- [x] Prompt de l'IA corrigé (ancrage vide), restes court terme retirés, extraction structurée des articles (type d'événement, ampleur, durable, avantage concurrentiel)
- [x] Étude d'événements sur l'archive (rendement anormal à 0 / 5 / 20 / 60 séances), test « déjà dans les prix ? », filtre de pertinence (la société doit être nommée)
- [x] Surprises de résultats, révisions des analystes et transactions des dirigeants (clé gratuite Finnhub, FMP pour les surprises)
- [x] Précision de l'IA mesurée à l'échéance (score de Brier) et correction AI_SHRINK réglée dessus dès 30 échéances
- [x] Archive locale des comptes : l'historique s'allonge au-delà des 4 exercices servis par la source
- [x] Retenues à la source par pays sur le compte-titres ; notes affichées (assurance-vie après 8 ans, gains PEA avant 2018, composition approchée des ETF) ; « PEA à confirmer » dans les ordres
- [x] Analyses IA groupées limitées à 10 et présentées comme de la stabilité, pas de la fiabilité
- [ ] À venir : comptes sur 10 ans (SEC EDGAR, ESEF / filings.xbrl.org), exposition géographique par chiffre d'affaires, valorisation face au secteur, base BDIF de l'AMF, source de cours de secours
