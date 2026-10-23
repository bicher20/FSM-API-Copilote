# FSM-API-Copilote

Deux livrables autour du **Scheduler API de Nomadia** (optimisation de tournées / field
service) :

## `/skill/SKILL.md`
Skill Claude (format `SKILL.md`) qui référence tout le modèle de données du Scheduler API
(Job, Resource, Shift, SLA, Requirement, Part, Events, Advanced…), le quick start, les
codes d'erreur et le système de crédits. Objectif : qu'une IA réponde à n'importe quelle
question sur comment modéliser un besoin de planification avec cette API.

À installer comme skill (ex. dans Claude Code : copier dans
`~/.claude/skills/nomadia-scheduler-api/SKILL.md`).

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
