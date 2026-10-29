#!/usr/bin/env python3
"""
Moteur de rapprochement "code client <-> modèle Nomadia" — stdlib uniquement.

Pourquoi ce script. L'agent qui exécute ce skill (Claude Code, Cursor, Codex, ou
autre) a déjà des outils pour lire le code du client (grep, lecture de fichiers,
inspection d'un schéma de base de données) — "Étape 1" de SKILL.md lui demande déjà
de les utiliser avant de poser une question. Ce script ne remplace pas cette lecture
de code : il prend ce que l'agent a DÉJÀ trouvé (une liste de noms de tables/colonnes/
champs extraits du repo client, à fournir en JSON) et calcule, par comparaison avec le
vocabulaire métier connu de chaque entité Nomadia (synonymes FR/EN courants + mesure de
similarité textuelle), quels champs client correspondent probablement à quel champ
Nomadia — pour que l'agent n'ait besoin de demander confirmation QUE sur ce qui reste
ambigu, jamais sur ce qu'il peut déjà déduire du code.

Ce n'est pas un classifieur magique : c'est une liste de synonymes + une mesure de
proximité de chaînes (difflib, stdlib). Les correspondances "faible confiance" ou
"aucune" doivent TOUJOURS être confirmées avec le client, jamais déduites en silence.

Usage :
    python3 scripts/match_data_model.py match --input client_fields.json
        -> client_fields.json : liste de chaînes (noms de tables/colonnes/champs
           trouvés dans le code/schéma du client), ex. :
           ["intervention", "technicien_id", "adresse_client", "duree_estimee",
            "competence_requise", "date_rdv_debut", "date_rdv_fin"]
        -> affiche, pour chaque entité Nomadia (Job, Resource, Location, ResourceType,
           JobType) et ses champs clés, le(s) champ(s) client qui matchent, avec un
           niveau de confiance (haute / moyenne / aucune) — haute : ne redemande pas
           au client, mappe directement dans le PRD/le payload en le disant
           explicitement ("je mappe ta colonne X sur le champ Y de l'API, dis-moi si
           je me trompe") ; moyenne : propose la correspondance MAIS fais confirmer
           explicitement, ne l'enregistre jamais comme acquise sans ce "oui" ; aucune :
           pose la question directement, rien à déduire.

    python3 scripts/match_data_model.py vocabulary
        -> affiche le dictionnaire de synonymes utilisé, pour audit/extension.
"""

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher

# Vocabulaire métier connu par entité Nomadia (self-service réel, voir entities.md).
# Clé = "<Entité>.<champ Nomadia>" (ou juste "<Entité>" pour le nom de la table elle-même).
# Valeur = synonymes/mots-clés FR+EN couramment vus dans un schéma de données client.
VOCABULARY = {
    "Job (table/entité)": [
        "job", "jobs", "intervention", "interventions", "rdv", "rendezvous",
        "rendez_vous", "visite", "visites", "tache", "taches", "mission",
        "missions", "commande", "commandes", "ticket", "tickets", "dossier",
        "dossiers", "chantier", "chantiers", "appel", "appels", "demande",
        "demandes", "ordre_travail", "bon_travail", "work_order",
    ],
    "Job.sla (fenêtre de rendez-vous)": [
        "fenetre", "creneau", "plage_horaire", "date_debut", "date_fin",
        "heure_debut", "heure_fin", "start_date", "end_date", "window",
        "time_slot", "date_rdv_debut", "date_rdv_fin",
    ],
    "Job.requirements (compétences requises)": [
        "competence", "competences", "habilitation", "habilitations",
        "certification", "qualification", "skill", "skills", "specialite",
        "competence_requise", "requirement",
    ],
    "Job.value_per_hour (criticité/valeur)": [
        "priorite", "priority", "criticite", "valeur", "montant", "importance",
        "urgence", "poids",
    ],
    "Job.custom_duration (durée)": [
        "duree", "duree_estimee", "duree_prevue", "temps_estime", "duration",
        "temps_intervention",
    ],
    "JobType (table/entité)": [
        "type_intervention", "categorie_intervention", "nature_intervention",
        "job_type", "type_job", "categorie", "nature",
    ],
    "Resource (table/entité)": [
        "technicien", "techniciens", "employe", "employes", "salarie",
        "salaries", "agent", "agents", "ouvrier", "ouvriers", "livreur",
        "livreurs", "chauffeur", "chauffeurs", "vehicule", "vehicules",
        "camion", "camions", "equipe", "equipes", "ressource", "ressources",
        "resource", "staff", "worker", "driver", "person", "personnel",
    ],
    "Resource.requirements (compétences de la ressource)": [
        "competence_technicien", "habilitation_technicien", "qualification",
        "certification_technicien", "skill_technicien",
    ],
    "Resource.shifts (disponibilité/horaires)": [
        "horaire", "horaires", "planning", "disponibilite", "disponibilites",
        "plage_travail", "shift", "shifts", "creneau_travail", "schedule",
    ],
    "ResourceType (table/entité)": [
        "metier", "profil", "categorie_technicien", "specialite",
        "type_technicien", "poste", "role", "profession", "resource_type",
    ],
    "Location (table/entité)": [
        "adresse", "adresses", "lieu", "lieux", "site", "sites",
        "adresse_client", "chantier_adresse", "point", "destination",
        "localisation", "geoloc", "coordonnees", "latitude", "longitude",
        "location", "address",
    ],
    "Location.locality (secteur/zone)": [
        "secteur", "zone", "region", "quartier", "arrondissement", "district",
        "territoire", "locality",
    ],
}


