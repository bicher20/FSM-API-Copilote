# Référence exhaustive des entités — Scheduler API Nomadia

Transcription complète du schéma (toutes les entités, tous les champs, types exacts,
M/O, valeurs par défaut). À consulter **avant d'écrire un payload ou du code** — ne
jamais inventer un nom de champ : s'il n'est pas ici, il n'existe pas dans l'API.

Légende : `M` = obligatoire, `O` = optionnel, `M(x)` = obligatoire avec valeur par
défaut `x` si omis.

---

## Général

### Location (Input)
| Champ | Type | M/O | Défaut/Notes |
|---|---|---|---|
| id | String(32) | M | clé primaire |
| latitude | Double | M | |
| longitude | Double | M | |
| locality | String(32) | O | regroupe des lieux : l'API tente de faire tous les jobs d'une même locality d'un coup |
| additional_travel_time | TimeSpan | O | durée ajoutée à tout trajet vers ce lieu |

### ScheduleDefinition (Input)
| Champ | Type | M/O | Notes |
|---|---|---|---|
| id | String(32) | M | |
| schedule_window_end_date_time | DateTime | O | sans valeur : l'API considère tous les shifts/SLA |
| current_date_time | DateTime | O | pour traiter des données hors temps réel |

### DeletedEntity (Input/Output)
| Champ | Type | M/O |
|---|---|---|
| entity_type | String(32) | M |
| entity_id1 | String(32) | M |
| entity_id2 | String(32) | O |
| entity_id3 | String(32) | O |

---

## Module Job

### JobType (Input)
| Champ | Type | M/O | Défaut |
|---|---|---|---|
| id | String(32) | M | |
| custom_duration | TimeSpan | M | PT1H |
| duration_in_half_days | Integer | O | utilisé seulement si custom_duration absent |
| value_per_hour | Double | M | 10000 |
| split_allowed | Boolean | O | |

### SLA (Input)
| Champ | Type | M/O | Défaut |
|---|---|---|---|
| id | String(32) | M | |
| earliest_start_date_time | DateTime | M | |
| latest_start_date_time | DateTime | M | |
| penalty_per_hour | Double | M | 0 |
| base_jeopardy_penalty | Double | M | 0 |
| penalty_per_hour_jeopardy | Double | M | * (valeur élevée par défaut) |

### Job (Input)
| Champ | Type | M/O | Notes |
|---|---|---|---|
| id | String(32) | M | |
| job_sla_id | String(32) | M | ignoré si appointment_sla_id fourni — FK SLA |
| appointment_sla_id | String(32) | O | FK SLA |
| job_type_id | String(32) | M(DEFAULT) | FK JobType |
| location_id | String(32) | M | FK Location |
| custom_duration | TimeSpan | O | sinon hérité du job_type |
| duration_in_half_days | Integer | O | utilisé seulement si custom_duration absent ; sinon hérité |
| value_per_hour | Double | O | sinon hérité du job_type |
| split_allowed | Boolean | O | sinon hérité du job_type |
| fixed_date_time | DateTime | O | démarrage imposé |
| appointment_priority | Integer | M(999) | plus bas = prioritaire pour les créneaux de rendez-vous |

### JobResource (Input)
| Champ | Type | M/O | Notes |
|---|---|---|---|
| job_id | String(32) | M | FK Job — clé composite avec resource_index |
| resource_index | Integer | M(1) | permet un job multi-ressources (plusieurs lignes) |
| fixed_resource_id | String(32) | O | FK Resource — outrepasse toute contrainte dure |
| commit_date_time_stamp | DateTime | O | nécessite fixed_resource_id ; trie les jobs committés entre eux |

### JobAvailability (Input)
| Champ | Type | M/O |
|---|---|---|
| id | String(32) | M |
| job_id | String(32) | M |
| start_date_time | DateTime | M |
| end_date_time | DateTime | M |

### JobUnavailability (Input)
Mêmes champs que JobAvailability. **En cas de chevauchement, JobUnavailability gagne.**

### JobAvailabilityPattern (Input)
| Champ | Type | M/O |
|---|---|---|
| id | String(32) | M |
| job_id | String(32) | M |
| start_time | TimeOnly | M |
| end_time | TimeOnly | M |
| day_pattern_id | String(32) | M | FK DayPattern |
| pattern_start_date | DateOnly | M |
| pattern_end_date | DateOnly | M |
| time_zone_id | String(64) | M | IANA (ex. "Europe/Paris") ou nom Windows |

### DayPattern (Input)
| Champ | Type | M/O |
|---|---|---|
| id | String(32) | M |
| day_based_cron_expression | String(256) | M |

Patterns prédéfinis (ids tout faits, pas besoin de les envoyer) :
`EVERY_DAY`, `MONDAY_TO_THURSDAY`, `MONDAY_TO_FRIDAY`, `MONDAY_TO_SATURDAY`.

