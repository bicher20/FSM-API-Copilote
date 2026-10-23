# Contribuer à ce skill

Projet solo pour l'instant, mais quelques règles pour que le skill reste fiable à
mesure qu'il grossit — inspiré des pratiques des repos de solveurs matures
(CONTRIBUTING.md/CONSTITUTION.md de `TimefoldAI/timefold-solver`).

## Principes

1. **Jamais de champ deviné.** Tout ajout qui touche au schéma Nomadia doit être
   vérifié contre `skill/reference/entities.md` (ou la doc officielle), jamais écrit
   de mémoire.
2. **Jamais de clé API en dur.** Aucun fichier commité ne doit contenir une clé API
   réelle, même pour un exemple "de test". Utiliser `--api-key`/variable d'env dans
   les scripts, `.env` dans les projets intégrateurs.
3. **Tout exemple ajouté dans `examples/` doit passer `validate_payload.py`** avant
   d'être commité — sans exception, même pour un exemple volontairement minimal.
4. **Toute modification de `scripts/validate_payload.py` doit être suivie d'un run de
   `scripts/test_validate_payload.py`** — ne jamais committer un changement du
   validateur sans relancer ses tests (une régression silencieuse s'est déjà produite
   une fois sur l'heuristique lat/lng, voir `skill/CHANGELOG.md` 1.2).
5. **Versionner.** Toute évolution de `skill/SKILL.md` qui change la procédure ou
   ajoute un fichier doit : bumper `version:` dans le frontmatter, ajouter une entrée
   dans `skill/CHANGELOG.md`, et mettre à jour `skill/llms.txt` si un nouveau fichier
   change ce qu'un agent doit lire.
6. **Agent-agnostique.** Aucune instruction du skill ne doit supposer un agent IA
   précis (Claude Code, Cursor, etc.) — seulement un accès fichiers + shell.

## Avant de committer

```bash
python3 skill/scripts/test_validate_payload.py   # doit afficher "TOUS LES TESTS PASSENT"
for f in skill/examples/*.json; do python3 skill/scripts/validate_payload.py "$f"; done
```
