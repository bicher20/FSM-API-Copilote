# Dépannage — Scheduler API Nomadia

Playbook à suivre quand quelque chose ne marche pas. Diagnostique par symptôme, pas par
intuition : le but est de confirmer la cause avant de changer du code.

## 1. Erreurs HTTP

| Code | Cause réelle la plus fréquente | Action |
|---|---|---|
| 400 | un champ requis manque, un `id` référencé n'existe pas (ex. `location_id` d'un job qui ne correspond à aucune `Location` envoyée), format de date/durée invalide | lire le détail renvoyé dans le body — il nomme le champ fautif. Vérifier aussi que tous les `id` croisés (job_type_id, location_id, resource_type_id, job_sla_id…) existent bien dans le payload |
| 401 | clé API absente du header, mauvais header (`x-api-key` exact, pas `Authorization`), clé révoquée | vérifier le header exact, régénérer la clé dans le Portail Nomadia si besoin |
| 402 | solde de crédits négatif | recharger depuis le portail avant de relancer des appels |
| 403 | essai gratuit terminé | informer l'utilisateur qu'un abonnement est requis — ne pas essayer de contourner |

## 2. Un job précis n'est pas planifié

1. Regarder `unallocated_job_reasons` pour ce `job_id` — la raison dit presque tout
   (voir l'énumération complète dans `reference/entities.md`).
2. Raisons les plus fréquentes en pratique et ce qu'elles veulent dire concrètement :
   - `AllPossibleResourcesFull` / `PossibleResourcesHaveMaxJobs` → augmenter
     `maximum_jobs_per_shift`, ajouter une ressource/un shift, ou réduire la durée des
     jobs voisins.
   - `NoAvailableResourcesMaxTravel(InShift)` → la fenêtre SLA du job est trop loin du
     dépôt / des autres jobs de la ressource compte tenu de `maximum_travel_time_*`.
     Vérifier les coordonnées (lat/lng inversées est une erreur classique).
   - `PossibleResourcesInsufficientParts` → le stock embarqué (`available_quantity`)
     est inférieur à la `consumption` cumulée des jobs déjà planifiés sur ce shift.
   - `CostsOutweighJobValue` → le `value_per_hour` du job est trop bas par rapport au
     coût du détour (cost_per_km/heure) — augmenter la valeur ou revoir les coûts.
   - `ResourceNotPermitted(PreReqs)` → un `Requirement` manque côté ressource, ou une
     contrainte `PreRequisiteDefinition` bloque (vérifier `same_resource`,
     `all_or_nothing`).
   - `NoValidTimeWithinSchedulingWindow` → le SLA du job tombe hors de
     `schedule_window_end_date_time`, ou hors de tous les shifts disponibles.
3. Isoler : reproduire avec le payload minimal du quick start (2 jobs, 1 ressource) en
   gardant uniquement les contraintes suspectées, pour confirmer la cause avant de
   toucher au payload réel.

## 3. Rien n'est planifié du tout (0 allocation)

Dans l'ordre, vérifier :
1. Les `id` croisés existent (chaque `job.location_id` a bien une `Location`
   correspondante, chaque `resource.resource_type_id` existe, etc.) — cause n°1 en
   pratique.
2. Les dates sont cohérentes : `shift.start_date_time` < `end_date_time`, le shift
   recouvre bien les fenêtres SLA des jobs, les dates ne sont pas dans le passé par
   rapport à `current_date_time`.
3. `value_per_hour` n'est pas à 0 quelque part (→ `ZeroValue`).
4. Le format des durées/dates est bien ISO 8601 (`PT30M`, pas `30m` ; `2026-11-02T08:00:00`,
   pas de timestamp Unix).

## 4. Le plan n'a "pas de sens" (ressource qui tourne en rond, jobs mal groupés)

- Vérifier `locality` sur les `Location` concernées — sans ça l'API ne sait pas qu'il
  faut regrouper ces jobs.
- Vérifier les multiplicateurs (`travel_time_multiplier`, `work_time_multiplier`) —
  une valeur mal définie à la ressource ou au shift peut fausser l'arbitrage coût/temps.
- Vérifier `shift_penalty` — une valeur trop haute pousse à tout concentrer sur une
  seule ressource/shift même si ce n'est pas souhaité métier.

## 5. Un résultat change entre deux appels identiques

Normal dans une certaine mesure (solveur heuristique) — mais si l'écart est important :
vérifier que `current_date_time` n'a pas changé entre les deux appels, et que rien n'a
été ajouté/retiré au payload (y compris un `id` généré différemment à chaque appel côté
code appelant).

## 6. Checklist pré-vol avant tout appel

Avant d'envoyer un payload (surtout en code, pas juste en test manuel) :
- [ ] Tous les `*_id` référencés existent dans le payload (location_id, job_type_id,
      resource_type_id, job_sla_id/appointment_sla_id, day_pattern_id, requirement_id,
      part_id…)
- [ ] Toutes les dates sont en ISO 8601, cohérentes (`earliest < latest`,
      `start < end`)
- [ ] Toutes les durées sont en ISO 8601 (`PT30M`, `PT1H30M`)
- [ ] Les coordonnées sont `latitude, longitude` dans cet ordre (pas inversées)
- [ ] `value_per_hour` n'est jamais à 0 sauf volontairement
- [ ] Le nombre de ressources × jobs planifiés reste dans le budget crédits prévu
