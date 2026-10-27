#!/usr/bin/env python3
"""
Comparateur de scénarios — exécutable en CLI, sans dépendance (urllib natif).

Pourquoi ce script : les solveurs "scientifiques" généralistes vendent souvent le
benchmarking/l'analyse de score comme fonctionnalité avancée (souvent payante en
édition Enterprise). Le Scheduler API de Nomadia n'expose pas de score détaillé par
contrainte, mais on peut obtenir le même type de preuve empirique en comparant
plusieurs variantes d'un même payload (ex : avec/sans shift_penalty, avec/sans
locality) sur les mêmes jobs/ressources — avant/après chiffré, pas juste une promesse.

Deux modes :
  1. Sans clé API : comparaison statique de configuration (diff des leviers ROI entre
     scénarios, via recommend_improvements.py) — gratuit, zéro crédit consommé.
  2. Avec clé API : appelle réellement /api/schedule pour chaque scénario et compare
     taux d'allocation, distance totale parcourue, coût en crédits. CONSOMME DES
     CRÉDITS RÉELS (un appel par scénario) — à n'utiliser qu'avec l'accord explicite de
     l'utilisateur, jamais en boucle automatique.

Usage :
    python3 scripts/compare_scenarios.py --scenario "Baseline" payload_a.json --scenario "Avec shift_penalty" payload_b.json
    python3 scripts/compare_scenarios.py --scenario "Baseline" payload_a.json --scenario "V2" payload_b.json --api-key "$NOMADIA_API_KEY"

Sécurité : ne jamais écrire une clé API en dur dans un fichier. Passer --api-key en
argument de commande ou définir la variable d'environnement NOMADIA_API_KEY — ce script
ne l'imprime ni ne la journalise jamais.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recommend_improvements import recommend_from_payload  # noqa: E402

# Deux environnements distincts (confirmés par Nomadia le 23/10/2026, versions non
# définitives à cette date) : TEST = scheduler-api-test.nomadia-app.com (actif),
# PROD = scheduler-api.nomadia-app.com (PAS ENCORE ACTIF à cette date). Test par
# défaut — surchargeable via NOMADIA_BASE_URL.
BASE_URL = os.environ.get("NOMADIA_BASE_URL", "https://scheduler-api-test.nomadia-app.com")

_env_announced = False


def _announce_env():
    """Affiche une fois par process quel environnement (test/prod) est ciblé — pour
    qu'un vrai appel API ne passe jamais inaperçu sur le mauvais environnement."""
    global _env_announced
    if _env_announced:
        return
    _env_announced = True
    if "-test" in BASE_URL:
        print(f"[INFO] Appel vers l'environnement de TEST Nomadia ({BASE_URL}) — pas la "
              f"prod. Pour basculer sur la prod une fois confirmée active, définir "
              f"NOMADIA_BASE_URL=https://scheduler-api.nomadia-app.com avant d'exécuter.")
    else:
        print(f"[ATTENTION] Appel vers {BASE_URL} — vérifie que c'est bien l'environnement "
              f"de PRODUCTION voulu et non le test (impact réel : données, crédits, "
              f"abonnement actif requis).")


_ERROR_HINTS = {
    400: "requête invalide — vérifie les id référencés et le format des dates/durées",
    401: "clé API manquante, invalide ou bloquée",
    402: "solde de crédits négatif",
    403: "période d'essai terminée — un abonnement est requis",
}


def call_schedule(api_key: str, payload: dict) -> dict:
    _announce_env()
    req = urllib.request.Request(
        f"{BASE_URL}/api/schedule",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        hint = _ERROR_HINTS.get(e.code, "erreur inattendue")
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} ({hint}) : {body[:300]}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"réseau : {e.reason}") from None


def estimate_credits(payload: dict, response: dict) -> int:
    nb_resources = len(payload.get("resources", []))
    nb_planned_jobs = len({a.get("job_id") for a in response.get("allocations", [])})
    return 5 + nb_resources * nb_planned_jobs


def analyze_live(label: str, payload_path: str, api_key: str) -> dict:
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
    response = call_schedule(api_key, payload)
    allocations = response.get("allocations", [])
    unallocated = response.get("unallocated_job_reasons", [])
    travels = response.get("travels", [])
    total_distance_km = sum(t.get("distance_in_metres", 0) for t in travels) / 1000
    return {
        "label": label,
        "jobs": len(payload.get("jobs", [])),
        "allocated": len({a.get("job_id") for a in allocations}),
        "unallocated": len(unallocated),
        "distance_km": round(total_distance_km, 1),
        "credits": estimate_credits(payload, response),
    }


def analyze_static(label: str, payload_path: str) -> dict:
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
    recs = recommend_from_payload(payload)
    high = sum(1 for r in recs if r["priority"] == "HIGH")
    medium = sum(1 for r in recs if r["priority"] == "MEDIUM")
    low = sum(1 for r in recs if r["priority"] == "LOW")
    return {
        "label": label,
        "jobs": len(payload.get("jobs", [])),
        "resources": len(payload.get("resources", [])),
        "reco_high": high,
        "reco_medium": medium,
        "reco_low": low,
    }


def print_live_table(rows: list[dict]):
    print(f"{'Scénario':<28} {'Jobs':>6} {'Alloués':>8} {'Non all.':>9} {'Distance (km)':>14} {'Crédits':>8}")
    for r in rows:
        print(f"{r['label']:<28} {r['jobs']:>6} {r['allocated']:>8} {r['unallocated']:>9} "
              f"{r['distance_km']:>14} {r['credits']:>8}")
    if len(rows) >= 2:
        base, last = rows[0], rows[-1]
        if base["jobs"]:
            delta_alloc = last["allocated"] - base["allocated"]
            delta_dist = last["distance_km"] - base["distance_km"]
            print(f"\nDelta '{base['label']}' -> '{last['label']}' : "
                  f"{delta_alloc:+d} job(s) alloué(s), {delta_dist:+.1f} km de trajet total")


def print_static_table(rows: list[dict]):
    print(f"{'Scénario':<28} {'Jobs':>6} {'Ressources':>11} {'HIGH':>5} {'MEDIUM':>7} {'LOW':>5}")
    for r in rows:
        print(f"{r['label']:<28} {r['jobs']:>6} {r['resources']:>11} "
              f"{r['reco_high']:>5} {r['reco_medium']:>7} {r['reco_low']:>5}")
    print("\n(mode sans clé API — comparaison de configuration uniquement, aucun crédit "
          "consommé. Relancer avec --api-key pour un avant/après chiffré sur le vrai "
          "résultat de planification.)")


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--scenario", nargs=2, action="append", metavar=("LABEL", "PAYLOAD_PATH"),
                         required=True, help="répétable : un label + un fichier payload par scénario")
    parser.add_argument("--api-key", default=os.environ.get("NOMADIA_API_KEY"),
                         help="clé API Nomadia (ou variable d'env NOMADIA_API_KEY) — jamais en dur dans un fichier")
    args = parser.parse_args()

    if len(args.scenario) < 2:
        print("[ERROR] fournis au moins 2 scénarios (--scenario LABEL PAYLOAD.json) pour comparer")
        sys.exit(1)

    if args.api_key:
        rows = []
        for label, path in args.scenario:
            try:
                rows.append(analyze_live(label, path, args.api_key))
            except RuntimeError as e:
                print(f"[ERROR] scénario '{label}' : {e}")
                sys.exit(1)
        print_live_table(rows)
    else:
        rows = [analyze_static(label, path) for label, path in args.scenario]
        print_static_table(rows)

    sys.exit(0)


if __name__ == "__main__":
    main()
