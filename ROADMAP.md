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

## 🔜 v1.3 — Catalogue PEA complet et fondamentaux
- Catalogue SBF 120 + grandes valeurs européennes + ETF éligibles PEA, secteurs
- Fondamentaux (PER, rendement du dividende, dette) intégrés au conseil et au classement

## v1.4 — Mesure de la qualité des conseils et alertes
- Historique des conseils et taux de réussite à 1 / 3 / 6 mois (backtest) affiché à côté du verdict
- Alertes Windows : seuil de prix, changement de verdict, forte variation d'une ligne du PEA
- Calendrier des résultats et des dividendes

## v1.5 — Gestion de portefeuille avancée
- Diversification (secteur, pays, poids par ligne) et suggestions de rééquilibrage
- Comparaison à un indice de référence (CAC 40, MSCI Europe)

## v2.0 — Multi-plateforme
- Installateurs macOS et Linux, signature de code Windows / macOS
