# Découverte structurée du besoin — avant d'écrire le moindre payload

**Pourquoi ce fichier.** Une conversation guidée sur 4 thèmes (entités, contraintes,
objectifs, taille du problème), qui suit une "couverture" du besoin et ne génère le
document de spec (le PRD) qu'une fois cette couverture suffisante — plutôt qu'un
formulaire ou une liste de questions posées d'un bloc. Ce skill va plus loin que cette
méthode générique : il peut **lire le code existant du client** (§0 Étape 1 de
`SKILL.md`) avant même de poser une question, et doit trancher explicitement entre
**deux offres Nomadia** (self-service vs complète).

Ce fichier s'applique quel que soit l'agent qui exécute le skill (Claude Code, Cursor,
Codex, ChatGPT avec accès fichiers, ou autre) — rien ici ne suppose un outil précis,
seulement la capacité de lire des fichiers, poser des questions, et exécuter des
commandes.

## Les 4 thèmes de découverte

Avant d'écrire un payload, confirme avoir une réponse (déduite du code, ou obtenue par
une question groupée — jamais un interrogatoire pas à pas) sur chacun des 4 thèmes
suivants. Ne redemande jamais ce que l'inspection du code a déjà révélé.

### 1. Entités — qui/quoi est planifié

- Quelles **ressources** (techniciens, véhicules, équipes) ? Combien, à peu près ?
  Y a-t-il plusieurs profils/catégories (ex. "électricien" vs "technicien standard") ?
- Quelles **interventions/jobs** ? Combien par jour/semaine, à peu près (voir thème 4) ?
  Ont-elles des durées variables selon le type d'intervention (→ `JobType`) ?
- Quels **lieux** ? Sont-ils déjà géocodés (lat/lng) dans le système du client, ou
  faut-il géocoder (`POST /geocode`) ?

**Mapper sur le code existant** : si le client a déjà une table "interventions", une
table "techniciens"/"véhicules", un modèle d'adresses — c'est ça qui deviendra
`jobs`/`resources`/`locations`. Le but de cette section n'est pas de redemander ces
infos si elles sont déjà visibles dans le repo (§0 Étape 1 de `SKILL.md`), mais de
vérifier explicitement ce mapping avec le client avant d'écrire le payload (" je vois
une table `interventions` avec les champs X/Y/Z, je la mappe sur `Job` comme ça,
confirme ").

### 2. Contraintes — dures vs souples

Distinguer explicitement les deux, ce que les clients ne font pas toujours
spontanément :
- **Dures** (doivent être respectées, sinon le plan est inacceptable) : compétence
  obligatoire (`requirements`), ressource déjà engagée (`fixed_resource_id`),
  indisponibilité connue (`resources[].unavailabilities[]`). En self-service, c'est
  à peu près tout ce qu'on a — voir §3.
- **Souples** (influencent le plan mais peuvent être arbitrées) : préférer finir tôt
  dans une fenêtre (`sla.penalty_per_hour`), limiter le nombre de ressources mobilisées
  (`shift_penalty`), regrouper par secteur (`locality`).

