#!/usr/bin/env python3
"""
Moteur d'état de l'entretien de découverte du besoin — exécutable en CLI, stdlib
uniquement, aucune dépendance externe.

Pourquoi un fichier et pas la mémoire de la conversation : si la conversation est
interrompue (coupure, changement d'agent, reprise le lendemain), l'état de l'entretien
ne doit pas se reperdre. C'est ce qui rend un entretien du type "PRD Assistant" de
Timefold fiable — l'état vit dans un fichier JSON, jamais seulement dans ce qu'un agent
"se souvient" avoir demandé.

Les sections, questions d'ouverture et critères de couverture sont lus depuis
reference/sections.json — ce script ne contient aucun texte métier en dur, pour que
sections.json reste la seule source de vérité sur CE qui est demandé.

Usage :
    python3 scripts/interview_state.py start
        -> crée un nouvel entretien, affiche son interview_id

    python3 scripts/interview_state.py record <section_id> "<réponse du client>" [--interview ID]
        -> enregistre un tour sur une section, met à jour sa couverture (voir
           "Évaluation de couverture" ci-dessous), affiche la progression de CETTE
           section après l'enregistrement

    python3 scripts/interview_state.py progress [--interview ID] [--verbose]
        -> affiche l'état de couverture de toutes les sections (○ ouvert / ◐ en cours /
           ● couvert) + un pourcentage global. --verbose liste aussi chaque tour avec
           son index, pour préparer un 'edit'.

    python3 scripts/interview_state.py edit <section> <turn_index> "<réponse corrigée>" [--interview ID]
        -> corrige une réponse déjà enregistrée (le client affine ou change une réponse
           suggérée/paraphrasée par l'agent) — ne recrée jamais un nouveau tour, remplace
           le tour existant pour que le PRD final reflète la version corrigée, pas les deux

    python3 scripts/interview_state.py prd [--interview ID] [--force] [--output-dir DIR]
        -> génère le PRD en Markdown depuis l'état. Refuse si couverture globale < seuil
           (reference/sections.json: threshold_percent) sauf --force (demande explicite
           de l'utilisateur à transmettre depuis l'agent, jamais à activer par défaut).

Évaluation de couverture — volontairement simple et vérifiable, PAS de NLP/LLM dans ce
script : un critère d'une section est marqué couvert dès qu'AU MOINS UNE réponse
enregistrée sur cette section contient un mot-clé associé (voir CRITERION_KEYWORDS
ci-dessous) OU dès que l'agent appelant marque explicitement le critère comme couvert
via --mark-criterion (l'agent, lui, SAIT ce qu'il vient de confirmer avec le client ;
ce script ne fait que persister ce qu'on lui dit, il ne comprend pas le français). Une
section est "◐ en cours" si au moins un tour est enregistré mais pas tous ses critères
couverts, "● couvert" si tous ses critères sont couverts, "○ ouvert" si aucun tour.

Ce script n'invente jamais de réponse : si un critère n'est pas marqué couvert, il reste
non couvert, point. C'est à l'agent (voir SKILL.md, règles d'entretien) de relancer sur
les critères manquants avant de passer à la section suivante, jamais à ce script de
deviner.
"""
import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SECTIONS_FILE = SKILL_ROOT / "reference" / "sections.json"
STATE_DIR = SKILL_ROOT.parent / ".interview_state"  # hors du repo du skill lui-même,
# jamais committé (voir .gitignore racine) : un état d'entretien est spécifique à un
# client, pas au skill.


