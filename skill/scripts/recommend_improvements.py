#!/usr/bin/env python3
"""
Recommandations d'amélioration — exécutable en CLI, orienté ROI.

Analyse un payload Scheduler API (config envoyée) et, si fourni, la réponse de l'API
(résultat de planification), puis sort une liste de recommandations priorisées, chacune
reliée à un impact business concret (voir reference/kpis-metier.md). Objectif : que le
copilote propose des améliorations de lui-même, sans attendre que l'utilisateur
identifie le problème.

Usage :
    python3 scripts/recommend_improvements.py payload.json
    python3 scripts/recommend_improvements.py payload.json --response reponse.json
    cat payload.json | python3 scripts/recommend_improvements.py -

Sortie : une liste de recommandations groupées par priorité (HIGH/MEDIUM/LOW), chacune
avec le constat, l'action concrète, et l'impact business attendu. Exit code toujours 0
(ce script ne bloque rien, contrairement à validate_payload.py — il informe).
"""
import sys
import json
import argparse
from datetime import datetime


def iso_duration_to_seconds(s):
    if not isinstance(s, str) or not (s.startswith("PT") or s.startswith("P")):
        return None
    import re
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", s)
    if not m:
        return None
    d, h, mi, se = (float(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def recommend_from_payload(payload: dict) -> list[dict]:
    """Recommandations déductibles de la config seule, avant même un appel API."""
    recs = []

    jobs = payload.get("jobs", [])
    resources = payload.get("resources", [])
    resource_types = payload.get("resource_types", [])
    locations = payload.get("locations", [])
    # Schéma self-service réel (reference/entities.md) : requirements est une simple
    # liste de chaînes directement sur jobs[]/job_types[]/resources[]/resource_types[],
    # il n'existe pas d'entité "Requirement"/"JobRequirement"/"ResourceRequirement"
    # séparée (ça, c'est l'offre complète — reference/offre-complete-nomadia.md).
    job_types = payload.get("job_types", [])
    has_job_requirements = any(j.get("requirements") for j in jobs) or any(jt.get("requirements") for jt in job_types)
    has_resource_requirements = any(r.get("requirements") for r in resources) or any(rt.get("requirements") for rt in resource_types)

    # 1. Aucune contrainte de compétence définie du tout
    if jobs and not has_job_requirements and not has_resource_requirements:
        recs.append({
            "priority": "MEDIUM",
            "finding": "aucune compétence/habilitation (champ 'requirements') n'est définie sur les jobs ou ressources",
            "action": "si certains jobs exigent une qualification précise (habilitation électrique, "
                      "certification...), ajouter une liste 'requirements' (chaînes simples) sur le job "
                      "concerné et sur les ressources habilitées — sinon l'API peut affecter n'importe "
                      "quelle ressource à n'importe quel job",
            "impact": "évite une non-conformité terrain (technicien envoyé sans la bonne habilitation) — "
                      "voir reference/kpis-metier.md §1",
        })

    # 2. Pas de shift_penalty -> pas d'incitation à consolider les tournées
    has_shift_penalty = any(rt.get("shift_penalty", 0) for rt in resource_types) or \
                         any(r.get("shift_penalty", 0) for r in resources)
    if resource_types and not has_shift_penalty:
        recs.append({
            "priority": "MEDIUM",
            "finding": "shift_penalty n'est défini sur aucun resource_type/resource (donc = 0 par défaut)",
            "action": "fixer un shift_penalty > 0 sur les resource_types concernés pour inciter l'API à "
                      "concentrer le travail sur moins de ressources/shifts plutôt que de l'étaler",
            "impact": "réduit le nombre de véhicules/techniciens mobilisés pour le même volume de jobs — "
                      "coût fixe journalier en moins, voir reference/kpis-metier.md §4",
        })

    # 3. Aucune locality -> pas de regroupement géographique
    if locations and not any(l.get("locality") for l in locations):
        recs.append({
            "priority": "LOW",
            "finding": "aucune locality définie sur les locations",
            "action": "regrouper les adresses d'un même quartier/secteur sous la même locality",
            "impact": "l'API tente de faire tous les jobs d'une locality d'un coup -> baisse le ratio "
                      "trajet/temps utile, voir reference/kpis-metier.md §2",
        })

    # 4. SLA sans pénalité -> aucune incitation à planifier tôt dans la fenêtre
    # Schéma self-service réel : sla et appointment_sla sont TOUJOURS des objets
    # imbriqués directement sur le job — il n'y a pas d'entité "SLA" top-level ni de
    # job_sla_id/appointment_sla_id référencés (ça, c'est l'offre complète).
    def sla_has_zero_penalty(sla):
        return sla.get("penalty_per_hour", 0) == 0 and sla.get("base_jeopardy_penalty", 0) == 0

    inline_slas = [j.get("sla") for j in jobs if isinstance(j.get("sla"), dict)]
    inline_slas += [j.get("appointment_sla") for j in jobs if isinstance(j.get("appointment_sla"), dict)]
    if inline_slas and all(sla_has_zero_penalty(s) for s in inline_slas):
        recs.append({
            "priority": "LOW",
            "finding": "toutes les fenêtres sla/appointment_sla ont penalty_per_hour=0 et "
                       "base_jeopardy_penalty=0 (valeurs par défaut)",
            "action": "fixer penalty_per_hour > 0 pour pousser l'API à planifier au plus tôt dans la "
                      "fenêtre, et/ou base_jeopardy_penalty > 0 si rater le SLA doit vraiment coûter cher "
                      "à l'optimisation",
            "impact": "réduit le risque de planifier systématiquement en fin de fenêtre client — voir "
                      "reference/kpis-metier.md §3",
        })
    elif not inline_slas and jobs:
        recs.append({
            "priority": "HIGH",
            "finding": "aucun job n'a de fenêtre 'sla' définie (objet imbriqué obligatoire côté self-service)",
            "action": "définir au moins l'objet 'sla' par job avec une fenêtre réaliste "
                      "(earliest_start_date_time / latest_start_date_time)",
            "impact": "sans SLA, l'API n'a aucune contrainte de respect de rendez-vous client — risque "
                      "direct de planning inexploitable commercialement, voir reference/kpis-metier.md §3",
        })

    # 5. Pas de plafond de jobs par shift -> risque de surcharge d'une ressource
    has_job_cap = any(rt.get("maximum_jobs_per_shift") for rt in resource_types) or \
                  any(r.get("maximum_jobs_per_shift") for r in resources)
    if resource_types and not has_job_cap:
        recs.append({
            "priority": "LOW",
            "finding": "maximum_jobs_per_shift n'est défini sur aucun resource_type/resource",
            "action": "fixer une limite si le métier a un seuil réaliste au-delà duquel la qualité "
                      "d'exécution se dégrade (fatigue, erreurs)",
            "impact": "protège contre un déséquilibre de charge entre ressources — voir "
                      "reference/kpis-metier.md §4",
        })

    # 6. Mécanismes de l'offre complète envoyés par erreur (silencieusement ignorés)
    # Confirmé par le schéma OpenAPI réel (reference/entities.md) : ScheduleDefinition,
    # PreRequisiteDefinition, Part/JobResourcePart/ResourcePart et JobResource
    # n'existent PAS en self-service. Si l'un de ces champs apparaît dans le payload,
    # ce n'est jamais un oubli à corriger — c'est un signal qu'on a essayé d'utiliser
    # un mécanisme de l'offre complète qui sera silencieusement ignoré par l'API.
    offre_complete_keys_present = [
        k for k in ("schedule_definitions", "schedule_definition", "pre_requisite_definitions",
                    "job_resources", "parts", "job_parts", "resource_parts")
        if payload.get(k)
    ]
    if offre_complete_keys_present:
        recs.append({
            "priority": "HIGH",
            "finding": f"le payload contient {', '.join(offre_complete_keys_present)} — "
                       f"mécanisme(s) de l'offre complète Nomadia, absent(s) de l'API self-service",
            "action": "ces clés seront silencieusement ignorées par l'API self-service (HTTP 200 "
                      "trompeur, pas une erreur). Si le besoin métier est réel, voir "
                      "reference/offre-complete-nomadia.md pour l'exemple correspondant et orienter le "
                      "client vers un contact Nomadia plutôt que de garder ce payload tel quel",
            "impact": "évite de croire qu'une contrainte a été prise en compte par le solveur alors "
                      "qu'elle a été purement et simplement ignorée",
        })

    return recs


def recommend_from_response(response: dict, payload: dict | None) -> list[dict]:
    """Recommandations tirées du résultat d'un appel réel — nécessite un vrai test API."""
    recs = []

    allocations = response.get("allocations", [])
    unallocated = response.get("unallocated_job_reasons", [])
    travels = response.get("travels", [])

    total_jobs = len(payload.get("jobs", [])) if payload else (len(allocations) + len(unallocated))

    if total_jobs:
        allocated_jobs = len({a.get("job_id") for a in allocations})
        rate = allocated_jobs / total_jobs * 100
        priority = "HIGH" if rate < 90 else "LOW"
        recs.append({
            "priority": priority,
            "finding": f"taux d'allocation = {rate:.0f}% ({allocated_jobs}/{total_jobs} jobs planifiés)",
            "action": "si < 90%, regarder le détail des unallocated_job_reasons ci-dessous et "
                      "troubleshooting.md §2 pour chaque raison avant de conclure à un manque de "
                      "capacité réelle",
            "impact": "chaque job non planifié = rattrapage manuel par un planificateur humain, voir "
                      "reference/kpis-metier.md §1",
        })

    if unallocated:
        tally = {}
        for u in unallocated:
            reason = u.get("unallocated_reason", "Unknown")
            tally[reason] = tally.get(reason, 0) + 1
        detail = ", ".join(f"{r}×{c}" for r, c in sorted(tally.items(), key=lambda x: -x[1]))
        recs.append({
            "priority": "HIGH",
            "finding": f"{len(unallocated)} job(s) non planifié(s) — répartition : {detail}",
            "action": "ouvrir troubleshooting.md §2 et traiter la raison la plus fréquente d'abord",
            "impact": "souvent la cause la plus visible en démo/POC auprès d'un prospect — à anticiper",
        })

    # Respect des pauses obligatoires (Break) : signalé pour la première fois le
    # 23/10/2026 par un testeur qui a remarqué que ce script ne vérifiait pas que les
    # pauses demandées dans le payload apparaissent bien dans break_allocations.
    # NOTE DE FIABILITÉ : on ne connaît pas précisément le schéma d'un item de
    # break_allocations (champs internes non confirmés) — ce contrôle compte
    # seulement le nombre de pauses demandées vs présentes, sans vérifier l'horaire
    # exact. Confirmé sur 07_pause_obligatoire.json (1 pause demandée -> 1 présente).
    if payload:
        requested_breaks = len(payload.get("breaks", []))
        for r in payload.get("resources", []):
            for shift in r.get("shifts", []):
                requested_breaks += len(shift.get("breaks", []))
        if requested_breaks:
            allocated_breaks = response.get("break_allocations", [])
            if len(allocated_breaks) < requested_breaks:
                recs.append({
                    "priority": "HIGH",
                    "finding": f"{requested_breaks} pause(s) obligatoire(s) demandée(s) dans le payload, "
                               f"mais seulement {len(allocated_breaks)} présente(s) dans break_allocations",
                    "action": "identifier quelle(s) pause(s) n'ont pas été honorées (resource/shift) — "
                              "souvent parce que la charge de jobs du shift ne laisse pas de créneau "
                              "compatible avec la fenêtre de pause demandée. Voir troubleshooting.md",
                    "impact": "une pause réglementaire (ex: pause déjeuner légale) non respectée dans le "
                              "plan proposé est un risque de conformité à ne jamais laisser passer en "
                              "silence — contrôle absent avant le 23/10/2026",
                })

    if travels:
        total_travel_s = 0
        for t in travels:
            try:
                s = datetime.fromisoformat(t["start_date_time"])
                e = datetime.fromisoformat(t["end_date_time"])
                total_travel_s += (e - s).total_seconds()
            except (KeyError, ValueError, TypeError):
                continue
        job_types = {jt.get("id"): jt for jt in (payload.get("job_types", []) if payload else [])}
        total_job_s = 0
        for j in (payload.get("jobs", []) if payload else []):
            cd = j.get("custom_duration") or job_types.get(j.get("job_type_id", "DEFAULT"), {}).get("custom_duration") or "PT1H"
            total_job_s += iso_duration_to_seconds(cd) or 3600
        if total_job_s:
            ratio = total_travel_s / total_job_s * 100
            priority = "HIGH" if ratio > 40 else ("MEDIUM" if ratio > 25 else "LOW")
            recs.append({
                "priority": priority,
                "finding": f"ratio trajet/temps utile ≈ {ratio:.0f}% "
                           f"({total_travel_s/3600:.1f}h de trajet pour {total_job_s/3600:.1f}h de jobs)",
                "action": "si > 25-30%, regarder locality sur les Location et resource_type.start/end_location_id "
                          "— souvent le levier le plus rapide",
                "impact": "c'est l'argument ROI le plus parlant face à un prospect — voir "
                          "reference/kpis-metier.md §2",
            })

    return recs


def print_recs(recs: list[dict]):
    if not recs:
        print("Aucune recommandation — configuration déjà cohérente sur les points vérifiés.")
        return
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for r in sorted(recs, key=lambda r: order.get(r["priority"], 9)):
        print(f"[{r['priority']}] {r['finding']}")
        print(f"    -> action : {r['action']}")
        print(f"    -> impact : {r['impact']}")
        print()


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("payload", help="chemin du payload JSON, ou '-' pour stdin")
    parser.add_argument("--response", help="chemin de la réponse API JSON (optionnel, pour analyser un vrai résultat)")
    args = parser.parse_args()

    src = sys.stdin.read() if args.payload == "-" else open(args.payload, encoding="utf-8").read()
    try:
        payload = json.loads(src)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON invalide dans {args.payload} : {e}")
        sys.exit(1)

    recs = recommend_from_payload(payload)

    if args.response:
        with open(args.response, encoding="utf-8") as f:
            try:
                response = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON invalide dans {args.response} : {e}")
                sys.exit(1)
        recs += recommend_from_response(response, payload)

    print_recs(recs)
    sys.exit(0)


if __name__ == "__main__":
    main()
