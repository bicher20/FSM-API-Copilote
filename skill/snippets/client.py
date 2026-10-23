"""
Client minimal pour le Scheduler API de Nomadia (Python / requests).
Point de départ à adapter — pas une lib officielle.
"""
from datetime import datetime
import requests

BASE_URL = "https://scheduler-api.nomadia-app.com"

_ERROR_HINTS = {
    400: "requête invalide — vérifie les id référencés et le format des dates/durées (voir skill/troubleshooting.md)",
    401: "clé API manquante, invalide ou bloquée — vérifie le header x-api-key",
    402: "solde de crédits négatif — recharge depuis le portail Nomadia",
    403: "période d'essai terminée — un abonnement est requis",
}


class NomadiaApiError(Exception):
    def __init__(self, status_code, body):
        hint = _ERROR_HINTS.get(status_code, "erreur inattendue")
        super().__init__(f"Nomadia API {status_code}: {hint}")
        self.status_code = status_code
        self.body = body


def schedule_request(api_key: str, payload: dict) -> dict:
    """payload : voir skill/reference/entities.md pour le schéma complet."""
    res = requests.post(
        f"{BASE_URL}/api/schedule",
        json=payload,
        headers={"x-api-key": api_key},
        timeout=60,
    )
    if not res.ok:
        raise NomadiaApiError(res.status_code, _safe_json(res))
    return res.json()


def geocode_request(api_key: str, addresses: list[dict]) -> dict:
    """addresses : max 100 par appel — [{id, address_line?, post_code?, city?, country_code?}]"""
    if len(addresses) > 100:
        raise ValueError("geocode_request: max 100 adresses par appel — découpe en lots")
    res = requests.post(
        f"{BASE_URL}/api/geocode",
        json={"addresses": addresses},
        headers={"x-api-key": api_key},
        timeout=30,
    )
    if not res.ok:
        raise NomadiaApiError(res.status_code, _safe_json(res))
    return res.json()


def validate_payload(payload: dict) -> list[str]:
    """Validation locale avant appel — attrape les erreurs les plus fréquentes
    sans consommer de crédits. Voir skill/troubleshooting.md §6."""
    errors = []
    loc_ids = {l["id"] for l in payload.get("locations", [])}
    job_type_ids = {t["id"] for t in payload.get("job_types", [])}
    res_type_ids = {t["id"] for t in payload.get("resource_types", [])}

    for job in payload.get("jobs", []):
        if job.get("location_id") not in loc_ids:
            errors.append(f'job {job.get("id")}: location_id "{job.get("location_id")}" absent de locations[]')
        jt = job.get("job_type_id")
        if jt and jt != "DEFAULT" and jt not in job_type_ids:
            errors.append(f'job {job.get("id")}: job_type_id "{jt}" absent de job_types[]')

    for resource in payload.get("resources", []):
        rt = resource.get("resource_type_id")
        if rt and rt != "DEFAULT" and rt not in res_type_ids:
            errors.append(f'resource {resource.get("id")}: resource_type_id "{rt}" absent de resource_types[]')
        for shift in resource.get("shifts", []):
            try:
                start = datetime.fromisoformat(shift["start_date_time"])
                end = datetime.fromisoformat(shift["end_date_time"])
                if start >= end:
                    errors.append(f'resource {resource.get("id")}: shift avec start_date_time >= end_date_time')
            except (KeyError, ValueError):
                errors.append(f'resource {resource.get("id")}: dates de shift invalides')

    return errors


def _safe_json(res):
    try:
        return res.json()
    except ValueError:
        return None
