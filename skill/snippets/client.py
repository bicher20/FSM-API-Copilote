"""
Client minimal pour le Scheduler API de Nomadia (Python / requests).
Point de départ à adapter — pas une lib officielle.

Pour valider un payload avant appel, préférer le script dédié, plus complet :
    python3 scripts/validate_payload.py payload.json
La fonction validate_payload() ci-dessous est une version allégée, utile en code mais
moins exhaustive que le script CLI.
"""
import os
import time
from datetime import datetime
import requests

# Deux environnements distincts (confirmés par Nomadia le 23/10/2026, versions non
# définitives à cette date — revérifier avant mise en prod) :
#   - TEST : https://scheduler-api-test.nomadia-app.com  (portail : .../dashboard)
#   - PROD : https://scheduler-api.nomadia-app.com        (PAS ENCORE ACTIF à cette date)
# Utiliser le test par défaut tant que la prod n'est pas confirmée active — on
# évite ainsi l'erreur DNS "Name or service not known" qu'on obtient en ciblant un
# domaine prod pas encore résolu. Surchargeable via la variable d'env NOMADIA_BASE_URL.
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
    400: "requête invalide — vérifie les id référencés et le format des dates/durées (voir skill/troubleshooting.md)",
    401: "clé API manquante, invalide ou bloquée — vérifie le header x-api-key",
    402: "solde de crédits négatif — recharge depuis le portail Nomadia",
    403: "période d'essai terminée — un abonnement est requis",
}

# Erreurs sur lesquelles réessayer a un sens : réseau, et 5xx (panne transitoire côté
# API). JAMAIS 400/401/402/403 : ce sont des erreurs de payload/compte, réessayer ne
# corrige rien et consomme des crédits pour rien.
_RETRYABLE_STATUS = {500, 502, 503, 504}


class NomadiaApiError(Exception):
    def __init__(self, status_code, body):
        hint = _ERROR_HINTS.get(status_code, "erreur inattendue")
        super().__init__(f"Nomadia API {status_code}: {hint}")
        self.status_code = status_code
        self.body = body


def _with_retry(fn, retries=2, base_delay=0.5):
    last_err = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except NomadiaApiError as e:
            last_err = e
            if e.status_code not in _RETRYABLE_STATUS or attempt == retries:
                raise
        except requests.RequestException as e:
            last_err = e
            if attempt == retries:
                raise
        time.sleep(base_delay * (2 ** attempt))
    raise last_err


def schedule_request(api_key: str, payload: dict) -> dict:
    """payload : voir skill/reference/entities.md pour le schéma complet."""
    _announce_env()
    def _call():
        res = requests.post(
            f"{BASE_URL}/api/schedule",
            json=payload,
            headers={"x-api-key": api_key},
            timeout=60,
        )
        if not res.ok:
            raise NomadiaApiError(res.status_code, _safe_json(res))
        return res.json()
    return _with_retry(_call)


def geocode_request(api_key: str, addresses: list[dict]) -> dict:
    """addresses : max 100 par appel — [{id, address_line?, post_code?, city?, country_code?}]"""
    if len(addresses) > 100:
        raise ValueError("geocode_request: max 100 adresses par appel — découpe en lots")
    _announce_env()
    def _call():
        res = requests.post(
            f"{BASE_URL}/api/geocode",
            json={"addresses": addresses},
            headers={"x-api-key": api_key},
            timeout=30,
        )
        if not res.ok:
            raise NomadiaApiError(res.status_code, _safe_json(res))
        return res.json()
    return _with_retry(_call)


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
