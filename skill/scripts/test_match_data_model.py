"""
Tests automatisés pour match_data_model.py.
Exécuter : python3 skill/scripts/test_match_data_model.py
Doit afficher "TOUS LES TESTS PASSENT" et sortir avec le code 0 ; sinon affiche le
détail du test qui échoue et sort avec le code 1.

Pourquoi ce fichier : le rapprochement de champs a déjà régressé silencieusement deux
fois (voir CHANGELOG.md 1.36 — faux positifs par sous-chaîne, lacune de vocabulaire).
Ce fichier fige le comportement attendu sur un corpus mixte FR/EN/camelCase
(fixtures/corpus_fsm_generique.json), notamment la découpe camelCase introduite pour
que 'disponibiliteRessource' ne soit plus traité comme un seul token illisible.
"""
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from match_data_model import _normalize, _split_camel_case, match_fields  # noqa: E402

FIXTURES_DIR = SKILL_DIR / "scripts" / "fixtures"

failures = []


def check(name: str, condition: bool, detail: str = ""):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {name}")
    if not condition:
        failures.append(f"{name}: {detail}")


def best_match(results: list[dict], field: str) -> dict | None:
    return next((r for r in results if r["champ_client"] == field), None)


# --- _split_camel_case doit insérer un '_' à chaque frontière minuscule->majuscule,
#     sans toucher au reste (c'est à _normalize de passer en minuscule après) ---
check(
    "_split_camel_case découpe une frontière simple",
    _split_camel_case("disponibiliteRessource") == "disponibilite_Ressource",
    _split_camel_case("disponibiliteRessource"),
)
check(
    "_split_camel_case découpe plusieurs frontières",
    _split_camel_case("planningHebdomadaireTechnicien") == "planning_Hebdomadaire_Technicien",
    _split_camel_case("planningHebdomadaireTechnicien"),
)
check(
    "_split_camel_case laisse un champ snake_case inchangé",
    _split_camel_case("type_intervention") == "type_intervention",
    _split_camel_case("type_intervention"),
)
check(
    "_split_camel_case laisse un champ déjà en minuscules inchangé",
    _split_camel_case("interventionid") == "interventionid",
    _split_camel_case("interventionid"),
)

# --- régression : la découpe camelCase doit avoir lieu AVANT _normalize (sinon la
#     casse est perdue et la frontière ne peut plus être détectée) ---
check(
    "_normalize seul ne découpe pas le camelCase (ordre des opérations)",
    _normalize("disponibiliteRessource") == "disponibiliteressource",
    _normalize("disponibiliteRessource"),
)

# --- corpus mixte FR/EN/camelCase : les champs camelCase doivent matcher comme leur
#     équivalent snake_case, pas finir en "aucune correspondance fiable" ---
with open(FIXTURES_DIR / "corpus_fsm_generique.json") as f:
    corpus = json.load(f)

results = match_fields(corpus)

for field, expected_entity in {
    "disponibiliteRessource": "Resource",
    "planningHebdomadaire": "Resource.shifts",
    "contactTelephoneSite": "Location",
}.items():
    r = best_match(results, field)
    check(
        f"'{field}' (camelCase) matche {expected_entity}",
        r is not None
        and r["confiance"] != "aucune"
        and r["correspondance_nomadia"] is not None
        and r["correspondance_nomadia"].startswith(expected_entity),
        r,
    )

# --- un champ réellement hors vocabulaire ('clientNomSociete' — "nom de société"
#     n'est pas un terme FSM standard) doit rester sans correspondance fiable : la
#     découpe camelCase ne doit pas se mettre à inventer des faux positifs ---
r = best_match(results, "clientNomSociete")
check(
    "'clientNomSociete' reste sans correspondance fiable (pas de faux positif)",
    r is not None and r["confiance"] == "aucune",
    r,
)

print()
if failures:
    print(f"ÉCHEC — {len(failures)} test(s) en erreur :")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("TOUS LES TESTS PASSENT")
    sys.exit(0)
