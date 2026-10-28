#!/usr/bin/env python3
"""
Moteur d'état de l'entretien de découverte du besoin — exécutable en CLI, stdlib
uniquement, aucune dépendance externe.

Pourquoi un fichier et pas la mémoire de la conversation : si la conversation est
interrompue (coupure, changement d'agent, reprise le lendemain), l'état de l'entretien
ne doit pas se reperdre. L'état vit dans un fichier JSON, jamais seulement dans ce
qu'un agent "se souvient" avoir demandé.

Les sections, questions d'ouverture et critères de couverture sont lus depuis
reference/sections.json — ce script ne contient aucun texte métier en dur, pour que
sections.json reste la seule source de vérité sur CE qui est demandé.

Usage :
    python3 scripts/interview_state.py start [--title "<client/besoin>"]
        -> crée un nouvel entretien, affiche son interview_id. Passer --title avec un
           repère reconnaissable (nom du client) : c'est ce que 'list' affiche pour
           retrouver cet entretien, un id hexadécimal seul ne dit rien.

    python3 scripts/interview_state.py list
        -> liste TOUS les entretiens en cours (id, titre, % de couverture), triés du
           plus récent au plus ancien. Indispensable dès que plusieurs clients sont
           suivis en parallèle : sans --interview explicite, les autres commandes
           prennent par défaut le plus récemment modifié, ce qui n'est PAS forcément
           le bon client si une conversation a été reprise entre-temps sur un autre
           dossier.

    python3 scripts/interview_state.py options <section_id> [--interview ID] [--page N]
        -> affiche le QCM de cette section (options numérotées + leur id), à poser au
           client tel quel : "plusieurs choix possibles, et tu peux préciser en plus".
           Un dernier numéro ("Autre chose à préciser") est TOUJOURS ajouté explicitement
           pour le texte libre — jamais juste une note en petit sous la liste. Les
           options marquées 'depends_on' dans sections.json et non encore pertinentes
           d'après les réponses déjà enregistrées de cet entretien sont masquées
           automatiquement (ex. pas de question "binôme technicien" si aucun technicien
           n'a été identifié en section entités) — l'agent n'a jamais à décider lui-même
           quoi cacher, le script le fait depuis l'état réel de l'entretien. Jamais plus
           de MAX_CHOICES_PER_SCREEN (4) choix affichés en une fois : au-delà, la section
           est automatiquement coupée en plusieurs parties ("partie 1/2", etc.) —
           --page sélectionne laquelle, et la sortie indique explicitement s'il y a une
           suite à rappeler une fois la réponse du client sur la partie courante notée.

    python3 scripts/interview_state.py record <section_id> ["<précision libre>"] [--options id1,id2,...] [--interview ID]
        -> enregistre un tour sur une section. --options prend les id choisis par le
           client (voir 'options <section_id>'), séparés par des virgules, et marque
           AUTOMATIQUEMENT les critères que ces choix couvrent
           (reference/sections.json: options[].criteria) — plus besoin que l'agent
           devine quel critère une réponse libre couvre. Le texte libre optionnel
           (positionnel, à placer avant --options) s'ajoute en précision, pour ce
           qu'aucune option ne couvre. --mark-criterion/--unmark-criterion restent
           disponibles pour un ajustement manuel (ex. critères 2/3 qui dépendent d'une
           autre section, jamais couverts par un seul choix QCM).

    python3 scripts/interview_state.py progress [--interview ID] [--verbose]
        -> affiche l'état de couverture de toutes les sections (○ ouvert / ◐ en cours /
           ● couvert) + un pourcentage global. --verbose liste aussi chaque tour avec
           son index, pour préparer un 'edit'.

    python3 scripts/interview_state.py edit <section> <turn_index> "<réponse corrigée>" [--interview ID]
        -> corrige une réponse déjà enregistrée (le client affine ou change une réponse
           suggérée/paraphrasée par l'agent) — ne recrée jamais un nouveau tour, remplace
           le tour existant pour que le PRD final reflète la version corrigée, pas les deux

    python3 scripts/interview_state.py prd [--interview ID] [--force] [--output-dir DIR]
                                            [--summary "<texte>"] [--entity "Nom|Statut|Description" ...]
        -> génère le PRD en Markdown depuis l'état. Refuse si couverture globale < seuil
           (reference/sections.json: threshold_percent) sauf --force (demande explicite
           de l'utilisateur à transmettre depuis l'agent, jamais à activer par défaut).
           --summary (optionnel) : un court récap écrit par l'agent ("ce qui est
           planifié"), inséré en tête du PRD. --entity (optionnel, répétable) : une
           entité du besoin au format "Nom|Statut|Description" (ex. "Interventions
           client|Planifiées|affectées à un technicien, un ordre et un horaire") —
           rendue en liste structurée sous "Ce qui est planifié", en plus ou à la place
           du --summary en texte libre ; jamais déduite automatiquement des labels QCM,
           c'est à l'agent de l'écrire d'après ce que le client a réellement dit. Le PRD
           se termine aussi par un récapitulatif global "Non négociable" / "Nice to
           have" qui agrège tous les thèmes (pas seulement 'contraintes') — sections.json:
           options[].hard, plus les objectifs (toujours classés "nice to have").

    python3 scripts/interview_state.py score [--interview ID]
        -> score de complétude self-service / offre complète : repère, parmi les
           contraintes cochées, celles qui correspondent à un mécanisme offre-complète-
           only documenté (sections.json: options[].offre_complete_trigger — stock de
           pièces, ordre entre jobs, binôme/multi-ressources), compare au niveau d'offre
           confirmé en section niveau_offre, et signale explicitement le cas "offre
           complète requise" (besoin détecté mais clé self-service/pas encore de clé/pas
           clarifié) au lieu de laisser l'agent le remarquer ou pas. Ce signal n'est
           JAMAIS un blocage : mène toujours l'entretien comme si on visait l'offre
           complète (jamais un périmètre réduit selon le niveau d'offre détecté), et
           présente le self-service au client sur un mode positif — "on sait gérer ça,
           il faudra juste nous contacter" — jamais comme une limite qui arrête la
           conversation. Ne couvre QUE ces 3 mécanismes-là — horizon de planification,
           disponibilité récurrente et priorité de rdv dédiée restent à vérifier
           soi-même (voir reference/offre-complete-nomadia.md).

    python3 scripts/interview_state.py handoff [--interview ID] [--summary "<texte>"]
        -> génère un message prêt à adapter (jamais envoyé automatiquement) pour mettre
           le client en relation avec le contact nommé (Marouane Bicher,
           marouane.bicher@nomadia.com), dès qu'il confirme vouloir passer par le
           compte pro/l'offre complète — reprend les mécanismes détectés par 'score'
           si --summary n'est pas fourni. À relire et adapter avant tout envoi réel.

Évaluation de couverture — volontairement simple et vérifiable, PAS de NLP/LLM dans ce
script : un critère d'une section est marqué couvert dès que le client a choisi une
option liée à ce critère (voir `options <section>` et `sections.json: options[].criteria`),
OU dès que l'agent appelant le marque explicitement via --mark-criterion (pour les
critères qu'un seul choix ne suffit pas à couvrir — l'agent, lui, SAIT ce qu'il vient de
confirmer avec le client ; ce script ne fait que persister ce qu'on lui dit, il ne
comprend pas le français). Une section est "◐ en cours" si au moins un tour est
enregistré mais pas tous ses critères couverts, "● couvert" si tous ses critères sont
couverts, "○ ouvert" si aucun tour.

Ce script n'invente jamais de réponse : si un critère n'est pas marqué couvert, il reste
non couvert, point. C'est à l'agent (voir SKILL.md, règles d'entretien) de relancer sur
les critères manquants avant de passer à la section suivante, jamais à ce script de
deviner.
"""
import argparse
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SECTIONS_FILE = SKILL_ROOT / "reference" / "sections.json"
STATE_DIR = SKILL_ROOT.parent / ".interview_state"  # hors du repo du skill lui-même,
# jamais committé (voir .gitignore racine) : un état d'entretien est spécifique à un
# client, pas au skill.

