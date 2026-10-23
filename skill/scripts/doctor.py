#!/usr/bin/env python3
"""
Doctor — point d'entrée unique du skill, exécutable en CLI, sans dépendance.

Pourquoi ce script : Timefold (et les solveurs généralistes en général) demandent
d'écrire du code Java/Kotlin pour obtenir le moindre diagnostic sur un plan. Ici, une
seule commande suffit pour tout faire sur un payload Nomadia : valider, diagnostiquer,
recommander — pas besoin de connaître les trois scripts séparés
(validate_payload.py / recommend_improvements.py / compare_scenarios.py) ni leur ordre.

Usage :
    python3 scripts/doctor.py payload.json
    python3 scripts/doctor.py payload.json --response reponse.json

Comportement :
    1. Valide le payload (validate_payload.py). S'il y a des [ERROR], s'arrête ici et
       sort avec le code 1 — inutile de recommander quoi que ce soit sur un payload
       structurellement cassé.
    2. Si le payload est valide (0 erreur bloquante), lance les recommandations ROI
       (recommend_improvements.py), sur la config seule et, si --response est fourni,
       sur le vrai résultat de l'appel API.
    3. Sortie unique, lisible, dans l'ordre : d'abord ce qui bloque, puis ce qui est à
       vérifier, puis ce qui pourrait être amélioré.

Exit code : 0 si le payload est valide (avec ou sans recommandations), 1 si le payload
a des erreurs bloquantes.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_payload import validate  # noqa: E402
from recommend_improvements import recommend_from_payload, recommend_from_response, print_recs  # noqa: E402


def load_json(path: str) -> dict:
    src = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    try:
        return json.loads(src)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON invalide dans {path} : {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    payload_path = sys.argv[1]
    response_path = None
    if "--response" in sys.argv:
        response_path = sys.argv[sys.argv.index("--response") + 1]

    payload = load_json(payload_path)

    print("=== 1/2 — Validation structurelle ===\n")
    errors, warnings = validate(payload)
    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[ERROR] {e}")

    if errors:
        print(f"\n{len(errors)} erreur(s) bloquante(s). Corrige le payload avant de "
              f"continuer — pas la peine de chercher des optimisations sur une base "
              f"structurellement cassée.")
        print("\n❌ VERDICT : à corriger avant tout appel réel.")
        sys.exit(1)

    print("\nPas d'erreur bloquante" + (f" — {len(warnings)} avertissement(s) ci-dessus à vérifier." if warnings else "."))

    print("\n=== 2/2 — Recommandations ROI ===\n")
    recs = recommend_from_payload(payload)
    if response_path:
        response = load_json(response_path)
        recs += recommend_from_response(response, payload)
    print_recs(recs)

    nb_high = sum(1 for r in recs if r["priority"] == "HIGH")
    if nb_high:
        print(f"✅ VERDICT : payload valide, mais {nb_high} recommandation(s) [HIGH] "
              f"ci-dessus méritent d'être traitées avant de considérer le résultat fiable.")
    elif recs:
        print("✅ VERDICT : payload valide et prêt pour un appel réel — quelques "
              "améliorations [MEDIUM]/[LOW] facultatives ci-dessus.")
    else:
        print("✅ VERDICT : payload valide, aucune recommandation — prêt pour un appel réel.")

    sys.exit(0)


if __name__ == "__main__":
    main()