Si le client mentionne une contrainte qui ressemble à "job multi-ressources", "stock de
pièces", "ordre entre deux interventions", "disponibilité qui se répète chaque
semaine", ou "horizon de planification à ne pas dépasser" — c'est un signal direct
vers le thème 3 (niveau d'offre), pas vers une modélisation self-service à inventer.

### 3. Objectifs — quels KPIs prioriser

Voir `reference/kpis-metier.md` pour la traduction technique → business. Demander
lequel compte le plus pour CE client, car les leviers peuvent se concurrencer
(ex. "limiter le nombre de techniciens" via `shift_penalty` haut peut dégrader le taux
d'allocation si la capacité devient insuffisante) :
- Taux d'allocation (aucun job perdu) ?
- Trajet/coût minimal ?
- Respect strict des rendez-vous/SLA (voir l'avertissement `value_per_hour` — §2bis de
  `SKILL.md`) ?
- Nombre de ressources mobilisées minimal ?

### 4. Taille du problème — et son impact direct sur le coût et le choix d'outil

Combien de jobs et de ressources, à peu près, dans le cas réel (pas juste un test) ?
Cette réponse change concrètement ce qu'on fait ensuite :
- **Petit volume (quelques jobs/ressources)** : écrire le payload à la main à partir
  d'un exemple de `examples/`.
- **Gros volume (des dizaines/centaines de jobs)** : utiliser
  `scripts/generate_load_test.py` plutôt que d'écrire à la main — et **annoncer le
  coût maximum estimé avant de générer quoi que ce soit** (`5 + ressources × jobs`
  crédits, voir le script). Ne jamais lancer l'appel réel sans acceptation explicite
  de ce coût.
- Le volume réel influence aussi la crédibilité d'une démo : un POC à 3 jobs ne prouve
  rien sur un vrai volume de production — le dire au client si c'est le cas.

## Niveau d'offre — self-service ou complète ? Trancher explicitement, sans jamais arrêter la conversation

**Règle impérative** : dès que le thème 2 (contraintes) ou 1 (entités) fait apparaître
un besoin qui correspond à un mécanisme listé dans
`reference/offre-complete-nomadia.md` (job multi-ressources/binôme, stock de pièces
embarqué, ordre obligatoire entre jobs, horizon de planification borné, disponibilité
vraiment récurrente, priorité de rendez-vous dédiée), **mène l'entretien exactement
comme si tu visais l'offre complète** — ne réduis jamais le périmètre des questions
suivantes à cause de ça, et **pose la question du niveau d'offre explicitement**
(jamais une supposition), mais sans que ça interrompe la conversation :

> "Ce que tu décris ([reformuler le besoin]), on sait le gérer — ça fait partie de
> l'offre complète Nomadia, qui demande juste qu'on te mette en contact avec leur
> équipe projet. On continue sur le reste du besoin, et je te montrerai aussi à quoi ça
> ressemble concrètement."

Ne jamais :
- supposer que le client est forcément en self-service seulement parce que c'est ce
  que ce skill peut appeler directement ;
- essayer d'encoder un mécanisme de l'offre complète dans un payload self-service pour
  "voir si ça marche" (il sera silencieusement ignoré — voir `reference/entities.md`) ;
- répondre "ce n'est pas possible" ou présenter le self-service comme une version
  dégradée/de repli — toujours une capacité qu'on gère, jamais une limite qui bloque ;
- s'arrêter ou suspendre l'entretien en attendant que le client tranche self-service vs
  offre complète — continuer à recueillir le reste du besoin dans le même mouvement, et
  montrer l'exemple offre complète (`reference/offre-complete-nomadia.md`) sans pour
  autant cesser d'avancer sur les autres thèmes.

Si le besoin du client ne touche **aucun** mécanisme de l'offre complète, pas besoin de
poser la question — rester sur self-service par défaut (c'est ce que la clé de test
donne, et c'est suffisant pour la très grande majorité des besoins de planification
simples/moyens).

## Checklist de couverture — avant d'écrire le payload

Un suivi de couverture adapté à une checklist binaire plutôt qu'un pourcentage (plus
simple à vérifier soi-même) :

- [ ] Entités identifiées (ressources, jobs, lieux) et mappées sur le modèle de données
      existant du client si un repo est ouvert
- [ ] Contraintes dures listées, et confirmées comme self-service ou offre complète
- [ ] Objectif business prioritaire connu (pour orienter `recommend_improvements.py`
      ensuite, pas pour bloquer l'écriture du payload)
- [ ] Taille du problème connue, au moins en ordre de grandeur
- [ ] Niveau d'offre tranché explicitement si un mécanisme offre-complète a été évoqué
- [ ] Clé API confirmée comme appartenant au client (voir `ONBOARDING.md` §2 /
      `SKILL.md` §-1) — uniquement nécessaire avant un appel réel, pas avant d'écrire
      le payload

Une fois ces points couverts, passer à l'Étape 3 de `SKILL.md` (écriture du payload,
validation, appel réel).
