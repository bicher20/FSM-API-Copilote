# Signaler un problème ou une suggestion

Ce skill est distribué à plusieurs clients, chacun potentiellement sur une version
différente (voir `skill/CHANGELOG.md`). Pour qu'un retour soit traitable, préciser
systématiquement :

1. **La version du skill** — ligne `version:` dans `skill/SKILL.md`, ou nom du
   package reçu (ex: `acme-v1.7.zip`, voir `scripts/package_for_client.py`).
2. **Ce qui a été demandé à l'agent IA** (le message exact, pas un résumé) et quel
   agent (Claude Code, Cursor, Copilot agent...) — le comportement peut varier d'un
   agent à l'autre même avec les mêmes instructions.
3. **Le payload minimal qui reproduit le problème** — si possible en partant d'un
   fichier de `skill/examples/` modifié, plutôt qu'un payload de production complet
   (plus simple à diagnostiquer, et évite d'envoyer des données client réelles pour
   rien).
4. **La sortie obtenue** de `scripts/doctor.py` sur ce payload, et ce qui était attendu
   à la place.

## Canal

Pour l'instant : contact direct avec Marouane Bicher (Flowify / MPWB) — pas de file
d'issues publique tant que le repo reste privé. Si ce skill devient public, cette
section sera mise à jour avec un lien vers les issues GitHub du repo.

## Ce qui n'est pas un bug

- Un `[WARN]` de `validate_payload.py` ou une recommandation de
  `recommend_improvements.py` n'est jamais une erreur du skill — c'est une suggestion à
  évaluer, pas une alerte à faire disparaître à tout prix.
- Un comportement différent selon l'agent IA utilisé (Claude Code vs Cursor vs autre)
  n'est pas un bug du skill lui-même si les instructions de `SKILL.md` ont bien été
  suivies — voir la note "agent-agnostique" en tête de `SKILL.md` : le skill donne les
  mêmes instructions à tous, il ne contrôle pas comment chaque agent les exécute.
