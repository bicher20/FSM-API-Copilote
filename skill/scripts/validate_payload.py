#!/usr/bin/env python3
"""
Validateur de payload Scheduler API (Nomadia) — exécutable en CLI, sans dépendance.

À lancer AVANT tout appel réel à l'API, pour attraper les erreurs les plus fréquentes
sans consommer de crédits. Claude doit exécuter ce script via Bash sur le payload
qu'il vient d'écrire, lire sa sortie, et corriger le payload si des erreurs sont
rapportées — avant de considérer le payload prêt.

Ce validateur suit le schéma self-service réel (voir reference/entities.md, lui-même
dérivé du schéma OpenAPI authentique de https://scheduler-json-api.readme.io) :
- requirements sont des chaînes simples, directement sur job/job_type/resource/
  resource_type (pas d'entité "Requirement" séparée).
- fixed_resource_id et fixed_date_time sont des champs directs sur Job.
- unavailabilities des ressources sont imbriquées sous resources[].unavailabilities[],
  pas une entité top-level avec resource_id en clé étrangère.
- sla et appointment_sla sont des objets imbriqués directement sur Job, jamais
  référencés par un id externe (pas d'entité "SLA" top-level).
- Il n'y a PAS de job_resources (multi-ressources), pre_requisite_definitions
  (ordre entre jobs), parts/job_parts/resource_parts (stock), ni
  schedule_definitions (horizon borné) en self-service — voir
  reference/offre-complete-nomadia.md. Si l'un de ces champs apparaît dans un
  payload, ce script l'alerte : il sera silencieusement ignoré par l'API, pas
  rejeté (HTTP 200 trompeur, voir reference/entities.md).

Usage:
    python3 scripts/validate_payload.py payload.json
    cat payload.json | python3 scripts/validate_payload.py -

Sortie: exit code 0 si aucune erreur, 1 sinon. Imprime chaque problème sur sa propre
ligne, préfixé par [ERROR] (bloquant, l'API refusera probablement) ou [WARN]
(suspect, à vérifier manuellement, ou silencieusement ignoré par l'API).
"""
import sys
import json
import re
from datetime import datetime

# Champs confirmés absents de l'API self-service (voir reference/offre-complete-nomadia.md).
# S'ils apparaissent au niveau racine du payload, l'API les ignore silencieusement
# (HTTP 200) plutôt que de les rejeter — donc ce n'est jamais une [ERROR] ici, mais
# un [WARN] fort pour éviter un faux sentiment que la contrainte a été prise en compte.
OFFRE_COMPLETE_ONLY_KEYS = {
    "job_resources": "job multi-ressources (reference/offre-complete-nomadia.md §1)",
    "parts": "pièces/stock (reference/offre-complete-nomadia.md §2)",
    "job_parts": "pièces/stock (reference/offre-complete-nomadia.md §2)",
    "resource_parts": "pièces/stock (reference/offre-complete-nomadia.md §2)",
    "pre_requisite_definitions": "ordre entre jobs (reference/offre-complete-nomadia.md §3)",
    "schedule_definitions": "horizon de planification borné (reference/offre-complete-nomadia.md §4)",
    "schedule_definition": "horizon de planification borné (reference/offre-complete-nomadia.md §4)",
    "job_availability_patterns": "disponibilité récurrente (reference/offre-complete-nomadia.md §5)",
    "resource_availability_patterns": "disponibilité récurrente (reference/offre-complete-nomadia.md §5)",
    "day_patterns": "disponibilité récurrente (reference/offre-complete-nomadia.md §5)",
    "requirements": "⚠️ ambigu : si c'est une liste de chaînes sur un job/resource, c'est normal "
                     "et self-service ; si c'est une liste d'objets {id: ...} au niveau racine, "
                     "c'est le mécanisme Requirement de l'offre complète, absent du self-service",
}

# Clés d'entité top-level confirmées absentes du self-service (pas de FK séparée) —
# toujours un [WARN] fort, jamais [ERROR], car l'API ne les rejette pas non plus.
OFFRE_COMPLETE_TOP_LEVEL_ENTITY_KEYS = {
    "job_requirements": "offre complète uniquement — self-service: requirements est une liste de "
                         "chaînes directement sur jobs[]/job_types[] (reference/entities.md)",
    "resource_requirements": "offre complète uniquement — self-service: requirements est une liste "
                              "de chaînes directement sur resources[]/resource_types[] (reference/entities.md)",
    "resource_unavailabilities": "offre complète uniquement — self-service: les indisponibilités sont "
                                  "imbriquées sous resources[].unavailabilities[] (reference/entities.md)",
    "slas": "offre complète uniquement — self-service: sla/appointment_sla sont des objets imbriqués "
            "directement sur jobs[], jamais référencés par un id (reference/entities.md)",
    "breaks": "offre complète uniquement — self-service: les pauses sont imbriquées sous "
              "resources[].shifts[].breaks[] (reference/entities.md)",
}


