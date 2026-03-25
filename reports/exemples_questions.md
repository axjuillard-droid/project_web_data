# Questions de test — Assistant RAG
# Knowledge Graph Sportifs & Compétitions

## Questions de référence avec réponses attendues

Ces questions servent à évaluer la qualité du système RAG.

---

### Catégorie 1 — Médailles et palmarès

| Question | Entité | Réponse attendue (KB) |
|----------|--------|----------------------|
| Quelles médailles a remporté Usain Bolt ? | UsainBolt | Gold Medal |
| Quel est le palmarès de Serena Williams ? | SerenaWilliams | Gold Medal |
| Simone Biles a-t-elle remporté des médailles d'argent ? | SimoneBiles | Silver Medal (si dans la KB) |
| Qui sont les multi-médaillés ? | — | Athlètes inférés SWRL multiMedalist |

---

### Catégorie 2 — Participations

| Question | Entité | Réponse attendue |
|----------|--------|-----------------|
| À quelles compétitions a participé Usain Bolt ? | UsainBolt | JO Beijing 2008, London 2012, Rio 2016 |
| Lionel Messi a-t-il participé à la Coupe du Monde 2022 ? | LionelMessi | FIFAWorldCup2022 |
| À quels tournois du Grand Chelem Federer a-t-il participé ? | RogerFederer | Wimbledon, Australian Open, US Open |
| Eliud Kipchoge a-t-il participé aux JO de Paris 2024 ? | EliudKipchoge | OlympicsParis2024 |

---

### Catégorie 3 — Sports et nationalités

| Question | Entité | Réponse attendue |
|----------|--------|-----------------|
| Quel sport pratique Lionel Messi ? | LionelMessi | Football |
| Quelle est la nationalité de Rafael Nadal ? | RafaelNadal | Spain |
| Quels athlètes représentent la France ? | France | KylianMbappe (+ autres si dans KB) |
| Quels athlètes kenyans sont dans la base ? | Kenya | EliudKipchoge |

---

### Catégorie 4 — Relations inférées (SWRL)

| Question | Entité | Propriété inférée | Réponse attendue |
|----------|--------|------------------|-----------------|
| Qui sont les rivaux de Novak Djokovic ? | NovakDjokovic | hasCompeted | Roger Federer, Rafael Nadal (même tournoi) |
| Qui sont les compatriotes d'Usain Bolt ? | UsainBolt | sameNationality | (athlètes jamaïcains dans la KB) |
| Qui sont les compatriotes de Kylian Mbappé ? | KylianMbappe | sameNationality | (athlètes français dans la KB) |

---

### Catégorie 5 — Compétitions

| Question | Entité | Réponse attendue |
|----------|--------|-----------------|
| Quelles compétitions ont eu lieu en France ? | France | OlympicsParis2024, RolandGarros… |
| Quelles compétitions ont eu lieu au Japon ? | Japan | OlympicsTokyo2020 |
| Quelle est l'année des JO de Tokyo ? | OlympicsTokyo2020 | 2021 |
| Où se trouve Wimbledon ? | Wimbledon | London / UnitedKingdom |

---

### Catégorie 6 — Cas limites (à documenter)

| Question | Comportement attendu |
|----------|---------------------|
| Quelle est la taille d'Usain Bolt ? | "Information non disponible dans la KB" |
| Qui a gagné le 100m aux JO 2020 ? | Fallback général + mention absence de détail |
| Querida ¿quien es el mejor deportista? | Entité non détectée → liste générale |
| Quel est le salaire de Cristiano Ronaldo ? | "Information non disponible" |

---

## Critères d'évaluation

| Critère | Description | Cible |
|---------|-------------|-------|
| **Couverture** | % de questions avec ≥ 1 triplet trouvé | ≥ 80% |
| **Traçabilité** | Triplets sources cités dans la réponse | 100% |
| **Cas 0 résultat** | Message explicite sans hallucination | 100% |
| **Latence** | Temps de réponse moyen | < 5s |
| **Cohérence** | Réponse cohérente avec les faits | À évaluer |
