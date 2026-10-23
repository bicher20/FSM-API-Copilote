"""
Tests automatisés pour validate_payload.py.
Exécuter : python3 skill/scripts/test_validate_payload.py
Doit afficher "TOUS LES TESTS PASSENT" et sortir avec le code 0 ; sinon affiche le
détail du test qui échoue et sort avec le code 1.

Pourquoi ce fichier : un skill qui modifie son propre validateur sans test risque de
réintroduire silencieusement un faux positif/négatif (c'est déjà arrivé une fois avec
l'heuristique lat/lng — voir CHANGELOG.md 1.2). Ce fichier fige le comportement attendu.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VALIDATOR = SKILL_DIR / "scripts" / "validate_payload.py"
EXAMPLES_DIR = SKILL_DIR / "examples"


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


# --- Les 5 exemples doivent tous passer sans erreur ---
for example_file in sorted(EXAMPLES_DIR.glob("*.json")):
    with open(example_file) as f:
        payload = json.load(f)
    code, output = run_validator(payload)
    check(f"exemple {example_file.name} valide (exit 0)", code == 0, output)

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

# --- shift sans id ne doit être qu'un WARN, jamais bloquant (cf. quick start officiel) ---
payload = load_minimal()
del payload["resources"][0]["shifts"][0]["id"]
code, output = run_validator(payload)
check("shift sans id = WARN seulement, pas bloquant (exit 0)", code == 0, output)
check("message mentionne l'absence d'id de shift", "id" in output and "WARN" in output, output)

# --- pre_requisite_definition avec job inexistant doit être détecté ---
with open(EXAMPLES_DIR / "04_ordre_entre_jobs.json") as f:
    payload = json.load(f)
payload["pre_requisite_definitions"][0]["later_job_id"] = "JOB-FANTOME"
code, output = run_validator(payload)
check("pre_requisite_definition avec job inexistant détecté (exit 1)", code == 1, output)

# --- job_resource.commit_date_time_stamp sans fixed_resource_id doit être détecté ---
with open(EXAMPLES_DIR / "06_ressource_engagee.json") as f:
    payload = json.load(f)
del payload["job_resources"][0]["fixed_resource_id"]
code, output = run_validator(payload)
check("commit_date_time_stamp sans fixed_resource_id détecté (exit 1)", code == 1, output)

# --- resource_unavailability avec resource_id inexistant doit être détecté ---
with open(EXAMPLES_DIR / "08_indisponibilite_ressource.json") as f:
    payload = json.load(f)
payload["resource_unavailabilities"][0]["resource_id"] = "RES-FANTOME"
code, output = run_validator(payload)
check("resource_unavailability avec resource_id inexistant détecté (exit 1)", code == 1, output)

# --- les 10 exemples doivent rester valides avec le validateur étendu ---
# (déjà couvert par la boucle "exemple ... valide" ci-dessus sur tout examples/*.json)

print()
if failures:
    print(f"ÉCHEC — {len(failures)} test(s) en erreur :")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("TOUS LES TESTS PASSENT")
    sys.exit(0)
