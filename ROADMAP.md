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
- [ ] Clés chiffrées sur macOS / Linux (trousseau du système)
