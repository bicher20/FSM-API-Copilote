#!/usr/bin/env python3
"""
Validateur de payload Scheduler API (Nomadia) — exécutable en CLI, sans dépendance.

À lancer AVANT tout appel réel à l'API, pour attraper les erreurs les plus fréquentes
sans consommer de crédits. Claude doit exécuter ce script via Bash sur le payload
qu'il vient d'écrire, lire sa sortie, et corriger le payload si des erreurs sont
rapportées — avant de considérer le payload prêt.

Usage:
    python3 scripts/validate_payload.py payload.json
    cat payload.json | python3 scripts/validate_payload.py -

Sortie: exit code 0 si aucune erreur, 1 sinon. Imprime chaque problème sur sa propre
ligne, préfixé par [ERROR] (bloquant, l'API refusera probablement) ou [WARN]
(suspect, à vérifier manuellement).
"""
import sys
import json
from datetime import datetime


def iso_duration_to_seconds(s):
    """Parse grossier d'une durée ISO 8601 (PT1H30M...) pour détecter un format invalide."""
    if not isinstance(s, str) or not s.startswith("PT") and not s.startswith("P"):
        return None
    import re
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
    sla_ids = {s.get("id") for s in payload.get("slas", [])}
    requirement_ids = {r.get("id") for r in payload.get("requirements", [])}
    part_ids = {p.get("id") for p in payload.get("parts", [])}

    # Jobs
    for job in payload.get("jobs", []):
        jid = job.get("id", "<sans id>")
        if not job.get("id"):
            errors.append(f"job: 'id' manquant")
        if job.get("location_id") not in loc_ids:
            errors.append(f"job {jid}: location_id \"{job.get('location_id')}\" absent de locations[]")
        jt = job.get("job_type_id", "DEFAULT")
        if jt not in job_type_ids:
            errors.append(f"job {jid}: job_type_id \"{jt}\" absent de job_types[]")
        sla_ref = job.get("job_sla_id") or job.get("appointment_sla_id")
        if sla_ids and sla_ref and sla_ref not in sla_ids:
            errors.append(f"job {jid}: sla \"{sla_ref}\" absent de slas[]")
        if not job.get("job_sla_id") and not job.get("appointment_sla_id") and "sla" not in job:
            warnings.append(f"job {jid}: aucune fenêtre SLA définie (job_sla_id / appointment_sla_id / sla inline)")
        if job.get("value_per_hour") == 0:
            warnings.append(f"job {jid}: value_per_hour = 0 -> ce job ne sera jamais planifié (raison ZeroValue)")
        cd = job.get("custom_duration")
        if cd is not None and iso_duration_to_seconds(cd) is None:
            errors.append(f"job {jid}: custom_duration \"{cd}\" n'est pas une durée ISO 8601 valide (ex. PT30M)")

    # Resources & shifts
    for resource in payload.get("resources", []):
        rid = resource.get("id", "<sans id>")
        rt = resource.get("resource_type_id", "DEFAULT")
        if rt not in res_type_ids:
            errors.append(f"resource {rid}: resource_type_id \"{rt}\" absent de resource_types[]")
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

    # Resource types / job types location refs
    for rt in payload.get("resource_types", []):
        for key in ("start_location_id", "end_location_id"):
            if rt.get(key) and rt.get(key) not in loc_ids:
                errors.append(f"resource_type {rt.get('id')}: {key} \"{rt.get(key)}\" absent de locations[]")

    # Requirements / parts cross-refs (si présents dans le payload)
    for jr in payload.get("job_requirements", []):
        if jr.get("requirement_id") not in requirement_ids:
            errors.append(f"job_requirement (job {jr.get('job_id')}): requirement_id \"{jr.get('requirement_id')}\" absent de requirements[]")
    for jp in payload.get("job_parts", []):
        if jp.get("part_id") not in part_ids:
            errors.append(f"job_part (job {jp.get('job_id')}): part_id \"{jp.get('part_id')}\" absent de parts[]")

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
