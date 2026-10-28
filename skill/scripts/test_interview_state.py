"""
Tests automatisés pour interview_state.py.
Exécuter : python3 skill/scripts/test_interview_state.py
Doit afficher "TOUS LES TESTS PASSENT" et sortir avec le code 0 ; sinon affiche le
détail du test qui échoue et sort avec le code 1.

Pourquoi ce fichier : interview_state.py est le moteur le plus complexe du skill
(filtrage depends_on, pagination groupée dur/souple, score, migration de schéma) et le
plus souvent modifié — sans tests, une régression silencieuse (ex. un KeyError sur un
vieil entretien après une évolution de sections.json, comme ça a été repéré et corrigé
une fois) ne se verrait qu'en situation réelle avec un client, trop tard. Tourne
entièrement EN PROCESS (import direct du module, pas de subprocess) avec STATE_DIR et
SECTIONS_FILE redirigés vers des fichiers temporaires — jamais sur le vrai
.interview_state/ ni sur reference/sections.json, pour ne jamais abîmer un entretien
réel en cours en lançant ces tests.
"""
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import interview_state as ist  # noqa: E402

failures = []


def check(name: str, condition: bool, detail: str = ""):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {name}")
    if not condition:
        failures.append(f"{name}: {detail}")


def run_captured(func, args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        func(args)
    return buf.getvalue()


# --- Mini sections.json de test, volontairement petit mais avec les mêmes mécanismes
#     que le vrai fichier (depends_on, hard, offre_complete_trigger, free text) ---
TEST_SECTIONS = {
    "threshold_percent": 50,
    "sections": [
        {
            "id": "ressources",
            "label": "Ressources",
            "opening_question": "Qui planifies-tu ?",
            "allow_free_text": True,
            "options": [
                {"id": "r1", "label": "Techniciens", "criteria": [0]},
                {"id": "r2", "label": "Véhicules", "criteria": [0]},
            ],
            "criteria": ["Les ressources sont identifiées"],
        },
        {
            "id": "contraintes",
            "label": "Contraintes",
            "opening_question": "Quelles contraintes ?",
            "allow_free_text": True,
            "options": [
                {"id": "c1", "label": "Compétence obligatoire", "criteria": [0], "hard": True},
                {"id": "c2", "label": "Stock de pièces", "criteria": [0], "hard": True,
                 "offre_complete_trigger": True},
                {"id": "c3", "label": "Binôme technicien", "criteria": [0], "hard": True,
                 "depends_on": {"section": "ressources", "any_of": ["r1"]},
                 "offre_complete_trigger": True},
                {"id": "c4", "label": "Regrouper par secteur", "criteria": [1], "hard": False},
            ],
            "criteria": ["Contraintes dures listées", "Contraintes souples listées"],
        },
        {
            "id": "niveau_offre",
            "label": "Niveau d'offre",
            "opening_question": "Quelle clé API ?",
            "allow_free_text": False,
            "options": [
                {"id": "n1", "label": "Clé self-service", "criteria": [0]},
                {"id": "n3", "label": "Offre complète", "criteria": [0]},
            ],
            "criteria": ["Niveau d'offre connu"],
        },
    ],
}


def setup_tmp_env():
    """Redirige STATE_DIR et SECTIONS_FILE du module vers des fichiers temporaires —
    jamais sur les vrais fichiers du skill. Retourne les anciennes valeurs à restaurer."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="nomadia_test_"))
    state_dir = tmp_dir / ".interview_state"
    sections_file = tmp_dir / "sections.json"
    sections_file.write_text(json.dumps(TEST_SECTIONS), encoding="utf-8")

    old_state_dir = ist.STATE_DIR
    old_sections_file = ist.SECTIONS_FILE
    ist.STATE_DIR = state_dir
    ist.SECTIONS_FILE = sections_file
    return old_state_dir, old_sections_file


def teardown_tmp_env(old_state_dir, old_sections_file):
    ist.STATE_DIR = old_state_dir
    ist.SECTIONS_FILE = old_sections_file


old_state_dir, old_sections_file = setup_tmp_env()

try:
    # --- start crée un entretien avec toutes les sections à 0 ---
    out = run_captured(ist.cmd_start, SimpleNamespace(title="Client Test"))
    check("start affiche un id d'entretien", "Entretien créé" in out, out)
    iid = ist.latest_interview_id()
    check("un seul entretien existe après start", iid is not None, "aucun fichier d'état trouvé")

    # --- rien n'est encore couvert : prd doit refuser sous le seuil, et lister les
    #     points à clarifier si on force quand même ---
    try:
        # output_dir n'est jamais atteint tant que le refus sous le seuil est
        # correct (cmd_prd sort avant toute écriture) — valeur bidon volontaire,
        # jamais un chemin dans le repo, pour ne rien écrire même si ce refus
        # venait à régresser silencieusement.
        ist.cmd_prd(SimpleNamespace(interview=iid, force=False, output_dir="/nonexistent/should-not-be-used",
                                     summary=None, entity=None))
        check("prd refuse sous le seuil sans --force", False, "aucune exception levée")
    except SystemExit as e:
        check("prd refuse sous le seuil sans --force", e.code != 0, str(e.code))

    early_out_dir = Path(tempfile.mkdtemp(prefix="nomadia_test_early_"))
    ist.cmd_prd(SimpleNamespace(interview=iid, force=True, output_dir=str(early_out_dir),
                                 summary=None, entity=None))
    early_prd = next(early_out_dir.glob("*.md")).read_text(encoding="utf-8")
    check("prd --force sous le seuil liste les points encore à clarifier",
          "encore à clarifier" in early_prd, early_prd)

    # --- depends_on : c3 (binôme) invisible avant que r1 soit choisi ---
    out = run_captured(ist.cmd_options, SimpleNamespace(section="contraintes", interview=iid, page=1))
    check("c3 (binôme) masqué avant tout choix de ressource", "Binôme technicien" not in out, out)
    check("1 choix masqué signalé", "1 choix non pertinent" in out, out)

    # --- record sur ressources avec r1 (techniciens) ---
    ist.cmd_record(SimpleNamespace(section="ressources", answer="", options="r1",
                                    interview=iid, mark_criterion=None, unmark_criterion=None))

    # --- c3 doit maintenant apparaître ---
    out = run_captured(ist.cmd_options, SimpleNamespace(section="contraintes", interview=iid, page=1))
    check("c3 (binôme) visible après choix d'un technicien (depends_on)", "Binôme technicien" in out, out)

    # --- options avec un --interview explicite mais inexistant doit ÉCHOUER bruyamment,
    #     jamais retomber en silence sur un affichage non filtré ---
    try:
        ist.cmd_options(SimpleNamespace(section="contraintes", interview="ffffff", page=1))
        check("options --interview inexistant échoue (jamais silencieux)", False,
              "aucune exception levée")
    except SystemExit as e:
        check("options --interview inexistant échoue (jamais silencieux)", e.code != 0, str(e.code))

    # --- record contraintes en 2 tours séparés (dures, puis souple) pour vérifier que
    #     le PRD distingue bien "Non négociable" de "Souple" PAR SECTION, pas seulement
    #     dans le récapitulatif global ---
    ist.cmd_record(SimpleNamespace(section="contraintes", answer="", options="c1,c2",
                                    interview=iid, mark_criterion=None, unmark_criterion=None))
    ist.cmd_record(SimpleNamespace(section="contraintes", answer="", options="c4",
                                    interview=iid, mark_criterion=None, unmark_criterion=None))
    state = ist.load_state(iid)
    sections, _ = ist.load_sections()
    pct = ist.compute_global_percent(state, sections)
    check("compute_global_percent avance après un record", pct > 0, f"pct={pct}")

    # --- score : c2 (offre_complete_trigger) détecté, niveau_offre pas encore répondu ---
    out = run_captured(ist.cmd_score, SimpleNamespace(interview=iid))
    check("score détecte le trigger offre complète (stock de pièces)", "Stock de pièces" in out, out)
    check("score signale OFFRE COMPLETE REQUISE sans niveau_offre confirmé",
          "OFFRE COMPLETE REQUISE" in out, out)

    # --- handoff reprend le trigger détecté et le contact nommé ---
    out = run_captured(ist.cmd_handoff, SimpleNamespace(interview=iid, summary=None))
    check("handoff cite le contact nommé", ist.NOMADIA_EXPERT_EMAIL in out, out)
    check("handoff cite le mécanisme détecté", "stock de pièces" in out.lower(), out)

    # --- confirme niveau_offre en self-service -> score doit changer de verdict ---
    ist.cmd_record(SimpleNamespace(section="niveau_offre", answer="", options="n1",
                                    interview=iid, mark_criterion=None, unmark_criterion=None))
    out = run_captured(ist.cmd_score, SimpleNamespace(interview=iid))
    check("score toujours OFFRE COMPLETE REQUISE avec self-service confirmé (c2 dépasse)",
          "OFFRE COMPLETE REQUISE" in out, out)

    # --- une fois tout couvert, prd (au-dessus du seuil, pas besoin de --force) reflète
    #     bien les réponses et distingue dur/souple PAR SECTION (2 tours séparés
    #     ci-dessus) en plus du récapitulatif global ---
    out_dir = Path(tempfile.mkdtemp(prefix="nomadia_test_out_"))
    ist.cmd_prd(SimpleNamespace(interview=iid, force=False, output_dir=str(out_dir),
                                 summary="Test résumé", entity=None))
    prd_files = list(out_dir.glob("*.md"))
    check("prd écrit un fichier une fois au-dessus du seuil", len(prd_files) == 1, str(prd_files))
    if prd_files:
        content = prd_files[0].read_text(encoding="utf-8")
        check("prd contient le résumé libre", "Test résumé" in content, content[:200])
        check("prd distingue non négociable / souple PAR SECTION (tours séparés)",
              "**Non négociable :**" in content and "**Souple (arbitrable) :**" in content, content)
        check("prd distingue aussi non négociable / nice to have dans le récapitulatif global",
              "## Récapitulatif global" in content and "Nice to have" in content, content)

    # --- list affiche l'entretien créé ---
    out = run_captured(ist.cmd_list, SimpleNamespace())
    check("list affiche le titre de l'entretien", "Client Test" in out, out)
    check("list affiche l'id de l'entretien", iid in out, out)

    # --- MIGRATION : simule un entretien démarré avant une évolution de sections.json
    #     (section manquante + total_criteria désynchronisé) et vérifie l'auto-réparation ---
    old_state_raw = {
        "interview_id": "legacy1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "title": "Vieil entretien",
        "sections": {
            "ressources": {
                # total_criteria désynchronisé (vrai = 1, len(criteria) de la section
                # de test) + covered_criteria contenant l'index 2, qui n'existe PAS
                # pour une section à 1 seul critère (seul l'index 0 est valide) —
                # simule une section raccourcie depuis que ce vieil entretien a démarré.
                "label": "Ressources", "turns": [], "covered_criteria": [2], "total_criteria": 3,
            },
            # 'contraintes' et 'niveau_offre' totalement absents de ce vieil état
        },
    }
    ist.save_state(old_state_raw)
    migrated = ist.load_state("legacy1")  # ne doit JAMAIS lever de KeyError
    check("migration ajoute les sections manquantes", "contraintes" in migrated["sections"]
          and "niveau_offre" in migrated["sections"], json.dumps(migrated["sections"], ensure_ascii=False))
    check("migration réaligne total_criteria désynchronisé",
          migrated["sections"]["ressources"]["total_criteria"] == 1,
          migrated["sections"]["ressources"])
    check("migration retire les indices de critère hors limites (2 invalide pour 1 critère)",
          migrated["sections"]["ressources"]["covered_criteria"] == [],
          migrated["sections"]["ressources"]["covered_criteria"])
    # compute_global_percent et progress ne doivent plus planter sur cet entretien migré
    pct = ist.compute_global_percent(migrated, sections)
    check("compute_global_percent fonctionne sur un entretien migré", isinstance(pct, float), pct)
    out = run_captured(ist.cmd_progress, SimpleNamespace(interview="legacy1", verbose=False))
    check("progress fonctionne sur un entretien migré (plus de KeyError)",
          "Vieil entretien" in out, out)
    out = run_captured(ist.cmd_list, SimpleNamespace())
    check("list fonctionne même avec un entretien migré dans le lot", "Vieil entretien" in out, out)

    # --- new_interview_id : jamais un id qui collide avec un fichier déjà présent ---
    taken = ist.latest_interview_id()
    ist.state_path(taken)  # juste pour s'assurer qu'il existe déjà
    new_id = ist.new_interview_id()
    check("new_interview_id ne réutilise jamais un id déjà pris",
          not ist.state_path(new_id).exists(), new_id)

finally:
    teardown_tmp_env(old_state_dir, old_sections_file)

print()
if failures:
    print(f"ÉCHEC — {len(failures)} test(s) en erreur :")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("TOUS LES TESTS PASSENT")