Format `day_based_cron_expression` : `<Day-of-Month> <Month> <Day-of-Week>`
- Day-of-Month : `1-31`, caractères spéciaux `, - * ? / L W`
- Month : `1-12` ou `JAN-DEC`, caractères spéciaux `, - * /`
- Day-of-Week : `1-7` ou `SUN-SAT`, caractères spéciaux `, - * ? / L #`

| Caractère | Sens |
|---|---|
| `*` | toute valeur |
| `?` | valeur arbitraire (ignore le champ) |
| `-` | plage (ex. `10-12`) |
| `,` | liste de valeurs |
| `/` | incrément (ex. `3/5` = 3,8,13,18,23,28) |
| `L` | dernier jour du mois (Day-of-Month), ou dernier jour de semaine du mois si précédé d'un chiffre (Day-of-Week, ex. `6L` = dernier vendredi) |
| `W` | jour ouvré le plus proche (Day-of-Month uniquement) |
| `#` | n-ième occurrence d'un jour de semaine (ex. `6#3` = 3e vendredi) |

Exemples : `* * ?` = tous les jours · `? 6 TUE` = tous les mardis de juin ·
`? * MON-FRI` = tous les jours ouvrés · `15 * ?` = le 15 de chaque mois ·
`L-3 * ?` = avant-avant-dernier jour du mois.

---

## Module Resource

### ResourceType (Input)
| Champ | Type | M/O | Défaut |
|---|---|---|---|
| id | String(32) | M | |
| start_location_id | String(32) | M | FK Location |
| end_location_id | String(32) | M | FK Location |
| cost_per_kilometre | Double | M | 1 |
| cost_per_hour | Double | M | 1 |
| maximum_travel_time_from_start_location | TimeSpan | O | |
| maximum_individual_travel_time | TimeSpan | O | entre 2 lieux consécutifs de la route |
| maximum_travel_time_per_shift | TimeSpan | O | trajet total cumulé sur le shift |
| travel_time_multiplier | Double | M | 1 |
| work_time_multiplier | Double | M | 1 |
| minimum_jobs_per_shift | Integer | O | |
| maximum_jobs_per_shift | Integer | O | |
| pre_shift_travel_period | TimeSpan | M | PT0S |
| post_shift_travel_period | TimeSpan | M | PT0S |
| overtime_period | TimeSpan | M | PT0S |
| overtime_cost_multiplier | Double | M | 5 |
| shift_penalty | Double | M | 0 — coût fixe dès qu'un shift a ≥1 job |

### Resource (Input)
Mêmes champs que ResourceType (tous optionnels ici, héritent du ResourceType si omis),
plus :
| Champ | Type | M/O | Défaut |
|---|---|---|---|
| id | String(32) | M | |
| resource_type_id | String(32) | M(DEFAULT) | FK ResourceType |

### Shift (Input)
Mêmes champs optionnels que Resource (héritent de la Resource si omis), plus :
| Champ | Type | M/O |
|---|---|---|
| id | String(32) | M |
| resource_id | String(32) | M |
| start_date_time | DateTime | M |
| end_date_time | DateTime | M |

### Break (Input)
| Champ | Type | M/O | Défaut |
|---|---|---|---|
| id | String(32) | M | |
| shift_id | String(32) | M | FK Shift |
| earliest_start_date_time | DateTime | M | |
| latest_start_date_time | DateTime | M | |
| duration | TimeSpan | M | PT1H |
| fixed_date_time | DateTime | O | |

### ResourceUnavailability (Input)
| Champ | Type | M/O |
|---|---|---|
| id | String(32) | M |
| resource_id | String(32) | M |
| start_date_time | DateTime | M |
| end_date_time | DateTime | M |
| location_id | String(32) | O |

---

## Module Output

### JobResourceAllocation (Output)
| Champ | Type | M/O |
|---|---|---|
| job_id | String(32) | M |
| resource_index | Integer | M |
| resource_id | String(32) | M |

### JobDateTimeAllocation (Output)
| Champ | Type | M/O |
|---|---|---|
| job_id | String(32) | M |
| resource_index | Integer | M |
| visit_id | Integer | M | plusieurs lignes si job découpé |
| start_date_time | DateTime | M |
| end_date_time | DateTime | M |

### BreakAllocation (Output)
| Champ | Type | M/O |
|---|---|---|
| break_id | String(32) | M |
| resource_id | String(32) | M |
| start_date_time | DateTime | M |
| end_date_time | DateTime | M |

### Travel (Output)
| Champ | Type | M/O |
|---|---|---|
| resource_id | String(32) | M |
| start_date_time | DateTime | M |
| end_date_time | DateTime | M |
| distance_in_metres | Double | M |
| start_location_id | String(32) | O |
| end_location_id | String(32) | O |

### UnallocatedJobReason (Output)
| Champ | Type | M/O |
|---|---|---|
| job_id | String(32) | M |
| unallocated_reason | String | M | voir énumération ci-dessous |

