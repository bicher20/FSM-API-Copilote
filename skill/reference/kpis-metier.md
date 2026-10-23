# KPIs métier — traduire le technique en argument business

Ni un prospect en rendez-vous commercial, ni une équipe opérationnelle qui suit sa
propre performance, ne raisonnent en champs JSON. Ce fichier traduit chaque paramètre
ou résultat technique du Scheduler API en indicateur business — à double usage :

- **Côté vente/avant-vente** : argumenter face à un prospect sans paraître purement
  technique (c'est le sens d'origine des formulations ci-dessous).
- **Côté client déjà équipé** : suivre sa propre performance de planification dans le
  temps — chaque section se relit aussi comme "comment surveiller ce chiffre chez moi"
  plutôt que "comment l'utiliser pour convaincre quelqu'un d'autre".

## 1. Taux d'allocation

**Ce que c'est** : part des jobs réellement planifiés sur une ressource, parmi tous les
jobs soumis.

**Comment le calculer** : `allocations.length / jobs.length` sur la réponse `/api/schedule`.

**Argument business** : un taux < 90% signifie qu'un planificateur humain devrait
rattraper à la main chaque jour les jobs non planifiés — c'est du temps perdu et un
risque de rendez-vous client oublié. Creuser `unallocated_job_reasons` (voir
`troubleshooting.md` §2) pour savoir si c'est un problème de capacité réelle (pas assez
de ressources) ou de contrainte mal configurée (SLA trop strict, compétence
sur-spécifiée).

## 2. Temps de trajet / temps utile

**Ce que c'est** : ratio entre la somme des `Travel` (temps de déplacement) et la somme
des durées de job effectivement réalisées.

**Argument business** : c'est l'indicateur qui vend le mieux l'optimisation de tournées
— un technicien qui passe 40% de sa journée sur la route au lieu de 20% coûte cher en
masse salariale pour la même production. C'est souvent le premier chiffre qu'un
prospect peut comparer à sa situation actuelle (estimée) sans outil.

## 3. Respect des SLA / fenêtres de rendez-vous

**Ce que c'est** : part des jobs planifiés dans la fenêtre horaire acceptée par le
client final (voir `SLA`, `JobAvailability`).

**Argument business** : un rendez-vous client raté ou en dehors de la fenêtre promise
est un coût de réputation, pas juste un coût opérationnel. C'est l'argument à utiliser
face à un prospect qui a une activité avec forte exigence client (santé à domicile,
livraison premium, installation).

## 4. Charge par ressource (équilibrage)

**Ce que c'est** : écart entre la ressource la plus chargée et la moins chargée sur une
journée/semaine planifiée (somme des durées de job allouées par `resource_id`).

**Argument business** : un déséquilibre important indique soit une sous-utilisation de
certaines ressources (coût fixe payé pour rien), soit une surcharge d'autres
(risque RH, turnover, erreurs liées à la fatigue).

## 5. Coût en crédits vs coût de planification manuelle

**Ce que c'est** : coût API par appel = `5 + (nb_ressources × nb_jobs_planifiés)` crédits
(voir Quick Start). À mettre en face du temps humain qu'un planificateur passerait à
faire la même chose à la main.

**Argument business** : c'est l'argument ROI direct. Exemple de calcul à faire en
rendez-vous : pour 10 ressources et 50 jobs/jour, un appel coûte `5 + 10×50 = 505`
crédits — à comparer au tarif du plan d'abonnement du prospect pour estimer un coût par
jour planifié, puis à mettre en face du temps qu'un planificateur humain y passerait
(souvent 30 min à 2h/jour selon la complexité).

## 6. Stabilité du plan (résultats incohérents entre deux appels identiques)

**Ce que c'est** : deux appels avec le même payload exact donnent des allocations
différentes (voir `troubleshooting.md` §5 — souvent dû à des contraintes
sous-déterminées, plusieurs solutions équivalentes existent).

**Argument business** : un prospect qui a déjà testé un outil d'optimisation et qui a
été déçu mentionne souvent "ça change tout le temps sans raison" — c'est un signal pour
creuser si le problème vient d'un payload sous-contraint plutôt que de l'outil
lui-même, et une bonne occasion de montrer qu'on sait diagnostiquer plutôt que de
promettre une solution magique.
