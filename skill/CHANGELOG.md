# Changelog du skill

## 1.6 — 2026-10-23
- Ajout `reference/battlecard-timefold.md` : argumentaire commercial factuel vs
  Timefold (barrière technique Java/Kotlin-only de leur Solver open source, pricing
  100% "contact sales" de leur offre Platform, géocodage inclus chez Nomadia) +
  reconnaissance honnête de ce que Timefold fait mieux (échelle 500k jobs,
  explicabilité native payante, what-if avancé) + réponses aux objections courantes.
  Sourcé sur docs.timefold.ai et timefold.ai/pricing au 23/10/2026.

## 1.5 — 2026-10-23
- Ajout `scripts/compare_scenarios.py` : comparateur de scénarios, zéro dépendance.
  Mode statique (diff de config, gratuit) ou mode réel (`--api-key`, vrai avant/après
  chiffré sur taux d'allocation/distance/crédits — consomme de vrais crédits, à
  n'utiliser qu'avec l'accord explicite de l'utilisateur). Réponse directe au fait que
  les solveurs scientifiques (Timefold, OptaPlanner) vendent souvent le benchmarking
  comme fonctionnalité Enterprise.
- Ajout `reference/replanification-temps-reel.md` : documente les patterns Nomadia
  équivalents aux fonctionnalités "continuous/real-time planning" et "pinned planning
  variables" des solveurs généralistes (fixed_resource_id + commit_date_time_stamp,
  DeletedEntity + output_type, ResourceKnownLocation + JobResourceStatus), et nomme
  honnêtement ce que Nomadia ne fait pas nativement (explication de score détaillée,
  mode daemon, benchmarking natif) avec le pattern qui compense chaque manque.

## 1.4 — 2026-10-23
- Ajout `scripts/recommend_improvements.py` : moteur de recommandations proactives,
  orienté ROI, exécutable en CLI. Analyse un payload (config seule) et optionnellement
  une vraie réponse API (`--response`) pour sortir des recommandations priorisées
  (HIGH/MEDIUM/LOW), chacune reliée à `reference/kpis-metier.md`. Testé sur les 5
  exemples et sur une réponse API simulée.
- `SKILL.md` §0 : nouvelle étape 2bis — table "objectif client → mécanismes Nomadia à
  activer → pourquoi (ROI)" pour cadrer la configuration dès que le besoin métier est
  connu, sans laisser l'utilisateur deviner quel champ cocher.
- `SKILL.md` §0 étape 3 : le copilote lance désormais systématiquement
  `recommend_improvements.py` après avoir posé un payload, et de nouveau après un vrai
  appel API — il doit présenter les recommandations `[HIGH]` sans attendre qu'on les
  lui demande.
- Préparation explicite à un test API réel (clé fournie précédemment par
  l'utilisateur) : rappel que la clé ne doit jamais être écrite en dur dans un fichier
  commité, uniquement utilisée en mémoire au moment du test.

## 1.3 — 2026-10-23
- Ajout `reference/kpis-metier.md` : traduction des paramètres/résultats techniques en
  arguments business (taux d'allocation, ratio trajet/temps utile, respect SLA,
  équilibrage de charge, coût en crédits vs planification manuelle, stabilité du plan).
- Ajout `scripts/test_validate_payload.py` : suite de tests automatisés sur le
  validateur (régression du bug lat/lng corrigé en 1.2, détection de chaque type
  d'erreur, les 5 exemples doivent tous passer).
- `SKILL.md` explicitement rendu agent-agnostique : note en tête de fichier précisant
  que la procédure ne dépend d'aucun agent IA précis (Claude Code, Cursor, Copilot
  agent, etc.), et reformulation des références à "Bash" en "ton outil d'exécution de
  commandes". Reste volontairement scopé à Nomadia uniquement (pas de couche
  multi-fournisseur).

## 1.2 — 2026-10-23
- Ajout `scripts/validate_payload.py` : validateur exécutable (plus un simple snippet à
  copier), testé contre un payload volontairement cassé.
- Ajout `examples/` : 5 payloads vérifiés (minimal, compétence requise, stock de pièces,
  ordre entre jobs, disponibilité récurrente), tous passés au validateur.
- Ajout boucle d'auto-correction dans `SKILL.md` §0 étape 3 (construire → valider →
  corriger → appeler → diagnostiquer une erreur API → corriger → réessayer une fois).
- `snippets/client.js` et `client.py` : ajout retry avec backoff sur les erreurs réseau
  et 5xx uniquement (jamais sur 400/401/402/403, qui ne se corrigent pas en réessayant).
- Ajout de ce CHANGELOG.

## 1.1 — 2026-10-23
- Ajout `reference/entities.md` (transcription exhaustive du schéma + énumération
  complète des raisons de non-allocation).
- Ajout `troubleshooting.md` (playbook de dépannage par symptôme).
- Ajout `snippets/client.js` et `client.py` (client HTTP + validation locale basique).

## 1.0 — 2026-10-23
- Première version : `SKILL.md` avec résumé du schéma complet, quick start, crédits et
  codes d'erreur, procédure de cadrage (§0).