def load_sections():
    with open(SECTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["sections"], data["threshold_percent"]


def state_path(interview_id: str) -> Path:
    return STATE_DIR / f"{interview_id}.json"


def new_interview_id() -> str:
    return secrets.token_hex(3)  # 6 hex, cohérent avec le suffixe du nom de fichier PRD


def load_state(interview_id: str) -> dict:
    path = state_path(interview_id)
    if not path.exists():
        print(f"[ERROR] Aucun entretien avec l'id {interview_id} ({path} introuvable). "
              f"Lance 'start' d'abord.", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(state["interview_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def latest_interview_id() -> str | None:
    """Si --interview est omis, utilise l'entretien le plus récemment modifié —
    confort pour l'agent appelant dans le cas (très courant) d'un seul entretien en
    cours à la fois. Un vrai multi-entretien doit toujours passer --interview."""
    if not STATE_DIR.exists():
        return None
    files = sorted(STATE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0].stem if files else None


def resolve_interview_id(args) -> str:
    interview_id = getattr(args, "interview", None) or latest_interview_id()
    if not interview_id:
        print("[ERROR] Aucun entretien trouvé. Lance 'start' d'abord, ou précise "
              "--interview ID.", file=sys.stderr)
        sys.exit(1)
    return interview_id


def cmd_start(args):
    sections, _ = load_sections()
    interview_id = new_interview_id()
    state = {
        "interview_id": interview_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": args.title or "Besoin client — à préciser",
        "sections": {
            s["id"]: {
                "label": s["label"],
                "turns": [],  # liste de {"at": iso, "answer": "..."}
                "covered_criteria": [],  # indices des critères marqués couverts
                "total_criteria": len(s["criteria"]),
            }
            for s in sections
        },
    }
    save_state(state)
    print(f"[OK] Entretien créé : {interview_id}")
    print(f"     État : {state_path(interview_id)}")
    print(f"     Sections à couvrir : {', '.join(s['id'] for s in sections)}")
    first = sections[0]
    print(f"\nPremière question (section '{first['id']}') :")
    print(f"  {first['opening_question']}")


def cmd_record(args):
    sections, _ = load_sections()
    section_ids = {s["id"] for s in sections}
    if args.section not in section_ids:
        print(f"[ERROR] Section inconnue : '{args.section}'. Sections valides : "
              f"{', '.join(sorted(section_ids))}", file=sys.stderr)
        sys.exit(1)

    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    sec_state = state["sections"][args.section]
    sec_state["turns"].append({
        "at": datetime.now(timezone.utc).isoformat(),
        "answer": args.answer,
    })

    sec_def = next(s for s in sections if s["id"] == args.section)

    def _check_idx(idx):
        if not (0 <= idx < len(sec_def["criteria"])):
            print(f"[ERROR] Index de critère invalide pour '{args.section}' : {idx} "
                  f"(section a {len(sec_def['criteria'])} critères, 0-indexés)",
                  file=sys.stderr)
            sys.exit(1)

    if args.mark_criterion is not None:
        for idx in args.mark_criterion:
            _check_idx(idx)
            if idx not in sec_state["covered_criteria"]:
                sec_state["covered_criteria"].append(idx)

    if args.unmark_criterion is not None:
        for idx in args.unmark_criterion:
            _check_idx(idx)
            if idx in sec_state["covered_criteria"]:
                sec_state["covered_criteria"].remove(idx)

    save_state(state)

    n_covered = len(sec_state["covered_criteria"])
    n_total = sec_state["total_criteria"]
    _, threshold = load_sections()
    global_pct = compute_global_percent(state, sections)
    n_sections_done = sum(
        1 for s in sections
        if len(state["sections"][s["id"]]["covered_criteria"]) >= state["sections"][s["id"]]["total_criteria"]
    )
    print(f"[OK] Tour enregistré sur '{args.section}' (entretien {interview_id}).")
    print(f"     Couverture de cette section : {n_covered}/{n_total}")
    print(f"     Avancement global : {global_pct}% ({n_sections_done}/{len(sections)} "
          f"sections complètes, seuil PRD {threshold}%)")
    print("     -> Partage ce chiffre avec le client à un moment naturel (ex. en "
          "clôturant la section) pour qu'il voie l'avancement, comme le fait le PRD "
          "Assistant de Timefold — voir reference/regles-entretien.md §2bis.")
    if n_covered < n_total:
        missing = [
            sec_def["criteria"][i] for i in range(n_total)
            if i not in sec_state["covered_criteria"]
        ]
        print("     Critères encore non couverts :")
        for crit in missing:
            print(f"       - {crit}")
        print("     -> Relance sur ces points avant de passer à la section suivante "
              "(voir SKILL.md, règles d'entretien).")


def cmd_edit(args):
    sections, _ = load_sections()
    section_ids = {s["id"] for s in sections}
    if args.section not in section_ids:
        print(f"[ERROR] Section inconnue : '{args.section}'. Sections valides : "
              f"{', '.join(sorted(section_ids))}", file=sys.stderr)
        sys.exit(1)

    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    sec_state = state["sections"][args.section]
    turns = sec_state["turns"]
    if not (0 <= args.turn_index < len(turns)):
        print(f"[ERROR] Index de tour invalide pour '{args.section}' : {args.turn_index} "
              f"({len(turns)} tour(s) enregistré(s), 0-indexés). Utilise "
              f"'progress --verbose' pour voir les tours et leur index.", file=sys.stderr)
        sys.exit(1)

    old_answer = turns[args.turn_index]["answer"]
    turns[args.turn_index]["answer"] = args.answer
    turns[args.turn_index]["edited_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    print(f"[OK] Réponse corrigée sur '{args.section}' (tour {args.turn_index}).")
    print(f"     Avant : {old_answer}")
    print(f"     Après : {args.answer}")
    print("     La couverture des critères n'a pas changé automatiquement — si cette "
          "correction change ce qui est couvert, relance 'record' avec "
          "--mark-criterion/--unmark-criterion pour la mettre à jour.")


def section_symbol(n_covered: int, n_turns: int, n_total: int) -> str:
    if n_covered >= n_total and n_total > 0:
        return "●"
    if n_turns > 0:
        return "◐"
    return "○"


def compute_global_percent(state: dict, sections: list) -> float:
    total_criteria = sum(len(s["criteria"]) for s in sections)
    if total_criteria == 0:
        return 0.0
    covered = sum(len(state["sections"][s["id"]]["covered_criteria"]) for s in sections)
    return round(100 * covered / total_criteria, 1)


def cmd_progress(args):
    sections, threshold = load_sections()
    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)

    print(f"Entretien {interview_id} — {state.get('title', '(sans titre)')}")
    print("-" * 60)
    for s in sections:
        sec_state = state["sections"][s["id"]]
        n_covered = len(sec_state["covered_criteria"])
        n_total = sec_state["total_criteria"]
        n_turns = len(sec_state["turns"])
        symbol = section_symbol(n_covered, n_turns, n_total)
        print(f"  {symbol} {s['id']:<14} {s['label']:<42} {n_covered}/{n_total} critères "
              f"({n_turns} tour(s))")
        if args.verbose:
            for i, turn in enumerate(sec_state["turns"]):
                edited = " (corrigé)" if "edited_at" in turn else ""
                print(f"       [{i}] {turn['answer']}{edited}")

    pct = compute_global_percent(state, sections)
    print("-" * 60)
    status = "OK — PRD possible" if pct >= threshold else f"sous le seuil de {threshold}%"
    print(f"  Couverture globale : {pct}% ({status})")


def render_prd_markdown(state: dict, sections: list, pct: float) -> str:
    lines = []
    title = state.get("title") or "Besoin client"
    lines.append(f"# PRD — {title}")
    lines.append("")
    lines.append(f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
                 f"par scripts/interview_state.py — entretien `{state['interview_id']}`, "
                 f"couverture globale {pct}%.*")
    lines.append("")
    lines.append("> Ce document reprend uniquement ce qui a été dit pendant l'entretien. "
                 "Aucune réponse n'est inventée — une section marquée incomplète ci-dessous "
                 "doit être reprise avec le client avant de construire le payload final.")
    lines.append("")
    for s in sections:
        sec_state = state["sections"][s["id"]]
        n_covered = len(sec_state["covered_criteria"])
        n_total = sec_state["total_criteria"]
        lines.append(f"## {s['label']}")
        lines.append("")
        lines.append(f"**Couverture : {n_covered}/{n_total} critères.**")
        lines.append("")
        if sec_state["turns"]:
            for turn in sec_state["turns"]:
                lines.append(f"- {turn['answer']}")
        else:
            lines.append("*(aucune réponse enregistrée sur cette section)*")
        lines.append("")
        uncovered = [
            s["criteria"][i] for i in range(n_total)
            if i not in sec_state["covered_criteria"]
        ]
        if uncovered:
            lines.append("**Points encore à clarifier :**")
            for crit in uncovered:
                lines.append(f"- {crit}")
            lines.append("")
    return "\n".join(lines)


def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "besoin"


def cmd_prd(args):
    sections, threshold = load_sections()
    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    pct = compute_global_percent(state, sections)

    if pct < threshold and not args.force:
        print(f"[ERROR] Couverture globale {pct}% < seuil {threshold}%. Le PRD n'est "
              f"généré qu'au-dessus du seuil, SAUF demande explicite de l'utilisateur "
              f"(relancer avec --force dans ce cas précis — jamais par défaut).",
              file=sys.stderr)
        sys.exit(1)

    md = render_prd_markdown(state, sections, pct)
    out_dir = Path(args.output_dir) if args.output_dir else (SKILL_ROOT / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(state.get("title", "besoin"))
    filename = f"{slug}-PRD-{interview_id}.md"
    out_path = out_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[OK] PRD écrit : {out_path}")
    print(f"     Couverture au moment de la génération : {pct}%"
          + (" (forcé sous le seuil)" if pct < threshold else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="crée un nouvel entretien")
    p_start.add_argument("--title", help="titre provisoire du besoin/client (peut être affiné plus tard)")
    p_start.set_defaults(func=cmd_start)

    p_record = sub.add_parser("record", help="enregistre un tour sur une section")
    p_record.add_argument("section", help="id de section (voir reference/sections.json)")
    p_record.add_argument("answer", help="réponse du client, reformulée fidèlement — jamais inventée")
    p_record.add_argument("--interview", help="id de l'entretien (défaut : le plus récent)")
    p_record.add_argument("--mark-criterion", type=int, nargs="*", default=None,
                           help="index(es) 0-based des critères de cette section que CETTE réponse "
                                "couvre explicitement, d'après le jugement de l'agent appelant — "
                                "ce script ne devine jamais ça seul")
    p_record.add_argument("--unmark-criterion", type=int, nargs="*", default=None,
                           help="index(es) 0-based à repasser en non-couvert — utile pour rouvrir "
                                "une section déjà marquée ● suite à \"parler de cette section\"")
    p_record.set_defaults(func=cmd_record)

    p_edit = sub.add_parser("edit", help="corrige une réponse déjà enregistrée (le client a changé d'avis ou corrige une suggestion)")
    p_edit.add_argument("section", help="id de section")
    p_edit.add_argument("turn_index", type=int, help="index 0-based du tour à corriger (voir 'progress --verbose' ou le PRD généré)")
    p_edit.add_argument("answer", help="texte corrigé qui remplace l'ancienne réponse")
    p_edit.add_argument("--interview", help="id de l'entretien (défaut : le plus récent)")
    p_edit.set_defaults(func=cmd_edit)

    p_progress = sub.add_parser("progress", help="affiche la couverture de l'entretien")
    p_progress.add_argument("--interview", help="id de l'entretien (défaut : le plus récent)")
    p_progress.add_argument("--verbose", action="store_true",
                             help="liste aussi chaque tour avec son index, pour préparer un 'edit'")
    p_progress.set_defaults(func=cmd_progress)

    p_prd = sub.add_parser("prd", help="génère le PRD en Markdown depuis l'état")
    p_prd.add_argument("--interview", help="id de l'entretien (défaut : le plus récent)")
    p_prd.add_argument("--force", action="store_true",
                        help="génère même sous le seuil — uniquement sur demande EXPLICITE de "
                             "l'utilisateur, jamais par défaut ni sur initiative de l'agent")
    p_prd.add_argument("--output-dir", help="dossier de sortie (défaut : skill/output/)")
    p_prd.set_defaults(func=cmd_prd)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
