# Dépannage — Scheduler API Nomadia

Playbook à suivre quand quelque chose ne marche pas. Diagnostique par symptôme, pas par
intuition : le but est de confirmer la cause avant de changer du code.

## 1. Erreurs HTTP

| Code | Cause réelle la plus fréquente | Action |
|---|---|---|
| 400 | un champ requis manque, un `id` référencé n'existe pas (ex. `location_id` d'un job qui ne correspond à aucune `Location` envoyée), format de date/durée invalide | lire le détail renvoyé dans le body — il nomme le champ fautif. Vérifier aussi que tous les `id` croisés (`job_type_id`, `location_id`, `resource_type_id`, `fixed_resource_id`…) existent bien dans le payload. ⚠️ Un champ au contraire *inconnu* n'est pas forcément détecté en 400 : voir l'avertissement sur la permissivité du désérialiseur dans `reference/entities.md` |
| 401 | clé API absente du header, mauvais header (`x-api-key` exact, pas `Authorization`), clé révoquée | vérifier le header exact, régénérer la clé dans le Portail Nomadia si besoin |
| 402 | solde de crédits négatif | recharger depuis le portail avant de relancer des appels |
| 403 | essai gratuit terminé | informer l'utilisateur qu'un abonnement est requis — ne pas essayer de contourner |

## 2. Un job précis n'est pas planifié

1. Regarder `unallocated_job_reasons` pour ce `job_id` — la raison dit presque tout.
   ⚠️ L'énumération complète des valeurs possibles (`AllPossibleResourcesFull`,
   `CostsOutweighJobValue`, etc.) vient de la doc de l'**offre complète** — elle n'est
   pas documentée sur les pages self-service et n'est donc pas garantie exhaustive
   côté self-service (voir reference/entities.md §Sortie). Les raisons ci-dessous
   restent les plus plausibles en pratique :
   - `AllPossibleResourcesFull` / `PossibleResourcesHaveMaxJobs` → augmenter
     `maximum_jobs_per_shift`, ajouter une ressource/un shift, ou réduire la durée des
     jobs voisins.
   - `NoAvailableResourcesMaxTravel(InShift)` → la fenêtre SLA du job est trop loin du
     dépôt / des autres jobs de la ressource compte tenu de `maximum_travel_time_*`.
     Vérifier les coordonnées (lat/lng inversées est une erreur classique).
   - `CostsOutweighJobValue` → le `value_per_hour` du job est trop bas par rapport au
     coût du détour (`cost_per_kilometre`/`cost_per_hour`) — augmenter la valeur ou
     revoir les coûts.
   - Un `requirements` manquant côté ressource (aucune ressource disponible ne couvre
     les `requirements` du job) est aussi une cause fréquente — vérifier §8 de
     `SKILL.md`.
   - Les raisons liées à `PossibleResourcesInsufficientParts`,
     `ResourceNotPermittedPreReqs`, `PreRequisiteJobNotAllocated` ou
     `NoValidTimeWithinSchedulingWindow` (horizon borné) concernent des mécanismes de
     l'offre complète (stock, ordre entre jobs, horizon borné) — si tu les vois
     apparaître en self-service, c'est suspect : voir
     `reference/offre-complete-nomadia.md`, ces mécanismes n'ont normalement aucun
     effet en self-service.
2. Isoler : reproduire avec le payload minimal du quick start (2 jobs, 1 ressource) en
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
- Vérifier `cost_per_kilometre`/`cost_per_hour` sur le `resource_type` — des valeurs
  mal définies faussent l'arbitrage coût/temps du solveur.
- Vérifier `shift_penalty` — une valeur trop haute pousse à tout concentrer sur une
  seule ressource/shift même si ce n'est pas souhaité métier.

## 4bis. Un job multi-ressources (`job_resources`, `resource_index`) n'est planifié qu'avec une seule ressource

**Statut au 27/10/2026 : cause définitivement confirmée — ce n'est pas un bug, pas
une limitation de l'environnement de test, et pas un nom de champ incorrect.**

**Cause réelle : l'API self-service n'a tout simplement aucun mécanisme de job
multi-ressources.** Confirmé en comparant le schéma OpenAPI réel qui alimente
`https://scheduler-json-api.readme.io` (récupéré directement, pas la doc rendue —
voir `vendor-docs/openapi-schedule.json`) avec le schéma du PDF interne "Scheduler
Schema Documentation" : ce dernier décrit l'**offre complète** Nomadia (avec équipe
projet), le premier l'**offre self-service** (ce que la clé API de test donne
réellement). `job_resources`/`JobResource`/`resource_index` n'existent que côté
offre complète — voir `reference/entities.md` (section "Mécanismes absents") et
`reference/offre-complete-nomadia.md` §1.

Testé en conditions réelles sur l'ancienne version de `examples/10_job_multi_ressources.json`
(payload avec deux entrées `job_resources` pour le même job, `resource_index: 1` puis
`2`, deux ressources disponibles aux mêmes horaires), ~14 crédits dépensés sur
plusieurs appels :
- Deux appels identiques (même payload) ont chacun alloué **une seule** ressource au
  job (RES-1 au premier appel, RES-2 au second) — pas les deux simultanément.
- `unallocated_job_reasons` était vide dans les deux cas (pas d'échec signalé).
- Résultat identique à ce qu'on obtiendrait si `job_resources` n'était jamais envoyé :
  l'API l'a silencieusement ignoré (HTTP 200 trompeur, cohérent avec un désérialiseur
  runtime permissif malgré `additionalProperties: false` déclaré dans la spec — voir
  reference/entities.md) et a traité le job comme un job normal à 1 ressource.

**Si un client a ce besoin** : ne jamais essayer de l'encoder dans le self-service
(toujours silencieusement ignoré). Montrer l'exemple de `reference/offre-complete-nomadia.md`
§1 et orienter vers un contact Nomadia — voir §-1 de `SKILL.md`. `examples/10_job_multi_ressources.json`
a été réduit à un payload minimal illustrant uniquement la forme offre-complète, avec
un avertissement explicite, plutôt que de laisser croire qu'il s'agit d'un exemple
self-service testable.

## 5. Un résultat change entre deux appels identiques

Normal dans une certaine mesure (solveur heuristique) — mais si l'écart est important,
vérifier que rien n'a été ajouté/retiré au payload (y compris un `id` généré
différemment à chaque appel côté code appelant).

## 6. Checklist pré-vol avant tout appel

Avant d'envoyer un payload (surtout en code, pas juste en test manuel) — ou plus
simplement, lancer `scripts/doctor.py` qui vérifie tout ceci automatiquement :
- [ ] Tous les `*_id` référencés existent dans le payload (`location_id`,
      `job_type_id`, `resource_type_id`, `fixed_resource_id`…)
- [ ] Toutes les dates sont en ISO 8601, cohérentes (`earliest < latest`,
      `start < end`)
- [ ] Toutes les durées sont en ISO 8601 (`PT30M`, `PT1H30M`)
- [ ] Les coordonnées sont `latitude, longitude` dans cet ordre (pas inversées)
- [ ] `value_per_hour` n'est jamais à 0 sauf volontairement
- [ ] `requirements` est une liste de chaînes simples, jamais une liste d'objets
      (schéma self-service réel — voir `reference/entities.md`)
- [ ] Aucun champ de l'offre complète (`job_resources`, `parts`,
      `pre_requisite_definitions`, `schedule_definition`, `*_pattern`) n'a été envoyé
      en pensant qu'il serait pris en compte — il serait silencieusement ignoré
- [ ] Le nombre de ressources × jobs planifiés reste dans le budget crédits prévu
