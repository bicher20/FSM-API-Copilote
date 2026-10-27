#!/usr/bin/env python3
"""
Générateur de payload de charge — exécutable en CLI, sans dépendance.

Génère un payload Scheduler API self-service réaliste à grande échelle (N jobs, M
ressources), pour challenger l'API sur le volume plutôt que sur un seul mécanisme à la
fois. Combine, à l'échelle, les mécanismes self-service confirmés dans
reference/entities.md : requirements (compétence sur une partie des jobs/ressources),
locality (jobs répartis en secteurs géographiques), SLA avec value_per_hour explicite
(voir troubleshooting.md §3bis — sans ça, le SLA n'est pas fiable), appointment_sla sur
une partie des jobs, fixed_resource_id sur quelques jobs, pauses, shift_penalty,
maximum_jobs_per_shift.

⚠️ COÛT : d'après SKILL.md, un appel schedule coûte 5 + (nb_ressources du payload ×
nb_jobs planifiés) crédits. Ce script affiche une estimation AVANT de rien envoyer —
ce script ne fait aucun appel réel, il écrit juste un fichier JSON local. Toujours
lancer scripts/doctor.py sur le résultat (gratuit) avant d'envisager un appel réel, et
ne jamais lancer l'appel sans avoir accepté explicitement le coût estimé.

Usage :
    python3 scripts/generate_load_test.py --jobs 100 --resources 10 -o payload.json
    python3 scripts/generate_load_test.py --jobs 100 --resources 10 --seed 42 -o payload.json

Options :
    --jobs N        nombre d'interventions à générer (défaut 100)
    --resources M   nombre de ressources à générer (défaut 10)
    --seed S        graine aléatoire, pour un résultat reproductible (défaut 42)
    -o FICHIER      fichier de sortie (défaut stdout)
"""
import argparse
import json
import random
import sys


LOCALITIES = ["NORD", "SUD", "EST", "OUEST", "CENTRE"]
# Centres approximatifs (lat, lng) pour répartir les locations par secteur autour de
# Paris, avec un peu de bruit pour que ça ressemble à un vrai secteur géographique.
LOCALITY_CENTERS = {
    "NORD": (48.90, 2.35),
    "SUD": (48.81, 2.35),
    "EST": (48.856, 2.42),
    "OUEST": (48.856, 2.28),
    "CENTRE": (48.8566, 2.3522),
}
DEPOT = {"id": "DEPOT", "latitude": 48.8566, "longitude": 2.3522}


