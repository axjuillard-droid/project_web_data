# Rapport SWRL - Raisonnement Symbolique

Ce rapport documente les résultats de l'application des règles logiques SWRL.

## Règles Appliquées
1. **hasCompeted** : Prémisses `Athlete(?a1), participatedIn(?a1, ?c), participatedIn(?a2, ?c), differentFrom(?a1, ?a2) -> hasCompeted(?a1, ?a2)`
2. **sameNationality** : Prémisses `Athlete(?a1), represents(?a1, ?c), represents(?a2, ?c), differentFrom(?a1, ?a2) -> sameNationality(?a1, ?a2)`
3. **multiMedalist** : Prémisses `Athlete(?a), wonMedal(?a, ?m1), GoldMedal(?m1), wonMedal(?a, ?m2), SilverMedal(?m2) -> multiMedalist(?a)`

## Résultats de l'Inférence
- **hasCompeted** : 44
- **multiMedalist** : 2
- **sameNationality** : 50


## Comparaison SWRL vs KGE
Le raisonnement SWRL (symbolique) fournit des résultats déterministes basés sur des règles strictes. 
- La règle `hasCompeted` découverte par SWRL peut être comparée aux scores de proximité dans l'espace latent du modèle KGE.
- Les faits prédits par le KGE avec un score élevé mais non présents en SWRL peuvent indiquer des relations manquantes ou des similarités structurelles.
