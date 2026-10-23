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
- `reference/entities.md` — transcription exhaustive de toutes les entités (champs,
  types, valeurs par défaut) + l'énumération complète des raisons de non-allocation
- `troubleshooting.md` — playbook de dépannage par symptôme (erreurs HTTP, job non
  planifié, plan incohérent)
- `snippets/client.js` et `snippets/client.py` — client HTTP minimal + validation locale
  du payload avant envoi (évite de consommer des crédits sur une requête mal formée)

À installer comme skill (ex. dans Claude Code : copier le dossier `skill/` dans
`~/.claude/skills/nomadia-scheduler-api/`).

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