def _split_camel_case(s: str) -> str:
    """Insère un '_' aux frontières camelCase (ex: 'disponibiliteRessource' ->
    'disponibilite_Ressource') AVANT toute mise en minuscule — sinon la frontière de
    casse est perdue et le découpage par token échoue silencieusement sur ce style de
    nommage (repéré en testant contre un corpus client volontairement mixte FR/EN/
    camelCase, voir CHANGELOG)."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)


def _normalize(s: str) -> str:
    """minuscule, sans accents, séparateurs uniformisés — pour comparer sans bruit.
    Le découpage camelCase doit être fait par l'appelant AVANT normalize (voir
    _split_camel_case) car cette fonction met en minuscule et détruit l'info de casse."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    for sep in ("-", " "):
        s = s.replace(sep, "_")
    return s


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _tokens(s: str) -> set[str]:
    """Découpe en tokens sur '_' après normalisation — un token vide (séparateurs
    collés) est ignoré."""
    return {t for t in s.split("_") if t}


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "haute"
    if score >= 0.6:
        return "moyenne"
    return "aucune"


def match_fields(client_fields: list[str]) -> list[dict]:
    results = []
    for raw_field in client_fields:
        norm_field = _normalize(_split_camel_case(raw_field))
        field_tokens = _tokens(norm_field)
        best_entity = None
        best_score = 0.0
        best_synonym = None
        for entity_key, synonyms in VOCABULARY.items():
            for syn in synonyms:
                norm_syn = _normalize(_split_camel_case(syn))
                syn_tokens = _tokens(norm_syn)
                if norm_field == norm_syn:
                    # correspondance exacte -> score maximal direct
                    score = 1.0
                elif syn_tokens and (syn_tokens <= field_tokens or field_tokens <= syn_tokens):
                    # correspondance par TOKEN complet (découpage sur '_'), jamais une
                    # sous-chaîne brute : "technicien_id" contient le token entier
                    # "technicien" -> vrai match ; "require_signature" ne contient PAS
                    # le token "nature" même si la sous-chaîne "signature" le contient
                    # littéralement ("si-NATUR-e") — une comparaison sur sous-chaînes
                    # brutes confondait les deux (repéré en testant contre un vrai
                    # schéma FSM open source, voir CHANGELOG). Un token complet qui
                    # matche un token complet reste un score fort, mais jamais aussi
                    # trompeur qu'une sous-chaîne au milieu d'un autre mot.
                    score = 0.9
                else:
                    score = _similarity(norm_field, norm_syn)
                if score > best_score:
                    best_score = score
                    best_entity = entity_key
                    best_synonym = syn
        results.append(
            {
                "champ_client": raw_field,
                "correspondance_nomadia": best_entity if best_score >= 0.6 else None,
                "synonyme_declencheur": best_synonym if best_score >= 0.6 else None,
                "score": round(best_score, 2),
                "confiance": _confidence_label(best_score),
            }
        )
    return results


