# FSM-API-Copilote

Deux livrables autour du **Scheduler API de Nomadia** (optimisation de tournées / field
service) :

## `/skill/`
Skill Claude (format `SKILL.md`) qui transforme Claude en copilote d'intégration pour le
Scheduler API : il cadre le besoin, inspecte le projet existant (clé API déjà en `.env`,
appels déjà en place, stack utilisé) avant de poser une seule question, puis écrit
directement le code/payload — et diagnostique une erreur ou un job non planifié plutôt
que de renvoyer un extrait de doc.

- `SKILL.md` — procédure à suivre + résumé de navigation du modèle de données
- `ONBOARDING.md` — démarrage rapide pour un client qui reçoit le skill (installation,
  clé API, premier test, premier vrai appel, dépannage réseau/DNS)
- `llms.txt` — index priorisé des fichiers pour un agent IA qui découvre le skill
- `reference/entities.md` — transcription exhaustive de toutes les entités (champs,
  types, valeurs par défaut) + l'énumération complète des raisons de non-allocation
- `reference/kpis-metier.md` — traduction des paramètres techniques en arguments business
- `reference/replanification-temps-reel.md` — patterns de replanification continue/temps réel
- `troubleshooting.md` — playbook de dépannage par symptôme (erreurs HTTP, job non
  planifié, plan incohérent)
- `scripts/doctor.py` — point d'entrée unique : valide puis recommande en une commande
- `scripts/validate_payload.py` / `recommend_improvements.py` — les deux étapes de
  `doctor.py`, utilisables séparément (ex: intégration CI)
- `scripts/compare_scenarios.py` — comparateur avant/après entre configs
- `snippets/client.js` et `snippets/client.py` — client HTTP minimal + retry/backoff
- `examples/` — 5 payloads déjà vérifiés, un par pattern courant
- `CHANGELOG.md` — historique des versions du skill

À installer comme skill (ex. dans Claude Code : copier le dossier `skill/` dans
`~/.claude/skills/nomadia-scheduler-api/`). Agent-agnostique : fonctionne avec tout
agent IA ayant accès à des fichiers + un shell, pas seulement Claude.

> **Non livré aux clients** : `reference/battlecard-timefold.md` est un argumentaire
> commercial interne (positionnement Nomadia vs Timefold/OptaPlanner). Utile pour
> préparer un rendez-vous, mais à retirer du dossier avant de donner le skill à un
> client — ce n'est pas un livrable d'intégration.

### Distribuer ce skill à un client

Ce skill est conçu pour être donné tel quel à différents clients qui intègrent le
Scheduler API de Nomadia chacun de leur côté. Points à respecter à chaque remise :

1. **Une clé API par client, jamais partagée.** Le skill ne contient et ne doit
   jamais contenir de clé API en dur (voir `CONTRIBUTING.md` §2) — chaque client
   fournit la sienne au moment de l'intégration, dans son propre `.env`.
2. **Retirer `reference/battlecard-timefold.md`** avant l'envoi (voir ci-dessus) —
   c'est pour toi, pas pour le client.
3. **Donner la version précise** (voir `version:` dans `SKILL.md` + l'entrée
   correspondante dans `CHANGELOG.md`) — utile si le client te signale un comportement
   et que tu dois savoir ce qu'il a réellement entre les mains.
4. **Le client utilise son propre agent IA** (Claude Code, Cursor, Copilot agent...) —
   rien dans ce skill ne suppose que c'est toi qui l'exécutes pour lui.

Les points 1-3 sont automatisés par :

```bash
python3 scripts/package_for_client.py --client "Nom du client"
```

Ça produit `dist/<client>-v<version>/` et `dist/<client>-v<version>.zip` — une copie de
`skill/` sans `reference/battlecard-timefold.md` ni les caches Python, nommée avec la
version exacte envoyée. Le dossier `dist/` n'est jamais commité (voir `.gitignore`) —
c'est un livrable, pas du code du repo.

## `/app/index.html`
Un copilote de découverte commerciale, en **chat** (une seule page HTML, aucune
dépendance, aucun backend) : il pose les bonnes questions à poser à un prospect
field service / tournées, dans l'ordre, organisées par thème (contexte, jobs,
ressources, contraintes, règles avancées, temps réel) — chaque question est reliée au
champ exact du modèle Nomadia qu'elle vient qualifier. En fin de parcours : un brief
généré automatiquement, copiable.

C'est un enchaînement de questions scripté (pas un vrai moteur conversationnel IA) : ça
ne fait aucun appel réseau, aucune clé API requise, gratuit et déployable n'importe où.
Les réponses sont sauvegardées localement dans le navigateur (`localStorage`).

Pour une vraie compréhension en langage libre (relances dynamiques façon
prd.timefold.ai), il faudrait brancher un LLM derrière (clé API Anthropic + petit
backend) — pas fait ici pour rester 100% gratuit et sans dépendance.

### Déploiement
Fichier statique : déployable tel quel sur Vercel, GitHub Pages, Hatchable, ou n'importe
quel hébergeur statique — aucune build requise.
