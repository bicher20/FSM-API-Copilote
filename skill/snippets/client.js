/**
 * Client minimal pour le Scheduler API de Nomadia (Node.js / navigateur avec fetch).
 * Point de départ à adapter — pas une lib officielle.
 */

// Deux environnements distincts (confirmés par Nomadia le 23/10/2026, versions non
// définitives à cette date — revérifier avant mise en prod) :
//   - TEST : https://scheduler-api-test.nomadia-app.com  (portail : .../dashboard)
//   - PROD : https://scheduler-api.nomadia-app.com        (PAS ENCORE ACTIF à cette date)
// Test par défaut tant que la prod n'est pas confirmée active — surchargeable via la
// variable d'env NOMADIA_BASE_URL (Node) ou en modifiant cette constante.
const BASE_URL =
  (typeof process !== "undefined" && process.env && process.env.NOMADIA_BASE_URL) ||
  "https://scheduler-api-test.nomadia-app.com";

// Affiche une fois par process quel environnement (test/prod) est ciblé — pour qu'un
// vrai appel API ne passe jamais inaperçu sur le mauvais environnement.
let _envAnnounced = false;
function _announceEnv() {
  if (_envAnnounced) return;
  _envAnnounced = true;
  if (BASE_URL.includes("-test")) {
    console.log(
      `[INFO] Appel vers l'environnement de TEST Nomadia (${BASE_URL}) — pas la prod. ` +
        `Pour basculer sur la prod une fois confirmée active, définir ` +
        `NOMADIA_BASE_URL=https://scheduler-api.nomadia-app.com avant d'exécuter.`
    );
  } else {
    console.log(
      `[ATTENTION] Appel vers ${BASE_URL} — vérifie que c'est bien l'environnement de ` +
        `PRODUCTION voulu et non le test (impact réel : données, crédits, abonnement actif requis).`
    );
  }
}

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

// Erreurs sur lesquelles réessayer a un sens : réseau, et 5xx (panne transitoire côté
// API). JAMAIS 400/401/402/403 : ce sont des erreurs de payload/compte, réessayer ne
// change rien et gaspille des crédits (le 400/402 consomme quand même des crédits).
const RETRYABLE_STATUS = new Set([500, 502, 503, 504]);

async function withRetry(fn, { retries = 2, baseDelayMs = 500 } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      const retryable = err instanceof NomadiaApiError ? RETRYABLE_STATUS.has(err.status) : true; // erreur réseau = retryable
      if (!retryable || attempt === retries) throw err;
      await new Promise((r) => setTimeout(r, baseDelayMs * 2 ** attempt));
    }
  }
  throw lastErr;
}

/**
 * @param {string} apiKey
 * @param {object} payload - voir skill/reference/entities.md pour le schéma complet
 * @returns {Promise<{allocations, travels, unallocated_job_reasons, break_allocations}>}
 */
async function scheduleRequest(apiKey, payload) {
  _announceEnv();
  return withRetry(async () => {
    const res = await fetch(`${BASE_URL}/api/schedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": apiKey },
      body: JSON.stringify(payload),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new NomadiaApiError(res.status, body);
    return body;
  });
}

/**
 * @param {string} apiKey
 * @param {Array<{id:string, address_line?:string, post_code?:string, city?:string, country_code?:string}>} addresses - max 100 par appel
 */
async function geocodeRequest(apiKey, addresses) {
  if (addresses.length > 100) {
    throw new Error("geocodeRequest: max 100 adresses par appel — découpe en lots");
  }
  _announceEnv();
  return withRetry(async () => {
    const res = await fetch(`${BASE_URL}/api/geocode`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": apiKey },
      body: JSON.stringify({ addresses }),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new NomadiaApiError(res.status, body);
    return body;
  });
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