def build_payload(n_jobs: int, n_resources: int, seed: int) -> dict:
    rng = random.Random(seed)

    locations = [DEPOT]
    for i in range(1, n_jobs + 1):
        locality = LOCALITIES[i % len(LOCALITIES)]
        base_lat, base_lng = LOCALITY_CENTERS[locality]
        locations.append({
            "id": f"LOC-{i}",
            "latitude": round(base_lat + rng.uniform(-0.02, 0.02), 4),
            "longitude": round(base_lng + rng.uniform(-0.02, 0.02), 4),
            "locality": locality,
        })

    job_types = [
        {"id": "DEFAULT", "custom_duration": "PT30M"},
        {"id": "INSTALLATION", "custom_duration": "PT1H"},
    ]

    resource_types = [
        {
            "id": "TECH_STD",
            "start_location_id": "DEPOT",
            "end_location_id": "DEPOT",
            "cost_per_kilometre": 0.4,
            "cost_per_hour": 15,
            "shift_penalty": 50,
            "maximum_jobs_per_shift": 15,
        },
        {
            "id": "TECH_ELEC",
            "start_location_id": "DEPOT",
            "end_location_id": "DEPOT",
            "cost_per_kilometre": 0.5,
            "cost_per_hour": 20,
            "shift_penalty": 50,
            "maximum_jobs_per_shift": 15,
        },
    ]

    # ~30% des ressources sont habilitées électricité, le reste standard.
    resources = []
    n_elec_resources = max(1, round(n_resources * 0.3))
    for i in range(1, n_resources + 1):
        is_elec = i <= n_elec_resources
        shift = {
            "start_date_time": "2026-11-02T08:00:00",
            "end_date_time": "2026-11-02T18:00:00",
            "breaks": [
                {
                    "earliest_start_date_time": "2026-11-02T12:00:00",
                    "latest_start_date_time": "2026-11-02T13:30:00",
                    "duration": "PT45M",
                }
            ],
        }
        resource = {
            "id": f"RES-{i}",
            "resource_type_id": "TECH_ELEC" if is_elec else "TECH_STD",
            "shifts": [shift],
        }
        if is_elec:
            resource["requirements"] = ["HABILITATION_ELEC"]
        resources.append(resource)

    # ~20% des jobs exigent l'habilitation électrique (donc doivent être couverts par
    # les ressources habilitées ci-dessus), ~10% ont un rendez-vous serré
    # (appointment_sla), un job sur 25 est engagé d'office sur une ressource précise
    # (fixed_resource_id), pour exercer plusieurs mécanismes en même temps à l'échelle.
    jobs = []
    for i in range(1, n_jobs + 1):
        requires_elec = (i % 5 == 0)  # 20%
        has_appointment = (i % 10 == 0)  # 10%
        is_fixed = (i % 25 == 0) and n_resources > 0  # ~4%
        job_type_id = "INSTALLATION" if requires_elec else "DEFAULT"

        job = {
            "id": f"JOB-{i}",
            "job_type_id": job_type_id,
            "location_id": f"LOC-{i}",
            # Leçon apprise le 27/10/2026 (troubleshooting.md §3bis) : value_per_hour
            # n'a pas de défaut fiable côté self-service — toujours le fixer
            # explicitement, surtout sur un job avec une pénalité SLA/rendez-vous.
            "value_per_hour": 200 if has_appointment else 50,
            "sla": {
                "earliest_start_date_time": "2026-11-02T08:00:00",
                "latest_start_date_time": "2026-11-02T18:00:00",
                "penalty_per_hour": 5,
            },
        }
        if requires_elec:
            job["requirements"] = ["HABILITATION_ELEC"]
        if has_appointment:
            # Fenêtre de rendez-vous de 30 min, répartie entre 9h et 17h selon le job.
            hour = 9 + (i // 10) % 8
            job["appointment_sla"] = {
                "earliest_start_date_time": f"2026-11-02T{hour:02d}:00:00",
                "latest_start_date_time": f"2026-11-02T{hour:02d}:30:00",
                "penalty_per_hour": 50,
                "base_jeopardy_penalty": 1000,
            }
        if is_fixed:
            job["fixed_resource_id"] = f"RES-{(i % n_resources) + 1}"
        jobs.append(job)

    return {
        "_comment": (
            f"Payload de charge généré par scripts/generate_load_test.py "
            f"(jobs={n_jobs}, resources={n_resources}, seed={seed}) pour challenger "
            f"l'API self-service sur le volume. Combine locality, requirements, "
            f"SLA+value_per_hour, appointment_sla, fixed_resource_id, breaks, "
            f"shift_penalty et maximum_jobs_per_shift à l'échelle. ⚠️ Toujours lancer "
            f"scripts/doctor.py sur ce fichier (gratuit) avant d'envisager un appel "
            f"réel, et estimer le coût avec --jobs/--resources avant d'accepter."
        ),
        "locations": locations,
        "job_types": job_types,
        "resource_types": resource_types,
        "jobs": jobs,
        "resources": resources,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jobs", type=int, default=100, help="nombre de jobs à générer (défaut 100)")
    parser.add_argument("--resources", type=int, default=10, help="nombre de ressources à générer (défaut 10)")
    parser.add_argument("--seed", type=int, default=42, help="graine aléatoire (défaut 42)")
    parser.add_argument("-o", "--output", help="fichier de sortie (défaut stdout)")
    args = parser.parse_args()

    payload = build_payload(args.jobs, args.resources, args.seed)
    out = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        max_cost = 5 + args.resources * args.jobs
        print(f"Écrit : {args.output}", file=sys.stderr)
        print(
            f"Coût MAXIMUM si les {args.jobs} jobs sont tous alloués avec "
            f"{args.resources} ressources dans le payload : 5 + ({args.resources} x "
            f"{args.jobs}) = {max_cost} crédits. En pratique souvent moins (certains "
            f"jobs peuvent rester non alloués, et la formule exacte de facturation "
            f"n'est confirmée que par test réel) — ne jamais lancer l'appel réel sans "
            f"avoir accepté ce pire cas.",
            file=sys.stderr,
        )
    else:
        print(out)


if __name__ == "__main__":
    main()
