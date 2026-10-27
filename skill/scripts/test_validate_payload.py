"""
Tests automatisés pour validate_payload.py.
Exécuter : python3 skill/scripts/test_validate_payload.py
Doit afficher "TOUS LES TESTS PASSENT" et sortir avec le code 0 ; sinon affiche le
détail du test qui échoue et sort avec le code 1.

Pourquoi ce fichier : un skill qui modifie son propre validateur sans test risque de
réintroduire silencieusement un faux positif/négatif (c'est déjà arrivé une fois avec
l'heuristique lat/lng — voir CHANGELOG.md 1.2). Ce fichier fige le comportement attendu.

Depuis la réécriture du 27/10/2026 sur le vrai schéma self-service (voir
reference/entities.md), 3 des 10 exemples (03, 04, 10) ne sont PAS des payloads
self-service valides : ils documentent des mécanismes de l'offre complète Nomadia qui
n'existent pas en self-service (reference/offre-complete-nomadia.md), et sont
volontairement incomplets (pas de locations/resources, etc.) puisqu'ils ne sont là que
pour montrer la forme du payload côté offre complète. Le validateur les laisse passer
en exit 0 avec des [WARN] (il ne les rejette jamais en [ERROR], puisque l'API
elle-même ne les rejette pas — elle les ignore silencieusement), mais ils sont exclus
de la boucle "tous les exemples doivent être des payloads self-service complets".
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VALIDATOR = SKILL_DIR / "scripts" / "validate_payload.py"
EXAMPLES_DIR = SKILL_DIR / "examples"

# Exemples qui documentent l'offre complète (pas d'équivalent self-service) —
# volontairement incomplets, exclus de la boucle de validation complète ci-dessous.
OFFRE_COMPLETE_ONLY_EXAMPLES = {
    "03_stock_pieces.json",
    "04_ordre_entre_jobs.json",
    "10_job_multi_ressources.json",
}


def run_validator(payload: dict) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "-"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def load_minimal() -> dict:
    with open(EXAMPLES_DIR / "01_minimal.json") as f:
        return json.load(f)


failures = []


def check(name: str, condition: bool, detail: str = ""):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {name}")
    if not condition:
        failures.append(f"{name}: {detail}")


# --- Les exemples self-service doivent tous passer sans erreur bloquante ---
for example_file in sorted(EXAMPLES_DIR.glob("*.json")):
    if example_file.name in OFFRE_COMPLETE_ONLY_EXAMPLES:
        continue
    with open(example_file) as f:
        payload = json.load(f)
    code, output = run_validator(payload)
    check(f"exemple {example_file.name} valide (exit 0)", code == 0, output)

# --- Les exemples offre-complète-only doivent au moins rester du JSON valide et ne
#     jamais planter le validateur (exit 0 ou 1 tous deux acceptables selon ce qu'ils
#     contiennent, mais pas de crash) ---
for name in OFFRE_COMPLETE_ONLY_EXAMPLES:
    with open(EXAMPLES_DIR / name) as f:
        payload = json.load(f)
    code, output = run_validator(payload)
    check(f"exemple {name} ne fait pas planter le validateur", code in (0, 1), output)

# --- location_id orpheline doit être détectée ---
payload = load_minimal()
payload["jobs"][0]["location_id"] = "LOC-INEXISTANTE"
code, output = run_validator(payload)
check("location_id orpheline détectée (exit 1)", code == 1, output)
check("message mentionne location_id", "location_id" in output, output)

# --- job_type_id orpheline doit être détectée ---
payload = load_minimal()
payload["jobs"][0]["job_type_id"] = "TYPE-INEXISTANT"
code, output = run_validator(payload)
check("job_type_id orpheline détectée (exit 1)", code == 1, output)

# --- durée ISO 8601 invalide doit être détectée ---
payload = load_minimal()
payload["jobs"][0]["custom_duration"] = "30min"
code, output = run_validator(payload)
check("durée ISO 8601 invalide détectée (exit 1)", code == 1, output)

# --- shift start >= end doit être détecté ---
payload = load_minimal()
shift = payload["resources"][0]["shifts"][0]
shift["start_date_time"], shift["end_date_time"] = shift["end_date_time"], shift["start_date_time"]
code, output = run_validator(payload)
check("shift start>=end détecté (exit 1)", code == 1, output)

# --- coordonnées lat/lng légitimes (Paris) ne doivent PAS déclencher d'erreur ---
# Régression du bug corrigé en 1.2 : l'ancienne heuristique "ordre lat/lng" donnait
# un faux positif sur des coordonnées parisiennes correctes.
payload = load_minimal()
for loc in payload.get("locations", []):
    loc["latitude"] = 48.8566
    loc["longitude"] = 2.3522
code, output = run_validator(payload)
check(
    "coordonnées Paris légitimes n'émettent pas d'erreur (exit 0)",
    code == 0,
    output,
)

# --- lat hors plage doit être détectée ---
payload = load_minimal()
payload["locations"][0]["latitude"] = 95.0
code, output = run_validator(payload)
check("latitude hors plage détectée (exit 1)", code == 1, output)

# --- lng hors plage doit être détectée ---
payload = load_minimal()
payload["locations"][0]["longitude"] = 200.0
code, output = run_validator(payload)
check("longitude hors plage détectée (exit 1)", code == 1, output)

# --- requirements en objets (ancien format offre complète) doit être détecté comme
#     erreur plutôt que silencieusement accepté : le schéma self-service réel exige
#     une liste de chaînes simples ---
payload = load_minimal()
payload["jobs"][0]["requirements"] = [{"id": "HABILITATION_ELEC"}]
code, output = run_validator(payload)
check("requirements sous forme d'objets détecté (exit 1)", code == 1, output)

# --- requirements sous forme de chaînes simples ne doit PAS déclencher d'erreur ---
payload = load_minimal()
payload["jobs"][0]["requirements"] = ["HABILITATION_ELEC"]
code, output = run_validator(payload)
check("requirements sous forme de chaînes accepté (exit 0)", code == 0, output)

# --- fixed_resource_id orphelin doit être détecté ---
payload = load_minimal()
payload["jobs"][0]["fixed_resource_id"] = "RES-FANTOME"
code, output = run_validator(payload)
check("fixed_resource_id orphelin détecté (exit 1)", code == 1, output)

# --- unavailability imbriquée (resource.unavailabilities[]) avec start>=end détectée ---
payload = load_minimal()
payload["resources"][0]["unavailabilities"] = [
    {"id": "INDISPO-1", "start_date_time": "2026-11-02T15:00:00", "end_date_time": "2026-11-02T14:00:00"}
]
code, output = run_validator(payload)
check("unavailability imbriquée start>=end détectée (exit 1)", code == 1, output)

# --- un payload avec un champ de l'offre complète au niveau racine (job_resources)
#     doit déclencher un WARN fort, mais rester exit 0 puisque l'API elle-même ne le
#     rejette pas (elle l'ignore silencieusement) ---
payload = load_minimal()
payload["job_resources"] = [{"job_id": "JOB-1", "resource_index": 1}]
code, output = run_validator(payload)
check("job_resources (offre complète) déclenche un WARN, pas une erreur (exit 0)", code == 0, output)
check("le WARN mentionne job_resources", "job_resources" in output and "WARN" in output, output)

print()
if failures:
    print(f"ÉCHEC — {len(failures)} test(s) en erreur :")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("TOUS LES TESTS PASSENT")
    sys.exit(0)