### OutputInformation (Output)
| Champ | Type | M/O |
|---|---|---|
| last_change_id | Long | O |
| output_type | String(32) | O | "COMPLETE" ou "UPDATE" |
| last_input_change_id | Long | O |

---

## Module Constraints

### Requirement (Input)
| Champ | Type | M/O |
|---|---|---|
| id | String(32) | M |

### JobTypeRequirement / JobRequirement / JobResourceRequirement / ResourceTypeRequirement / ResourceRequirement / ShiftRequirement (Input)
Toutes sur le même schéma : FK vers l'entité concernée + `requirement_id` (M, FK
Requirement). `JobResourceRequirement` a en plus `resource_index` (Integer, M(1)).

### Part (Input)
| Champ | Type | M/O |
|---|---|---|
| id | String(32) | M |

### JobTypePart / JobPart / JobResourcePart (Input)
FK vers l'entité + `part_id` (M, FK Part) + `consumption` (Integer, M). `JobResourcePart`
ajoute `resource_index` (Integer, M(1)).

### ResourceTypePart / ResourcePart / ShiftPart (Input)
FK vers l'entité + `part_id` (M, FK Part) + `available_quantity` (Integer, M).

---

## Module Events

### JobResourceStatus (Input)
| Champ | Type | M/O |
|---|---|---|
| job_id | String(32) | M |
| resource_index | Integer | M(1) |
| visit_id | Integer | M |
| travel_start_date_time | DateTime | O |
| expected_arrival_date_time | DateTime | O |
| start_date_time | DateTime | O |
| end_date_time | DateTime | O |

### ResourceKnownLocation (Input)
| Champ | Type | M/O |
|---|---|---|
| resource_id | String(32) | M |
| date_time_stamp | DateTime | M |
| latitude | Double | M |
| longitude | Double | M |

---

## Module Advanced

### PreRequisiteDefinition (Input)
| Champ | Type | M/O | Défaut |
|---|---|---|---|
| earlier_job_id | String(32) | M | |
| later_job_id | String(32) | M | |
| minimum_time_difference | TimeSpan | O | |
| maximum_time_difference | TimeSpan | O | |
| same_resource | Boolean | M | false |
| all_or_nothing | Boolean | M | false |

### JobResourcePriority (Input) — *WIP*
| Champ | Type | M/O |
|---|---|---|
| job_id | String(32) | M |
| resource_index | Integer | M(1) |
| resource_id | String(32) | M |
| priority | String(32) | M | `MANDATORY` \| `FAVOURED` \| `UNFAVOURED` \| `FORBIDDEN` |

### AllowedSplitPoint (Input) — *WIP*
| Champ | Type | M/O |
|---|---|---|
| job_id | String(32) | M |
| index | Integer | M(1) |
| duration | TimeSpan | M |

⚠️ Les entités marquées *WIP* dans la doc source peuvent ne pas être pleinement
supportées par le moteur — à valider par un appel réel avant de s'appuyer dessus en
prod.

---

## Énumération complète — `unallocated_reason`

| Valeur | Signification |
|---|---|
| NotCalculated | raison non calculée (contrainte de temps de calcul) |
| Unknown | raison indéterminée |
| ZeroValue | valeur du job = 0, impossible à planifier |
| NoValidTimeWithinSchedulingWindow | pas de fenêtre de temps valide dans la fenêtre de planification |
| NoPossibleResources | job fixé (fixed_resource_id) sur une ressource non permise |
| AllPossibleResourcesFull | aucune ressource n'a de temps libre |
| NoAvailableResourcesMaxTravel | toutes les ressources dépasseraient leur trajet max |
| AvailableResourcesLittleTime | ressources dispo mais pas le temps d'y aller |
| PossibleResourcesDistant | ressources dispo mais toutes trop loin |
| PossibleResourcesInsufficientParts | pas assez de pièces/stock embarqué |
| PossibleResourcesHaveMaxJobs | ressources déjà au max de jobs/shift |
| LowValue | valeur trop basse pour justifier le détour |
| JobInvalid | données du job invalides, non chargées |
| MultiResourceJob | job multi-ressources difficile à caser |
| InvalidFixedJobsInPossibleRoute | d'autres jobs fixés invalides perturbent la route |
| CostsOutweighJobValue | coût de réalisation > valeur du job |
| NoAvailableResourcesMaxTravelInShift | dépasserait le trajet max du shift |
| PossibleResourcesNoShiftAtTime | aucune ressource n'a de shift sur ce créneau |
| ResourceNotPermitted | ressource individuelle non autorisée |
| ResourceNotPermittedPreReqs | non autorisée à cause d'une contrainte de pré-requis |
| PreRequisiteJobNotAllocated | un job pré-requis n'a pas été planifié |
| DependantJobNotAllocated | un job dépendant n'a pas été planifié |