MAX_CHOICES_PER_SCREEN = 4  # jamais plus de 3-4 choix présentés en une fois au client
# (+ le numéro "autre chose à préciser") — une section avec plus d'options que ça est
# automatiquement présentée en plusieurs parties plutôt que balancée d'un bloc.

# Couleurs ANSI par défaut dans le terminal — désactivées automatiquement si
# NO_COLOR est défini (convention standard, voir no-color.org) ou si la sortie n'est
# pas un vrai terminal (redirection vers un fichier, pipe, agent qui capture le texte
# brut) : jamais de code ANSI littéral dans un fichier ou un résultat non affiché tel
# quel. Aucune dépendance externe (pas de colorama) — juste des séquences ANSI brutes.
_USE_COLOR = not os.environ.get("NO_COLOR") and sys.stdout.isatty()
_CODES = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "bold": "1", "dim": "2"}


def c(text: str, *styles: str) -> str:
    """Colore `text` si le terminal le supporte, sinon le rend tel quel — jamais de
    code ANSI qui traînerait dans une sortie redirigée ou relue par un autre outil."""
    if not _USE_COLOR or not styles:
        return text
    prefix = "".join(f"\033[{_CODES[s]}m" for s in styles if s in _CODES)
    return f"{prefix}{text}\033[0m"


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
        print(f"{c('[ERROR]', 'red', 'bold')} Aucun entretien avec l'id {interview_id} ({path} introuvable). "
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
        print(f"{c('[ERROR]', 'red', 'bold')} Aucun entretien trouvé. Lance 'start' d'abord, ou précise "
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
    print(f"{c('[OK]', 'green', 'bold')} Entretien créé : {interview_id}")
    print(f"     État : {state_path(interview_id)}")
    print(f"     Sections à couvrir : {', '.join(s['id'] for s in sections)}")
    first = sections[0]
    print(f"\nPremière question (section '{first['id']}') :")
    print(f"  {first['opening_question']}")


def _selected_option_ids(sec_state: dict) -> set[str]:
    """Tous les id d'options choisies au fil des tours d'une section — sert de base au
    filtrage 'depends_on' des autres sections."""
    chosen: set[str] = set()
    for turn in sec_state.get("turns", []):
        chosen.update(turn.get("option_ids") or [])
    return chosen


def _option_visible(opt: dict, state: dict | None) -> bool:
    """Le 'cerveau' qui évite d'envoyer systématiquement la liste complète de choix :
    une option avec 'depends_on' reste invisible tant que la section référencée n'a pas
    déjà reçu au moins une des réponses listées. Sans état d'entretien résolu (aucun
    entretien démarré encore), ou sans 'depends_on', l'option reste visible par défaut —
    on ne filtre jamais à l'aveugle, seulement à partir de ce que le client a confirmé."""
    dep = opt.get("depends_on")
    if not dep or state is None:
        return True
    dep_section_id = dep.get("section")
    any_of = set(dep.get("any_of") or [])
    if not dep_section_id or not any_of:
        return True
    sec_state = state["sections"].get(dep_section_id)
    if sec_state is None:
        return False
    return bool(_selected_option_ids(sec_state) & any_of)


def _grouped_visible_options(sec_def: dict, visible: list[dict]) -> list[tuple[str | None, list[dict]]]:
    """Regroupe les options visibles par 'hard' (dur / souple) avant pagination, pour
    qu'une page ne mélange jamais une contrainte dure et une préférence souple sans le
    dire — jamais paginer à l'aveugle sur l'ordre brut du fichier. Sections sans flag
    'hard' (la plupart) : un seul groupe sans sous-titre, comportement inchangé."""
    if not any("hard" in opt for opt in sec_def.get("options", [])):
        return [(None, visible)]
    hard = [o for o in visible if o.get("hard") is True]
    soft = [o for o in visible if o.get("hard") is False]
    other = [o for o in visible if "hard" not in o]
    groups: list[tuple[str | None, list[dict]]] = []
    if hard:
        groups.append(("Contraintes dures (jamais violées)", hard))
    if soft:
        groups.append(("Préférences souples (arbitrables)", soft))
    if other:
        groups.append((None, other))
    return groups


def cmd_options(args):
    sections, _ = load_sections()
    sec_def = next((s for s in sections if s["id"] == args.section), None)
    if sec_def is None:
        print(f"{c('[ERROR]', 'red', 'bold')} Section inconnue : '{args.section}'. Sections valides : "
              f"{', '.join(sorted(s['id'] for s in sections))}", file=sys.stderr)
        sys.exit(1)

    interview_id = getattr(args, "interview", None) or latest_interview_id()
    state = load_state(interview_id) if interview_id and state_path(interview_id).exists() else None

    all_options = sec_def.get("options", [])
    visible = [opt for opt in all_options if _option_visible(opt, state)]
    hidden_count = len(all_options) - len(visible)

    # Pagine GROUPE PAR GROUPE (dur, puis souple) pour qu'une page ne mélange jamais
    # les deux sans le dire — jamais un découpage brut sur l'ordre du fichier.
    groups = _grouped_visible_options(sec_def, visible)
    pages: list[tuple[str | None, list[dict]]] = []
    for group_label, group_opts in groups:
        if not group_opts:
            continue
        for i in range(0, len(group_opts), MAX_CHOICES_PER_SCREEN):
            pages.append((group_label, group_opts[i:i + MAX_CHOICES_PER_SCREEN]))
    if not pages:
        pages = [(None, [])]
    total_pages = len(pages)
    page = max(1, min(getattr(args, "page", 1) or 1, total_pages))
    group_label, chunk = pages[page - 1]

    print(sec_def["opening_question"])
    if total_pages > 1:
        print(c(f"(partie {page}/{total_pages} — jamais plus de {MAX_CHOICES_PER_SCREEN} choix "
                f"à la fois pour rester lisible pour le client)", "dim"))
    if group_label:
        print(c(f"-- {group_label} --", "bold"))
    for i, opt in enumerate(chunk, start=1):
        id_tag = c(f"[id: {opt['id']}]", "dim")
        print(f"  {c(str(i), 'cyan', 'bold')}. {opt['label']}   {id_tag}")
    free_text_num = len(chunk) + 1
    if sec_def.get("allow_free_text", True):
        print(f"  {c(str(free_text_num), 'cyan', 'bold')}. Autre chose à préciser, pas dans la liste ci-dessus")
    print("\n-> plusieurs choix possibles. Présente cette liste numérotée au client "
          "tel quel (sans les [id: ...], c'est pour toi) ; il répond par les numéros. "
          "record --options reçoit les id correspondants aux numéros choisis, séparés "
          "par des virgules (ex. --options e1,e4,e6) — jamais les numéros eux-mêmes, qui "
          "ne sont qu'un affichage. Si le client choisit le numéro "
          f"{free_text_num} ('Autre chose à préciser'), note ce qu'il dit comme texte "
          "libre positionnel de 'record' (pas dans --options, ce n'est pas une vraie "
          "option) — ex. record <section> \"ce que le client a précisé\" --options ...")
    if page < total_pages:
        print(c(f"-> d'autres choix existent pour cette même question : une fois la réponse "
                f"du client sur cette partie enregistrée (record), rappelle "
                f"'options {sec_def['id']} --page {page + 1}"
                f"{f' --interview {interview_id}' if interview_id else ''}' pour lui proposer "
                f"la suite dans la même conversation — jamais tout balancer d'un coup.", "yellow"))
    if hidden_count:
        print(c(f"({hidden_count} choix non pertinent(s) à ce stade ont été masqués "
                f"automatiquement d'après les réponses déjà données — rien à filtrer "
                f"toi-même.)", "dim"))


def _resolve_options(sec_def: dict, option_ids: list[str] | None) -> tuple[list[str], list[int]]:
    """Retourne (labels choisis, indices de critères couverts) pour une liste d'id
    d'options. Erreur si un id ne correspond à aucune option connue de la section —
    jamais un id ignoré silencieusement, pour éviter de rater une réponse du client."""
    if not option_ids:
        return [], []
    by_id = {opt["id"]: opt for opt in sec_def.get("options", [])}
    labels, criteria_idx = [], []
    for oid in option_ids:
        opt = by_id.get(oid)
        if opt is None:
            valid = ", ".join(sorted(by_id)) or "(aucune option définie pour cette section)"
            print(f"{c('[ERROR]', 'red', 'bold')} Option inconnue '{oid}' pour la section '{sec_def['id']}'. "
                  f"Options valides : {valid}. Vérifie avec "
                  f"'scripts/interview_state.py options {sec_def['id']}'.", file=sys.stderr)
            sys.exit(1)
        labels.append(opt["label"])
        criteria_idx.extend(opt.get("criteria", []))
    return labels, criteria_idx


def cmd_record(args):
    sections, _ = load_sections()
    section_ids = {s["id"] for s in sections}
    if args.section not in section_ids:
        print(f"{c('[ERROR]', 'red', 'bold')} Section inconnue : '{args.section}'. Sections valides : "
              f"{', '.join(sorted(section_ids))}", file=sys.stderr)
        sys.exit(1)

    sec_def = next(s for s in sections if s["id"] == args.section)
    option_ids = [o.strip() for o in args.options.split(",") if o.strip()] if args.options else []
    option_labels, option_criteria = _resolve_options(sec_def, option_ids)

    free_text = (args.answer or "").strip()
    if not option_labels and not free_text:
        print(f"{c('[ERROR]', 'red', 'bold')} Rien à enregistrer : passe --options (choix du client) et/ou "
              "un texte libre.", file=sys.stderr)
        sys.exit(1)
    composed = "; ".join(option_labels)
    if free_text:
        composed = f"{composed} + précision : {free_text}" if composed else free_text

    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    sec_state = state["sections"][args.section]
    sec_state["turns"].append({
        "at": datetime.now(timezone.utc).isoformat(),
        "answer": composed,
        **({"option_ids": option_ids} if option_ids else {}),
    })

    def _check_idx(idx):
        if not (0 <= idx < len(sec_def["criteria"])):
            print(f"{c('[ERROR]', 'red', 'bold')} Index de critère invalide pour '{args.section}' : {idx} "
                  f"(section a {len(sec_def['criteria'])} critères, 0-indexés)",
                  file=sys.stderr)
            sys.exit(1)

    all_to_mark = list(option_criteria) + list(args.mark_criterion or [])
    for idx in all_to_mark:
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
    print(f"{c('[OK]', 'green', 'bold')} Tour enregistré sur '{args.section}' (entretien {interview_id}).")
    print(f"     Couverture de cette section : {n_covered}/{n_total}")
    print(f"     Avancement global : {c(f'{global_pct}%', 'cyan', 'bold')} "
          f"({n_sections_done}/{len(sections)} sections complètes, seuil PRD {threshold}%)")
    print("     -> Partage ce chiffre avec le client à un moment naturel (ex. en "
          "clôturant la section) pour qu'il voie l'avancement — voir "
          "reference/regles-entretien.md §2bis.")
    if n_covered < n_total:
        missing = [
            sec_def["criteria"][i] for i in range(n_total)
            if i not in sec_state["covered_criteria"]
        ]
        print("     Critères encore non couverts :")
        for crit in missing:
            print(f"       - {crit}")
        print("     -> Relance sur ces points avant de passer à la section suivante — "
              "REFORMULE la question différemment (jamais un copier-coller de la même "
              "phrase) et nomme précisément ce qui manque encore, pour que le client "
              "comprenne tout de suite quoi préciser (voir SKILL.md, règles d'entretien "
              "§4bis).")


def cmd_edit(args):
    sections, _ = load_sections()
    section_ids = {s["id"] for s in sections}
    if args.section not in section_ids:
        print(f"{c('[ERROR]', 'red', 'bold')} Section inconnue : '{args.section}'. Sections valides : "
              f"{', '.join(sorted(section_ids))}", file=sys.stderr)
        sys.exit(1)

    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    sec_state = state["sections"][args.section]
    turns = sec_state["turns"]
    if not (0 <= args.turn_index < len(turns)):
        print(f"{c('[ERROR]', 'red', 'bold')} Index de tour invalide pour '{args.section}' : {args.turn_index} "
              f"({len(turns)} tour(s) enregistré(s), 0-indexés). Utilise "
              f"'progress --verbose' pour voir les tours et leur index.", file=sys.stderr)
        sys.exit(1)

    old_answer = turns[args.turn_index]["answer"]
    turns[args.turn_index]["answer"] = args.answer
    turns[args.turn_index]["edited_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    print(f"{c('[OK]', 'green', 'bold')} Réponse corrigée sur '{args.section}' (tour {args.turn_index}).")
    print(f"     Avant : {old_answer}")
    print(f"     Après : {args.answer}")
    print("     La couverture des critères n'a pas changé automatiquement — si cette "
          "correction change ce qui est couvert, relance 'record' avec "
          "--mark-criterion/--unmark-criterion pour la mettre à jour.")


def section_symbol(n_covered: int, n_turns: int, n_total: int) -> str:
    if n_covered >= n_total and n_total > 0:
        return c("●", "green", "bold")
    if n_turns > 0:
        return c("◐", "yellow", "bold")
    return c("○", "dim")


def compute_global_percent(state: dict, sections: list) -> float:
    total_criteria = sum(len(s["criteria"]) for s in sections)
    if total_criteria == 0:
        return 0.0
    covered = sum(len(state["sections"][s["id"]]["covered_criteria"]) for s in sections)
    return round(100 * covered / total_criteria, 1)


def cmd_list(args):
    """Liste tous les entretiens en cours (fichiers dans STATE_DIR), triés du plus
    récent au plus ancien — indispensable dès qu'on suit plusieurs clients en
    parallèle : 'latest_interview_id()' ne suffit plus à lui seul pour retrouver un
    entretien précis, et personne ne doit avoir à mémoriser un id hexadécimal."""
    sections, threshold = load_sections()
    if not STATE_DIR.exists():
        print("Aucun entretien en cours.")
        return
    files = sorted(STATE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("Aucun entretien en cours.")
        return
    print(f"{len(files)} entretien(s) :\n")
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        pct = compute_global_percent(state, sections)
        status_text = "PRD possible" if pct >= threshold else f"sous le seuil ({threshold}%)"
        status = c(f"{status_text:<22}", "green", "bold") if pct >= threshold else c(f"{status_text:<22}", "yellow")
        created = state.get("created_at", "date inconnue")
        print(f"  {state['interview_id']}  {c(f'{pct:>5}%', 'cyan')}  {status}  "
              f"{state.get('title', '(sans titre)')}  — créé {created}")
    print(f"\nPasse --interview ID à n'importe quelle commande pour reprendre un "
          f"entretien précis plutôt que le plus récent par défaut.")


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
    if pct >= threshold:
        status = c("OK — PRD possible", "green", "bold")
    else:
        status = c(f"sous le seuil de {threshold}%", "yellow")
    print(f"  Couverture globale : {c(f'{pct}%', 'cyan', 'bold')} ({status})")


def _classify_turn_by_hardness(sec_def: dict, turn: dict) -> str:
    """Pour une section dont au moins une option porte un flag 'hard' (ex.
    'contraintes') : dit si CE tour est plutôt non négociable, souple, ou mixte/texte
    libre seul. Ne classe rien pour une section sans flag 'hard' défini (retourne
    None) — jamais une classification devinée sur une section qui ne s'y prête pas."""
    by_id = {opt["id"]: opt for opt in sec_def.get("options", [])}
    if not any("hard" in opt for opt in by_id.values()):
        return None
    option_ids = turn.get("option_ids") or []
    hards = [by_id[oid]["hard"] for oid in option_ids if oid in by_id and "hard" in by_id[oid]]
    if not hards:
        return "texte_libre"
    if all(hards):
        return "dur"
    if not any(hards):
        return "souple"
    return "mixte"


def _parse_entities(raw: list[str] | None) -> list[dict]:
    """Parse les --entity "Nom|Statut|Description" en triplets. Erreur explicite si le
    format ne respecte pas les 3 champs séparés par '|' — jamais une entité tronquée ou
    mal coupée silencieusement."""
    entities = []
    for item in raw or []:
        parts = [p.strip() for p in item.split("|")]
        if len(parts) != 3 or not all(parts):
            print(f"{c('[ERROR]', 'red', 'bold')} --entity attend le format "
                  f"\"Nom|Statut|Description\" (3 champs non vides séparés par '|'), reçu : "
                  f"'{item}'", file=sys.stderr)
            sys.exit(1)
        name, status, desc = parts
        entities.append({"name": name, "status": status, "description": desc})
    return entities


def _build_global_roundup(state: dict, sections: list) -> tuple[list[str], list[str]]:
    """Agrège, sur TOUS les thèmes (pas seulement 'contraintes'), deux listes uniques :
    non-négociable et nice-to-have — inspiré de la structure d'un rapport de besoin qui
    pose ces deux catégories une seule fois en fin de document plutôt que section par
    section. Classement fait OPTION par OPTION (jamais tour par tour), pour qu'un tour
    "mixte" (ex. deux contraintes dures + une préférence souple cochées ensemble) ne
    duplique pas toute la phrase composée dans les deux listes — chaque item choisi va
    dans sa seule bonne liste, sans mélange :
    - 'contraintes' : chaque option cochée au moins une fois est classée via son flag
      options[].hard (dur -> non négociable, souple -> nice to have) ;
    - 'objectifs' : chaque option cochée est un objectif à optimiser, donc classée
      nice-to-have par nature (jamais non-négociable — un KPI priorisé n'est pas une
      contrainte dure) ;
    - le texte libre (sans option associée) et les autres sections (entités, taille,
      niveau_offre) ne portent pas de notion de négociabilité et n'alimentent pas ce
      récapitulatif — ils restent visibles dans le détail par section ci-dessus."""
    non_negociable: list[str] = []
    nice_to_have: list[str] = []

    contraintes_def = next((s for s in sections if s["id"] == "contraintes"), None)
    if contraintes_def is not None:
        by_id = {opt["id"]: opt for opt in contraintes_def.get("options", [])}
        seen_hard, seen_soft = set(), set()
        for turn in state["sections"]["contraintes"]["turns"]:
            for oid in turn.get("option_ids") or []:
                opt = by_id.get(oid)
                if opt is None or "hard" not in opt:
                    continue
                if opt["hard"] and opt["id"] not in seen_hard:
                    seen_hard.add(opt["id"])
                    non_negociable.append(opt["label"])
                elif not opt["hard"] and opt["id"] not in seen_soft:
                    seen_soft.add(opt["id"])
                    nice_to_have.append(opt["label"])

    objectifs_def = next((s for s in sections if s["id"] == "objectifs"), None)
    if objectifs_def is not None:
        by_id = {opt["id"]: opt for opt in objectifs_def.get("options", [])}
        seen = set()
        for turn in state["sections"]["objectifs"]["turns"]:
            for oid in turn.get("option_ids") or []:
                if oid in by_id and oid not in seen:
                    seen.add(oid)
                    nice_to_have.append(by_id[oid]["label"])

    return non_negociable, nice_to_have


def render_prd_markdown(state: dict, sections: list, pct: float, summary: str | None = None,
                         entities: list[dict] | None = None) -> str:
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
    if summary or entities:
        lines.append("## Ce qui est planifié")
        lines.append("")
        if summary:
            lines.append(summary.strip())
            lines.append("")
        if entities:
            for ent in entities:
                lines.append(f"- **{ent['name']}** — *{ent['status']}* : {ent['description']}")
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
            # Section avec distinction dur/souple (ex. contraintes) : deux groupes
            # séparés plutôt qu'un paragraphe mélangé — plus net pour le client qui
            # relit le PRD et pour l'agent qui enchaîne vers le payload.
            buckets: dict[str, list[str]] = {"dur": [], "souple": [], "mixte": [], "texte_libre": []}
            any_classified = False
            for turn in sec_state["turns"]:
                kind = _classify_turn_by_hardness(s, turn)
                if kind is None:
                    buckets.setdefault("_flat", []).append(turn["answer"])
                else:
                    any_classified = True
                    buckets[kind].append(turn["answer"])
            if any_classified:
                if buckets["dur"]:
                    lines.append("**Non négociable :**")
                    for a in buckets["dur"]:
                        lines.append(f"- {a}")
                    lines.append("")
                if buckets["souple"]:
                    lines.append("**Souple (arbitrable) :**")
                    for a in buckets["souple"]:
                        lines.append(f"- {a}")
                    lines.append("")
                for a in buckets["mixte"] + buckets["texte_libre"]:
                    lines.append(f"- {a}")
                if buckets["mixte"] or buckets["texte_libre"]:
                    lines.append("")
            else:
                for a in buckets.get("_flat", []):
                    lines.append(f"- {a}")
                lines.append("")
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

    non_negociable, nice_to_have = _build_global_roundup(state, sections)
    if non_negociable or nice_to_have:
        lines.append("## Récapitulatif global — tous thèmes confondus")
        lines.append("")
        lines.append("*Reprend en un seul endroit ce qui est non négociable et ce qui est "
                     "nice to have, toutes sections mélangées — le détail par thème ci-dessus "
                     "reste la référence si un point précis doit être retracé.*")
        lines.append("")
        if non_negociable:
            lines.append("**Non négociable :**")
            for a in non_negociable:
                lines.append(f"- {a}")
            lines.append("")
        if nice_to_have:
            lines.append("**Nice to have :**")
            for a in nice_to_have:
                lines.append(f"- {a}")
            lines.append("")
    return "\n".join(lines)


def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "besoin"


NOMADIA_EXPERT_NAME = "Marouane Bicher"
NOMADIA_EXPERT_EMAIL = "marouane.bicher@nomadia.com"

_TIER_SELF_SERVICE = {"n1", "n2"}
_TIER_OFFRE_COMPLETE = {"n3"}
_TIER_NO_KEY = {"n4"}
_TIER_UNKNOWN = {"n5"}


def _collect_offre_complete_triggers(state: dict, sections: list) -> list[str]:
    """Labels des choix du client qui correspondent à un mécanisme offre-complète-only
    documenté (sections.json: options[].offre_complete_trigger) — jamais une déduction
    du script sur la BASE du texte libre, seulement sur des choix QCM explicites."""
    triggers = []
    for s in sections:
        sec_state = state["sections"].get(s["id"])
        if sec_state is None:
            continue
        chosen = _selected_option_ids(sec_state)
        for opt in s.get("options", []):
            if opt.get("offre_complete_trigger") and opt["id"] in chosen:
                triggers.append(opt["label"])
    return triggers


def cmd_score(args):
    """Score de complétude : dit si l'entretien a rassemblé tout ce qu'il faut pour
    construire le payload, ET si le niveau d'offre Nomadia confirmé par le client
    (self-service / offre complète / pas encore de clé) correspond à ce que ses
    contraintes citées impliquent réellement. Volontairement simple et vérifiable comme
    le reste du script : compare des id choisis, ne devine jamais un besoin à partir du
    texte libre."""
    sections, threshold = load_sections()
    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    pct = compute_global_percent(state, sections)

    print(f"Entretien {interview_id} — {state.get('title', '(sans titre)')}")
    print("-" * 60)

    if pct < threshold:
        print(f"{c('[INCOMPLET]', 'yellow', 'bold')} Couverture globale {pct}% < seuil {threshold}%.")
        print("     -> Le besoin n'est pas encore assez cadré pour juger du niveau d'offre "
              "nécessaire avec certitude. Continue l'entretien (voir 'progress') avant de "
              "te fier à ce score.")
        print("-" * 60)

    triggers = _collect_offre_complete_triggers(state, sections)
    niveau_state = state["sections"].get("niveau_offre")
    tier_ids = _selected_option_ids(niveau_state) if niveau_state else set()
    has_self_service = bool(tier_ids & _TIER_SELF_SERVICE)
    has_offre_complete = bool(tier_ids & _TIER_OFFRE_COMPLETE)
    no_key_yet = bool(tier_ids & _TIER_NO_KEY)
    tier_unknown = bool(tier_ids & _TIER_UNKNOWN) or not tier_ids

    if triggers:
        print(f"Mécanismes offre-complète-only détectés dans les contraintes citées ({len(triggers)}) :")
        for t in triggers:
            print(f"  - {t}")
    else:
        print("Aucun mécanisme offre-complète-only détecté dans les contraintes citées.")
    print()

    if triggers and has_offre_complete:
        print(f"{c('[OK]', 'green', 'bold')} Cohérent : le client a déjà accès à l'offre complète, "
              "qui couvre ces mécanismes.")
    elif triggers and (has_self_service or no_key_yet or tier_unknown):
        print(f"{c('[OFFRE COMPLETE REQUISE]', 'yellow', 'bold')} Ces mécanismes dépassent le "
              "self-service (voir reference/offre-complete-nomadia.md) — rien de bloquant : "
              "l'offre complète Nomadia les gère. Le client n'a pour l'instant confirmé que "
              "self-service / pas encore de clé / pas clarifié en section niveau_offre.")
        print("     -> NE STOPPE PAS l'entretien pour autant : continue à recueillir le besoin "
              "exactement comme si tu visais l'offre complète (ne réduis jamais le périmètre des "
              "questions à cause du niveau d'offre détecté). Présente ça positivement au client, "
              "jamais comme un blocage : \"ça, on sait le gérer — il te suffira de me mettre en "
              f"contact avec l'équipe Nomadia ({NOMADIA_EXPERT_NAME}, expert Nomadia sur ce "
              f"périmètre — {NOMADIA_EXPERT_EMAIL}).\" Donne toujours ce contact nommément si le "
              "client veut passer par le compte pro, jamais un \"équipe Nomadia\" anonyme. Note-le "
              "dans le PRD (section niveau_offre) pour que ce soit visible au moment de "
              "construire, ou génère directement un message prêt à envoyer avec 'handoff' — voir "
              "reference/regles-entretien.md §7.")
    elif not triggers and has_self_service:
        print(f"{c('[OK]', 'green', 'bold')} Self-service suffit : aucun besoin cité ne dépasse "
              "ce que couvre une clé self-service.")
    elif not triggers and (no_key_yet or tier_unknown):
        print(f"{c('[A CONFIRMER]', 'yellow', 'bold')} Aucun mécanisme offre-complète-only détecté, "
              "mais le niveau d'accès du client (clé API) n'est pas encore confirmé en section "
              "niveau_offre — à clarifier avant le premier appel réel.")
    else:
        print(f"{c('[A CONFIRMER]', 'yellow', 'bold')} Situation pas encore assez claire pour "
              "trancher — reprends la section niveau_offre.")

    print("-" * 60)
    print("Rappel : ce score ne porte QUE sur les mécanismes repérables via les choix QCM de "
          "'contraintes' (stock de pièces, ordre entre jobs, binôme/multi-ressources) — "
          "l'horizon de planification, la disponibilité récurrente et la priorité de rdv "
          "dédiée restent à vérifier toi-même avec le client si pertinent, voir "
          "reference/offre-complete-nomadia.md.")


def cmd_handoff(args):
    """Génère un message prêt à copier-coller pour mettre le client en relation avec
    le contact nommé, dès qu'il confirme vouloir passer par le compte pro/l'offre
    complète — pour ne pas avoir à le rédiger à la main chaque fois. Ce script
    n'ENVOIE jamais rien lui-même : c'est un brouillon à relire/adapter avant envoi,
    jamais un message automatique."""
    sections, _ = load_sections()
    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    title = state.get("title") or "votre besoin"

    triggers = _collect_offre_complete_triggers(state, sections)

    if args.summary:
        need_line = args.summary
    elif triggers:
        need_line = ("votre besoin touche à " + ", ".join(t.lower() for t in triggers) +
                     " — des mécanismes que l'offre self-service ne couvre pas")
    else:
        need_line = f"votre besoin ({title})"

    print(f"{c('[OK]', 'green', 'bold')} Brouillon généré — à relire et adapter avant tout envoi, "
          "ce script n'envoie rien lui-même :\n")
    print("-" * 60)
    print(f"Objet : {title} — mise en relation avec Nomadia\n")
    print("Bonjour,\n")
    print(f"Pour la suite de {need_line}, je vous mets en relation avec notre expert sur ce "
          "périmètre :\n")
    print(f"{NOMADIA_EXPERT_NAME}")
    print("Expert Nomadia")
    print(f"{NOMADIA_EXPERT_EMAIL}\n")
    if triggers:
        print("Il pourra vous accompagner sur l'activation et la configuration de ces points "
              "côté offre complète. On continue en parallèle sur le reste du besoin de notre "
              "côté.\n")
    else:
        print("Il pourra répondre à vos questions sur ce périmètre.\n")
    print("Cordialement,")
    print("-" * 60)
    print(f"\nRappel : {NOMADIA_EXPERT_NAME} est TOUJOURS le contact donné nommément si le "
          "client veut passer par le compte pro — jamais un \"équipe Nomadia\" anonyme (voir "
          "reference/offre-complete-nomadia.md).")


def cmd_prd(args):
    sections, threshold = load_sections()
    interview_id = resolve_interview_id(args)
    state = load_state(interview_id)
    pct = compute_global_percent(state, sections)

    if pct < threshold and not args.force:
        print(f"{c('[ERROR]', 'red', 'bold')} Couverture globale {pct}% < seuil {threshold}%. Le PRD n'est "
              f"généré qu'au-dessus du seuil, SAUF demande explicite de l'utilisateur "
              f"(relancer avec --force dans ce cas précis — jamais par défaut).",
              file=sys.stderr)
        sys.exit(1)

    entities = _parse_entities(args.entity)
    md = render_prd_markdown(state, sections, pct, summary=args.summary, entities=entities)
    out_dir = Path(args.output_dir) if args.output_dir else (SKILL_ROOT / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(state.get("title", "besoin"))
    filename = f"{slug}-PRD-{interview_id}.md"
    out_path = out_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"{c('[OK]', 'green', 'bold')} PRD écrit : {out_path}")
    print(f"     Couverture au moment de la génération : {pct}%"
          + (" (forcé sous le seuil)" if pct < threshold else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="crée un nouvel entretien")
    p_start.add_argument("--title", help="titre provisoire du besoin/client (peut être affiné plus tard)")
    p_start.set_defaults(func=cmd_start)

    p_list = sub.add_parser("list", help="liste tous les entretiens en cours (plusieurs clients en parallèle)")
    p_list.set_defaults(func=cmd_list)

    p_options = sub.add_parser("options", help="affiche le QCM d'une section (options numérotées à poser au client)")
    p_options.add_argument("section", help="id de section (voir reference/sections.json)")
    p_options.add_argument("--interview", help="id de l'entretien (défaut : le plus récent) — sert à filtrer "
                                                 "les options déjà non pertinentes d'après les réponses "
                                                 "précédentes (voir options[].depends_on)")
    p_options.add_argument("--page", type=int, default=1,
                            help=f"partie à afficher si la section a plus de {MAX_CHOICES_PER_SCREEN} "
                                 "choix visibles (défaut : 1) — jamais plus de "
                                 f"{MAX_CHOICES_PER_SCREEN} choix présentés au client en une fois")
    p_options.set_defaults(func=cmd_options)

    p_record = sub.add_parser("record", help="enregistre un tour sur une section")
    p_record.add_argument("section", help="id de section (voir reference/sections.json)")
    p_record.add_argument("answer", nargs="?", default="",
                           help="précision libre du client, en plus de --options (optionnel si "
                                "--options suffit) — jamais inventée")
    p_record.add_argument("--options", default=None,
                           help="id des options choisies par le client (voir 'options <section>'), "
                                "séparés par des virgules — ex. --options e1,e3 — marque "
                                "automatiquement les critères liés. Une seule chaîne (pas "
                                "plusieurs valeurs) pour ne jamais entrer en conflit avec le "
                                "texte libre positionnel, quel que soit l'ordre des arguments.")
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
    p_prd.add_argument("--summary", default=None,
                        help="un ou deux phrases écrites par l'agent, résumant ce qui est "
                             "planifié (quoi/qui) — insérées en tête du PRD sous \"Ce qui "
                             "est planifié\", avant le détail par section. Optionnel.")
    p_prd.add_argument("--entity", action="append", default=None,
                        help="une entité du besoin au format \"Nom|Statut|Description\" "
                             "(répétable, une fois par entité) — ex. --entity \"Techniciens|"
                             "Disponibilité|réalisent les interventions, avec compétences et "
                             "disponibilités variables\". Rendue en liste structurée sous "
                             "\"Ce qui est planifié\", en plus du --summary en texte libre.")
    p_prd.set_defaults(func=cmd_prd)

    p_score = sub.add_parser("score", help="score de complétude : self-service suffit, offre complète "
                                            "nécessaire, ou décalage détecté")
    p_score.add_argument("--interview", help="id de l'entretien (défaut : le plus récent)")
    p_score.set_defaults(func=cmd_score)

    p_handoff = sub.add_parser("handoff", help="génère un message prêt à adapter pour mettre le "
                                                "client en relation avec le contact nommé")
    p_handoff.add_argument("--interview", help="id de l'entretien (défaut : le plus récent)")
    p_handoff.add_argument("--summary", help="recap du besoin en texte libre à insérer dans le "
                                              "message (sinon déduit des mécanismes offre-complète "
                                              "détectés, ou du titre de l'entretien)")
    p_handoff.set_defaults(func=cmd_handoff)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
