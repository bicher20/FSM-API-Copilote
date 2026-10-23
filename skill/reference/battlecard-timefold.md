# Battlecard — Nomadia vs Timefold (solveurs généralistes)

Argumentaire factuel pour une conversation commerciale où un prospect compare Nomadia
à Timefold (ou un solveur généraliste équivalent : OptaPlanner, Google OR-Tools...).
Basé sur la documentation publique de Timefold au 23/10/2026 — à revérifier si le
prospect cite un chiffre/plan précis, les offres évoluent.

## 1. Barrière technique à l'intégration

**Timefold** : le Solver open source (gratuit) s'utilise en **Java ou Kotlin
uniquement** — il faut écrire soi-même les contraintes en code (`ConstraintProvider`,
API façon Streams). Les quickstarts officiels sont tous Java/Kotlin (Quarkus, Spring
Boot) ; aucune API REST language-agnostic n'est documentée pour la version open
source. [docs.timefold.ai/quickstart/overview](https://docs.timefold.ai/timefold-solver/1.x/quickstart/overview)

**Nomadia** : API REST JSON pure, un seul `POST /api/schedule`, utilisable depuis
**n'importe quel langage** qui sait faire du HTTP (déjà prouvé dans ce skill :
`snippets/client.js` et `client.py`). Pas de JVM, pas de code de contrainte à écrire —
la configuration se fait par données (JSON), pas par développement.

**Argument** : pour un prospect sans équipe Java dédiée (la majorité des PME/ETI
field service), Nomadia réduit le temps d'intégration de plusieurs semaines de
développement à quelques jours d'intégration API.

## 2. Accès et pricing

**Timefold** : la version hébergée/API ("Timefold Platform" — Spark / Flow /
Horizon) est **100% "contact sales"** sur les trois tiers, aucun prix public, aucun
essai en self-service documenté pour cette offre.
[timefold.ai/pricing](https://timefold.ai/pricing)

**Nomadia** : essai en self-service, clé API obtenue directement via le portail,
pricing transparent et prévisible en crédits (`5 + nb_ressources × nb_jobs_planifiés`
par appel — voir `SKILL.md` §2).

**Argument** : un prospect peut tester Nomadia aujourd'hui sans attendre un cycle de
vente côté fournisseur. C'est un argument de vitesse, pas juste de prix.

## 3. Géocodage inclus

**Nomadia** : `/api/geocode` dans la même API, même clé, même facturation.

**Timefold** : seule l'offre "Spark" (déjà "contact sales") mentionne des "matrices de
temps de trajet et distance intégrées" — rien sur le géocodage d'adresses lui-même.

**Argument** : un fournisseur, une intégration, une facture — pas de brique
supplémentaire à acheter/intégrer ailleurs.

## 4. Ce que Timefold fait mieux (à reconnaître honnêtement)

- **Échelle** : l'édition Enterprise annonce un support jusqu'à 500 000 jobs/shifts.
  Si le prospect a un volume massif (logistique nationale, pas field service PME),
  creuser ce point sérieusement plutôt que botter en touche.
- **Explicabilité native** : "score analysis", "constraint profiling" existent
  nativement chez Timefold (tiers payants) — chez Nomadia, c'est reconstruit via
  `scripts/recommend_improvements.py` et `troubleshooting.md` de ce skill, pas natif à
  l'API. Dire clairement que c'est un outillage qu'on apporte, pas une fonctionnalité
  du fournisseur.
- **Solver open source gratuit** : pour une équipe qui a déjà des devs Java capables
  d'écrire des contraintes, le Solver communautaire est gratuit et très flexible —
  c'est un vrai concurrent si le prospect a cette compétence en interne et veut tout
  maîtriser en code.
- **What-if / scénarios avancés** : l'offre "Horizon" documente des fonctionnalités
  (what-if scenarios, trafic temps réel) plus poussées que ce que Nomadia expose
  nativement — `scripts/compare_scenarios.py` dans ce skill couvre une partie du
  besoin mais reste plus basique.

## 5. Objections fréquentes et réponses

**"Timefold est open source, donc gratuit"** → le *solver* est gratuit, mais il faut
une équipe Java pour l'opérer, l'héberger, le maintenir. Le coût réel n'est pas la
licence, c'est le développement + l'infra. Nomadia facture l'usage mais inclut tout
l'hébergement et l'optimisation.

**"Timefold est plus précis/plus scientifique"** → le moteur peut être très bon sur de
gros volumes, mais rien dans leur doc publique ne démontre une supériorité pour un
field service de taille PME/ETI — l'essentiel du gain vient de la configuration
(contraintes, SLA, pénalités) bien posée, pas du moteur seul. C'est justement ce que
`SKILL.md` §0 étape 2bis et `scripts/recommend_improvements.py` encadrent côté Nomadia.

**"On veut comparer les deux avant de choisir"** → proposer un POC chiffré avec
`scripts/compare_scenarios.py` sur les vrais jobs/ressources du prospect plutôt qu'un
débat théorique — l'argument le plus solide est un chiffre produit sur leurs données.
