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
    python3 scripts/generate_load_test.py --jobs 50 --resources 5 \
        --elec-resource-ratio 0.6 --elec-job-ratio 0.5 --appointment-ratio 0.2 \
        --fixed-ratio 0 --date 2026-12-01 -o payload.json

Options :
    --jobs N                  nombre d'interventions à générer (défaut 100)
    --resources M              nombre de ressources à générer (défaut 10)
    --seed S                   graine aléatoire, pour un résultat reproductible (défaut 42)
    --elec-resource-ratio R    proportion de ressources habilitées électricité, 0-1 (défaut 0.3)
    --elec-job-ratio R         proportion de jobs exigeant l'habilitation électrique, 0-1 (défaut 0.2)
    --appointment-ratio R      proportion de jobs avec un rendez-vous serré (appointment_sla), 0-1 (défaut 0.1)
    --fixed-ratio R            proportion de jobs engagés d'office (fixed_resource_id), 0-1 (défaut 0.04)
    --date AAAA-MM-JJ          date du planning (défaut 2026-11-02)
    -o FICHIER                 fichier de sortie (défaut stdout)

Les ratios n'ont rien de figé : adapte-les au vrai besoin du client plutôt que de
garder les défauts si tu connais ses effectifs réels (ex. "certains" techniciens
habilités électricité n'est pas forcément 30%).
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


def build_payload(
    n_jobs: int,
    n_resources: int,
    seed: int,
    elec_resource_ratio: float = 0.3,
    elec_job_ratio: float = 0.2,
    appointment_ratio: float = 0.1,
    fixed_ratio: float = 0.04,
    date: str = "2026-11-02",
) -> dict:
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

    # Ratios paramétrables (voir --elec-resource-ratio etc.) plutôt que des
    # pourcentages codés en dur — un vrai client n'a pas forcément 30%/20%.
    n_elec_resources = max(1, round(n_resources * elec_resource_ratio))
    elec_resource_indices = set(rng.sample(range(1, n_resources + 1), min(n_elec_resources, n_resources)))

    resources = []
    for i in range(1, n_resources + 1):
        is_elec = i in elec_resource_indices
        shift = {
            "start_date_time": f"{date}T08:00:00",
            "end_date_time": f"{date}T18:00:00",
            "breaks": [
                {
                    "earliest_start_date_time": f"{date}T12:00:00",
                    "latest_start_date_time": f"{date}T13:30:00",
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

    # Jobs exigeant l'habilitation électrique, avec rendez-vous serré
    # (appointment_sla), ou engagés d'office sur une ressource précise
    # (fixed_resource_id) : tirés aléatoirement selon les ratios fournis, pour
    # exercer plusieurs mécanismes self-service en même temps à l'échelle, sans
    # imposer un motif figé (modulo) qui ne correspondrait pas au cas réel du client.
    n_elec_jobs = max(0, round(n_jobs * elec_job_ratio))
    n_appointment_jobs = max(0, round(n_jobs * appointment_ratio))
    n_fixed_jobs = max(0, round(n_jobs * fixed_ratio)) if n_resources > 0 else 0
    all_job_indices = list(range(1, n_jobs + 1))
    elec_job_indices = set(rng.sample(all_job_indices, min(n_elec_jobs, n_jobs)))
    appointment_job_indices = set(rng.sample(all_job_indices, min(n_appointment_jobs, n_jobs)))
    fixed_job_indices = set(rng.sample(all_job_indices, min(n_fixed_jobs, n_jobs)))

    jobs = []
    for i in range(1, n_jobs + 1):
        requires_elec = i in elec_job_indices
        has_appointment = i in appointment_job_indices
        is_fixed = i in fixed_job_indices
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
                "earliest_start_date_time": f"{date}T08:00:00",
                "latest_start_date_time": f"{date}T18:00:00",
                "penalty_per_hour": 5,
            },
        }
        if requires_elec:
            job["requirements"] = ["HABILITATION_ELEC"]
        if has_appointment:
            # Fenêtre de rendez-vous de 30 min, répartie entre 9h et 17h.
            hour = rng.randint(9, 16)
            job["appointment_sla"] = {
                "earliest_start_date_time": f"{date}T{hour:02d}:00:00",
                "latest_start_date_time": f"{date}T{hour:02d}:30:00",
                "penalty_per_hour": 50,
                "base_jeopardy_penalty": 1000,
            }
        if is_fixed:
            job["fixed_resource_id"] = f"RES-{rng.randint(1, n_resources)}"
        jobs.append(job)

    return {
        "_comment": (
            f"Payload de charge généré par scripts/generate_load_test.py "
            f"(jobs={n_jobs}, resources={n_resources}, seed={seed}, "
            f"elec_resource_ratio={elec_resource_ratio}, elec_job_ratio={elec_job_ratio}, "
            f"appointment_ratio={appointment_ratio}, fixed_ratio={fixed_ratio}, date={date}) "
            f"pour challenger l'API self-service sur le volume. Combine locality, "
            f"requirements, SLA+value_per_hour, appointment_sla, fixed_resource_id, "
            f"breaks, shift_penalty et maximum_jobs_per_shift à l'échelle. ⚠️ Toujours "
            f"lancer scripts/doctor.py sur ce fichier (gratuit) avant d'envisager un "
            f"appel réel, et estimer le coût avec --jobs/--resources avant d'accepter."
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
    parser.add_argument("--elec-resource-ratio", type=float, default=0.3,
                         help="proportion de ressources habilitées électricité, 0-1 (défaut 0.3)")
    parser.add_argument("--elec-job-ratio", type=float, default=0.2,
                         help="proportion de jobs exigeant l'habilitation électrique, 0-1 (défaut 0.2)")
    parser.add_argument("--appointment-ratio", type=float, default=0.1,
                         help="proportion de jobs avec un rendez-vous serré (appointment_sla), 0-1 (défaut 0.1)")
    parser.add_argument("--fixed-ratio", type=float, default=0.04,
                         help="proportion de jobs engagés d'office sur une ressource (fixed_resource_id), 0-1 (défaut 0.04)")
    parser.add_argument("--date", default="2026-11-02", help="date du planning, format AAAA-MM-JJ (défaut 2026-11-02)")
    parser.add_argument("-o", "--output", help="fichier de sortie (défaut stdout)")
    args = parser.parse_args()

    payload = build_payload(
        args.jobs, args.resources, args.seed,
        elec_resource_ratio=args.elec_resource_ratio,
        elec_job_ratio=args.elec_job_ratio,
        appointment_ratio=args.appointment_ratio,
        fixed_ratio=args.fixed_ratio,
        date=args.date,
    )
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
