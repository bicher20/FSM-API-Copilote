# Replanification temps réel et "pinning" — l'équivalent Nomadia des fonctions avancées des solveurs scientifiques

Les solveurs généralistes documentent souvent des fonctionnalités dédiées pour la
planification continue/temps réel ("continuous
planning", "real-time planning", "non-disruptive replanning") et pour figer une
affectation déjà engagée pendant que le solveur réoptimise le reste ("pinned planning
variables"). Le Scheduler API de Nomadia n'a pas de nom marketing pour ça, mais les
mêmes besoins se couvrent avec les mécanismes déjà présents dans le schéma — il faut
juste savoir les assembler. Ce fichier documente l'assemblage, pour ne jamais laisser
croire que Nomadia serait "moins capable" par manque de documentation plutôt que par
manque de fonctionnalité.

## 1. Figer une affectation déjà engagée ("pinning")

**Besoin** : un technicien est déjà en route vers un job — il ne faut pas que le
prochain appel de replanification le réaffecte ailleurs.

**Mécanisme Nomadia** :
- `JobResource.fixed_resource_id` — force la ressource pour ce job, outrepasse les
  contraintes dures (équivalent direct d'un "pinned planning variable").
- `JobResource.commit_date_time_stamp` — marque le job comme "committé" : à faire au
  plus tôt sur la ressource fixée. Si plusieurs jobs sont committés sur la même
  ressource, ils sont triés par cette valeur — donc l'ordre d'engagement réel est
  respecté, pas juste l'affectation.

**Pattern recommandé** : dès qu'un `JobResourceStatus` reçu indique qu'un job est
`travel_start_date_time` ou `start_date_time` renseigné (la ressource est partie ou a
commencé), basculer ce job en `fixed_resource_id` + `commit_date_time_stamp` avant le
prochain appel — sinon le solveur peut légitimement le réaffecter ailleurs lors de la
replanification suivante.

## 2. Replanification incrémentale (ne pas tout réenvoyer à chaque fois)

**Besoin** : éviter de reconstruire et renvoyer l'intégralité du payload à chaque
petite mise à jour (nouveau job, annulation, changement de dispo) — coûteux en temps
d'intégration et en crédits si ça pousse à sur-planifier.

**Mécanisme Nomadia** :
- `DeletedEntity` (Input) — signale qu'une entité (`entity_type` + `entity_id1/2/3`) a
  été supprimée, sans avoir à reconstruire tout le payload autour.
- `OutputInformation.output_type` (`COMPLETE` vs `UPDATE`) + `last_change_id` /
  `last_input_change_id` — permet de savoir si la réponse est un plan complet ou une
  mise à jour incrémentale, et de chaîner les appels suivants sur le bon état.

**Pattern recommandé** : maintenir côté application un état "dernier payload envoyé" +
le `last_change_id` reçu. À chaque événement métier (nouveau job, annulation,
changement de shift), n'envoyer que le delta (entités ajoutées/modifiées +
`DeletedEntity` pour les supprimées) plutôt que l'intégralité du planning.

## 3. Suivi temps réel pendant l'exécution

**Besoin** : réagir si une ressource prend du retard, change de position, ou ne peut
plus respecter le plan initial.

**Mécanisme Nomadia** :
- `ResourceKnownLocation` — position GPS connue d'une ressource à un instant T
  (`resource_id`, `date_time_stamp`, `latitude`, `longitude`) — à envoyer en entrée pour
  que la replanification suivante reparte de la position réelle, pas de la position
  théorique du plan initial.
- `JobResourceStatus` — avancement réel d'un job (`travel_start_date_time` /
  `expected_arrival_date_time` / `start_date_time` / `end_date_time`) — permet de
  détecter un retard avant qu'il ne se propage sur toute la tournée.

**Pattern recommandé** : à chaque replanification, injecter la dernière
`ResourceKnownLocation` connue pour chaque ressource active, pas uniquement sa position
de dépôt théorique — sinon l'optimisation suivante part d'une hypothèse déjà fausse.

## 4. Ce que Nomadia ne fait PAS nativement (à dire honnêtement à un prospect)

- Pas d'explication détaillée du score par contrainte (pas d'équivalent de "score
  analysis"/indictments) — `unallocated_job_reasons` est un enum plat, pas une
  décomposition pondérée. C'est pour ça que `scripts/recommend_improvements.py` et
  `troubleshooting.md` §2 existent dans ce skill : reconstruire manuellement une partie
  de ce diagnostic à partir des données disponibles (payload + réponse), faute de
  l'avoir nativement.
- Pas de mode "daemon"/solveur qui tourne en continu en tâche de fond — chaque appel
  est synchrone et autonome. La "continuité" se construit côté application avec les
  patterns ci-dessus, pas côté API.
- Pas de benchmarking intégré — `scripts/compare_scenarios.py` dans ce skill comble ce
  manque en comparant plusieurs variantes de configuration (statiquement, ou via de
  vrais appels API) pour prouver un gain plutôt que l'affirmer.

Ne jamais présenter ces limites comme des "manques" sans donner le pattern qui les
compense — c'est tout l'intérêt de ce fichier.
