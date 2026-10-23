/**
 * Client minimal pour le Scheduler API de Nomadia (Node.js / navigateur avec fetch).
 * Point de départ à adapter — pas une lib officielle.
 */

const BASE_URL = "https://scheduler-api.nomadia-app.com";

class NomadiaApiError extends Error {
  constructor(status, body) {
    const hint = {
      400: "requête invalide — vérifie les id référencés et le format des dates/durées (voir skill/troubleshooting.md)",
      401: "clé API manquante, invalide ou bloquée — vérifie le header x-api-key",
      402: "solde de crédits négatif — recharge depuis le portail Nomadia",
      403: "période d'essai terminée — un abonnement est requis",
    }[status] || "erreur inattendue";
    super(`Nomadia API ${status}: ${hint}`);
    this.status = status;
    this.body = body;
  }
}

/**
 * @param {string} apiKey
 * @param {object} payload - voir skill/reference/entities.md pour le schéma complet
 * @returns {Promise<{allocations, travels, unallocated_job_reasons, break_allocations}>}
 */
async function scheduleRequest(apiKey, payload) {
  const res = await fetch(`${BASE_URL}/api/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": apiKey },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new NomadiaApiError(res.status, body);
  return body;
}

/**
 * @param {string} apiKey
 * @param {Array<{id:string, address_line?:string, post_code?:string, city?:string, country_code?:string}>} addresses - max 100 par appel
 */
async function geocodeRequest(apiKey, addresses) {
  if (addresses.length > 100) {
    throw new Error("geocodeRequest: max 100 adresses par appel — découpe en lots");
  }
  const res = await fetch(`${BASE_URL}/api/geocode`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": apiKey },
    body: JSON.stringify({ addresses }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new NomadiaApiError(res.status, body);
  return body;
}

/**
 * Validation locale avant appel — attrape les erreurs les plus fréquentes
 * sans consommer de crédits. Voir skill/troubleshooting.md §6.
 */
function validatePayload(payload) {
  const errors = [];
  const locIds = new Set((payload.locations || []).map((l) => l.id));
  const jobTypeIds = new Set((payload.job_types || []).map((t) => t.id));
  const resTypeIds = new Set((payload.resource_types || []).map((t) => t.id));

  for (const job of payload.jobs || []) {
    if (!locIds.has(job.location_id)) {
      errors.push(`job ${job.id}: location_id "${job.location_id}" n'existe pas dans locations[]`);
    }
    if (job.job_type_id && !jobTypeIds.has(job.job_type_id) && job.job_type_id !== "DEFAULT") {
      errors.push(`job ${job.id}: job_type_id "${job.job_type_id}" n'existe pas dans job_types[]`);
    }
  }
  for (const resource of payload.resources || []) {
    if (resource.resource_type_id && !resTypeIds.has(resource.resource_type_id) && resource.resource_type_id !== "DEFAULT") {
      errors.push(`resource ${resource.id}: resource_type_id "${resource.resource_type_id}" n'existe pas dans resource_types[]`);
    }
    for (const shift of resource.shifts || []) {
      if (new Date(shift.start_date_time) >= new Date(shift.end_date_time)) {
        errors.push(`resource ${resource.id}: shift avec start_date_time >= end_date_time`);
      }
    }
  }
  return errors;
}

module.exports = { scheduleRequest, geocodeRequest, validatePayload, NomadiaApiError };
