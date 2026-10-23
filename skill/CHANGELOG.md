# Changelog du skill

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