def iso_duration_to_seconds(s):
    """Parse grossier d'une durée ISO 8601 (PT1H30M...) pour détecter un format invalide."""
    if not isinstance(s, str) or (not s.startswith("PT") and not s.startswith("P")):
        return None
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", s)
    if not m:
        return None
    d, h, mi, se = (float(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def validate(payload: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []

    loc_ids = {l.get("id") for l in payload.get("locations", [])}
    job_type_ids = {t.get("id") for t in payload.get("job_types", [])} | {"DEFAULT"}
    res_type_ids = {t.get("id") for t in payload.get("resource_types", [])} | {"DEFAULT"}
    resource_ids = {r.get("id") for r in payload.get("resources", [])}
    job_ids = {j.get("id") for j in payload.get("jobs", [])}

    # Mécanismes de l'offre complète envoyés par erreur à l'API self-service :
    # jamais bloquant pour l'API (elle les ignore), mais un [WARN] fort ici pour
    # éviter de croire qu'une contrainte a été prise en compte alors qu'elle a été
    # silencieusement ignorée.
    for key, note in OFFRE_COMPLETE_ONLY_KEYS.items():
        if key == "requirements" and key not in payload:
            continue
        if key in payload and payload.get(key):
            if key == "requirements":
                # Au niveau racine, "requirements" n'existe dans aucun schéma connu
                # (self-service ou complet) — toujours suspect.
                warnings.append(
                    f"payload: clé racine \"requirements\" inattendue — {note}"
                )
            else:
                warnings.append(
                    f"payload: clé \"{key}\" détectée — ce mécanisme n'existe PAS dans l'API "
                    f"self-service, elle sera silencieusement ignorée (HTTP 200 trompeur), "
                    f"pas rejetée. {note}"
                )
    for key, note in OFFRE_COMPLETE_TOP_LEVEL_ENTITY_KEYS.items():
        if key in payload and payload.get(key):
            warnings.append(f"payload: clé \"{key}\" détectée — {note}")

    def check_requirements_list(owner_label, obj):
        reqs = obj.get("requirements")
        if reqs is None:
            return
        if not isinstance(reqs, list) or any(not isinstance(r, str) for r in reqs):
            errors.append(
                f"{owner_label}: requirements doit être une liste de chaînes simples "
                f"(ex. [\"HABILITATION_ELEC\"]), pas une liste d'objets — voir reference/entities.md"
            )

    # Job types
    for jt in payload.get("job_types", []):
        check_requirements_list(f"job_type {jt.get('id')}", jt)

    # Resource types
    for rt in payload.get("resource_types", []):
        check_requirements_list(f"resource_type {rt.get('id')}", rt)
        for key in ("start_location_id", "end_location_id"):
            if rt.get(key) and rt.get(key) not in loc_ids:
                errors.append(f"resource_type {rt.get('id')}: {key} \"{rt.get(key)}\" absent de locations[]")

    # Jobs
    for job in payload.get("jobs", []):
        jid = job.get("id", "<sans id>")
        if not job.get("id"):
            errors.append("job: 'id' manquant")
        if job.get("location_id") not in loc_ids:
            errors.append(f"job {jid}: location_id \"{job.get('location_id')}\" absent de locations[]")
        jt = job.get("job_type_id", "DEFAULT")
        if jt not in job_type_ids:
            errors.append(f"job {jid}: job_type_id \"{jt}\" absent de job_types[]")
        check_requirements_list(f"job {jid}", job)

        sla = job.get("sla")
        if sla is None:
            warnings.append(f"job {jid}: aucune fenêtre 'sla' définie (objet imbriqué, voir reference/entities.md)")
        else:
            for key in ("earliest_start_date_time", "latest_start_date_time"):
                if key not in sla:
                    errors.append(f"job {jid}: sla.{key} manquant (obligatoire)")
        for sla_key in ("sla", "appointment_sla"):
            s = job.get(sla_key)
            if isinstance(s, dict):
                es, ls = s.get("earliest_start_date_time"), s.get("latest_start_date_time")
                try:
                    if es and ls and datetime.fromisoformat(es) > datetime.fromisoformat(ls):
                        errors.append(f"job {jid}: {sla_key}.earliest_start_date_time > latest_start_date_time")
                except ValueError:
                    errors.append(f"job {jid}: dates de {sla_key} invalides : {es!r} / {ls!r}")

        if job.get("value_per_hour") == 0:
            warnings.append(f"job {jid}: value_per_hour = 0 -> ce job risque de ne jamais être planifié")
        cd = job.get("custom_duration")
        if cd is not None and iso_duration_to_seconds(cd) is None:
            errors.append(f"job {jid}: custom_duration \"{cd}\" n'est pas une durée ISO 8601 valide (ex. PT30M)")

        if job.get("fixed_resource_id") and job.get("fixed_resource_id") not in resource_ids:
            errors.append(f"job {jid}: fixed_resource_id \"{job.get('fixed_resource_id')}\" absent de resources[]")

        for av in job.get("availabilities", []) + job.get("unavailabilities", []):
            s, e = av.get("start_date_time"), av.get("end_date_time")
            try:
                if s and e and datetime.fromisoformat(s) >= datetime.fromisoformat(e):
                    errors.append(f"job {jid}: fenêtre de (in)disponibilité start >= end ({s} >= {e})")
            except ValueError:
                errors.append(f"job {jid}: date de (in)disponibilité invalide : {s!r} / {e!r}")

    # Resources & shifts
    for resource in payload.get("resources", []):
        rid = resource.get("id", "<sans id>")
        rt = resource.get("resource_type_id", "DEFAULT")
        if rt not in res_type_ids:
            errors.append(f"resource {rid}: resource_type_id \"{rt}\" absent de resource_types[]")
        check_requirements_list(f"resource {rid}", resource)

        shifts = resource.get("shifts", [])
        if not shifts:
            warnings.append(f"resource {rid}: aucun shift défini -> ne pourra jamais être affectée")
        for shift in shifts:
            s, e = shift.get("start_date_time"), shift.get("end_date_time")
            try:
                if s and e and datetime.fromisoformat(s) >= datetime.fromisoformat(e):
                    errors.append(f"resource {rid}: shift start_date_time >= end_date_time ({s} >= {e})")
            except ValueError:
                errors.append(f"resource {rid}: date de shift invalide (format attendu 2026-11-02T08:00:00): {s!r} / {e!r}")
            for brk in shift.get("breaks", []):
                bs, be = brk.get("earliest_start_date_time"), brk.get("latest_start_date_time")
                try:
                    if bs and be and datetime.fromisoformat(bs) > datetime.fromisoformat(be):
                        errors.append(f"resource {rid}: break avec earliest_start_date_time > latest_start_date_time")
                except ValueError:
                    errors.append(f"resource {rid}: dates de break invalides : {bs!r} / {be!r}")
                bd = brk.get("duration")
                if bd is not None and iso_duration_to_seconds(bd) is None:
                    errors.append(f"resource {rid}: break duration \"{bd}\" n'est pas une durée ISO 8601 valide")

        # Indisponibilités imbriquées (schéma self-service réel)
        for ru in resource.get("unavailabilities", []):
            s, e = ru.get("start_date_time"), ru.get("end_date_time")
            try:
                if s and e and datetime.fromisoformat(s) >= datetime.fromisoformat(e):
                    errors.append(f"resource {rid}: unavailability start_date_time >= end_date_time ({s} >= {e})")
            except ValueError:
                errors.append(f"resource {rid}: date d'indisponibilité invalide : {s!r} / {e!r}")
            if ru.get("location_id") and ru.get("location_id") not in loc_ids:
                errors.append(f"resource {rid}: unavailability location_id \"{ru.get('location_id')}\" absent de locations[]")

        for key in ("start_location_id", "end_location_id"):
            if resource.get(key) and resource.get(key) not in loc_ids:
                errors.append(f"resource {rid}: {key} \"{resource.get(key)}\" absent de locations[]")

    # Coordonnées plausibles (détecte lat/lng inversées — erreur classique)
    for loc in payload.get("locations", []):
        lat, lng = loc.get("latitude"), loc.get("longitude")
        if isinstance(lat, (int, float)) and abs(lat) > 90:
            errors.append(f"location {loc.get('id')}: latitude={lat} hors plage [-90,90] -> lat/lng probablement inversées")
        if isinstance(lng, (int, float)) and abs(lng) > 180:
            errors.append(f"location {loc.get('id')}: longitude={lng} hors plage [-180,180] -> lat/lng probablement inversées")

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    src = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
    try:
        payload = json.loads(src)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON invalide : {e}")
        sys.exit(1)

    errors, warnings = validate(payload)
    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[ERROR] {e}")

    if errors:
        print(f"\n{len(errors)} erreur(s) bloquante(s), {len(warnings)} avertissement(s). Corrige avant d'appeler l'API.")
        sys.exit(1)
    if warnings:
        print(f"\n0 erreur bloquante, {len(warnings)} avertissement(s) à vérifier.")
    else:
        print("\nPayload valide — rien à signaler.")
    sys.exit(0)


if __name__ == "__main__":
    main()