def cmd_match(args: argparse.Namespace) -> None:
    try:
        with open(args.input, encoding="utf-8") as f:
            client_fields = json.load(f)
    except FileNotFoundError:
        print(f"[ERREUR] fichier introuvable : {args.input}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERREUR] {args.input} n'est pas un JSON valide : {e}")
        sys.exit(1)

    if not isinstance(client_fields, list):
        print("[ERREUR] le fichier d'entrée doit être une liste JSON de chaînes.")
        sys.exit(1)
    if not client_fields:
        print("[ERREUR] la liste est vide — rien à rapprocher.")
        sys.exit(1)
    non_strings = [v for v in client_fields if not isinstance(v, str)]
    if non_strings:
        print(f"[ERREUR] la liste doit contenir uniquement des chaînes — valeur(s) non "
              f"textuelle(s) trouvée(s) : {non_strings!r}. Si ce sont des noms de "
              "colonnes/tables, écris-les comme des chaînes JSON (\"nom_du_champ\").")
        sys.exit(1)
    empty = [i for i, v in enumerate(client_fields) if not v.strip()]
    if empty:
        print(f"[ERREUR] chaîne(s) vide(s) à l'index {empty} — retire-les ou précise un nom.")
        sys.exit(1)

    results = match_fields(client_fields)

    haute = [r for r in results if r["confiance"] == "haute"]
    moyenne = [r for r in results if r["confiance"] == "moyenne"]
    aucune = [r for r in results if r["confiance"] == "aucune"]

    print(f"Rapprochement de {len(results)} champ(s) client contre le modèle Nomadia.\n")

    if haute:
        print("== Haute confiance — ne redemande PAS au client, mappe directement ==")
        print("   (dis-le quand même explicitement : \"je mappe ta colonne X sur Y\")")
        for r in haute:
            print(f"  - {r['champ_client']!r} -> {r['correspondance_nomadia']} "
                  f"(score {r['score']})")
        print()

    if moyenne:
        print("== Confiance moyenne — propose la correspondance, FAIS CONFIRMER ==")
        for r in moyenne:
            print(f"  - {r['champ_client']!r} -> {r['correspondance_nomadia']} "
                  f"(score {r['score']}) : \"je devine que {r['champ_client']} "
                  f"correspond à {r['correspondance_nomadia']}, c'est bien ça ?\"")
        print()

    if aucune:
        print("== Aucune correspondance fiable — pose la question directement ==")
        for r in aucune:
            print(f"  - {r['champ_client']!r} : rien à déduire du nom, demande au client "
                  "ce que c'est et où ça se range (entité, contrainte, ou hors périmètre).")
        print()

    print("Rappel : une correspondance 'haute' ou 'moyenne' reste une hypothèse issue du "
          "NOM du champ, jamais une garantie sur sa VALEUR ou son format réel — vérifie "
          "toujours un exemple de donnée réelle avant d'écrire le payload final (voir "
          "reference/entities.md pour le format attendu par champ).")


def cmd_vocabulary(args: argparse.Namespace) -> None:
    for entity_key, synonyms in VOCABULARY.items():
        print(f"{entity_key}:")
        print(f"  {', '.join(synonyms)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rapprochement entre les champs du code/schéma client et le modèle "
                     "Nomadia self-service — aide l'agent à ne questionner le client que "
                     "sur ce qui reste réellement ambigu."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_match = sub.add_parser("match", help="rapproche une liste de champs client du modèle Nomadia")
    p_match.add_argument("--input", required=True, help="fichier JSON : liste de chaînes (champs client)")
    p_match.set_defaults(func=cmd_match)

    p_vocab = sub.add_parser("vocabulary", help="affiche le dictionnaire de synonymes utilisé")
    p_vocab.set_defaults(func=cmd_vocabulary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
