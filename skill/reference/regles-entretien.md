# Règles de conduite de l'entretien — à lire avant de mener le premier entretien

Ce fichier détaille ce que `SKILL.md` §0ter résume. S'applique à tout entretien mené
via `reference/sections.json` + `scripts/interview_state.py`, quel que soit l'agent qui
l'exécute (Claude Code, Cursor, Codex, ChatGPT, ou autre).

## 1. Une question à la fois, dans les mots du client

Jamais de jargon technique à ce stade ("job", "resource", "payload", `requirements`) —
ces mots arrivent plus tard, quand on construit. Pendant l'entretien, on parle
"intervention", "technicien", "rendez-vous", "secteur". Une seule question posée à la
fois (`sections.json[].opening_question` pour ouvrir une section), jamais une liste de
5 questions d'un coup — c'est ce qui distingue un entretien d'un formulaire.

## 2. Reformuler avant de passer à la section suivante

Avant de clore une section (tous ses critères couverts) et d'ouvrir la suivante,
reformule ce que tu as compris en une phrase et fais confirmer : "Si je résume : [...],
c'est bien ça ?" — jamais d'enchaîner directement sur la question suivante sans ce
point de passage. C'est le moment où le client peut corriger quelque chose avant que ça
se fige dans le PRD.

## 2bis. Montrer l'avancement au client — jamais le laisser deviner où il en est

Chaque `record` affiche désormais un **avancement global** (pourcentage + nombre de
sections complètes sur le total) — une barre de progression du besoin, pas juste une
donnée interne. Ne garde jamais ce chiffre pour toi seul : partage-le au
client à un moment naturel — typiquement dans la phrase de clôture d'une section ("Bien
reçu, on tient le cadrage du planning — on est à environ 60% de l'ensemble, il reste la
taille réelle et le type de clé API à voir") — pas après chaque phrase isolée, ce qui
serait mécanique, mais au moins à chaque changement de section et explicitement à
l'approche du seuil ("on y est presque, encore un point et le PRD est prêt"). L'objectif
est que le client ressente une progression mesurable et naturelle, jamais qu'il se
demande "on en est où ?" ou "ça va durer encore longtemps ?".

## 3. Le client peut TOUJOURS corriger une réponse suggérée

Quand tu reformules ou que tu proposes une réponse probable à sa place (ex. "je devine,
d'après ton code, que tu as environ 10 techniciens — c'est ça ?"), c'est une
**suggestion à valider**, jamais une réponse définitive tant que le client ne l'a pas
confirmée explicitement. Trois issues possibles à chaque suggestion :
- il confirme tel quel → `record` normalement ;
- il corrige → enregistre directement la version corrigée avec `record` (pas besoin
  d'`edit` si rien n'a encore été enregistré sur ce point) ;
- une réponse déjà enregistrée plus tôt doit changer (il se rend compte après coup que
  ce qu'il a dit n'est plus exact, ou que ta suggestion était fausse) → utilise
  `scripts/interview_state.py edit <section> <turn_index> "<réponse corrigée>"` plutôt
  que d'ajouter un tour en plus, pour que le PRD final ne contienne pas deux versions
  contradictoires. Utilise `progress --verbose` pour retrouver l'index du tour à
  corriger.

Ne jamais insister sur une suggestion que le client vient de corriger, et ne jamais
reformuler une deuxième fois une réponse déjà confirmée "pour faire mieux" — ça ralentit
l'entretien sans raison.

## 4. Relancer si un critère n'est pas couvert, jamais l'inventer

Après chaque `record`, le script affiche les critères encore non couverts de la
section. Relance **spécifiquement sur ces points** (pas une question générique "dis-moi
plus") avant de clore la section. Si le client ne sait vraiment pas répondre à un
critère (ex. volume réel pas encore connu), note-le comme tel dans le PRD plutôt que de
deviner une valeur à sa place — un "pas encore su" honnête vaut mieux qu'un chiffre
inventé qui orientera mal la construction du payload ensuite.

## 5. "Parler de cette section" — rouvrir une section déjà couverte

Le client peut à tout moment demander à revenir sur une section déjà marquée ● : propose
toujours cette option explicitement dans ta reformulation de clôture ("on peut aussi
revenir sur [section] plus tard si besoin"). Pour rouvrir : `record` normalement sur
cette section (ça ajoute un tour), et si la nouvelle réponse invalide un critère déjà
marqué couvert, `--unmark-criterion` avant de re-couvrir avec la bonne info.

## 6. Le PRD ne s'écrit qu'au-dessus du seuil, ou sur demande explicite

`threshold_percent` dans `sections.json` (85% par défaut) est la barrière par défaut.
`scripts/interview_state.py prd` refuse en dessous sans `--force`. **`--force` ne
s'active que si le client demande explicitement le PRD malgré des sections
incomplètes** ("donne-moi quand même ce que tu as") — jamais sur ta propre initiative
pour aller plus vite. Le PRD généré sous le seuil liste quand même, section par
section, les points encore à clarifier — jamais caché.

## 7. Une fois le PRD généré : enchaîner sur le code, pas s'arrêter là

Le PRD n'est pas la fin de la mission, c'est l'étape avant la construction (voir §0 et
§2bis de `SKILL.md`). Une fois généré :
- relis ce que l'étape 1 de §0 a trouvé dans le code existant du client (modèle de
  données, stack, clé API déjà présente) ;
- construis le payload/code d'intégration à partir du PRD plutôt que de redemander au
  client ce qu'il vient de dire — chaque section du PRD correspond à une partie du
  payload (entités → `jobs`/`resources`/`locations`, contraintes → `requirements`/
  `sla`/`fixed_resource_id`, objectifs → `recommend_improvements.py` à lancer ensuite,
  niveau d'offre → ouvrir `reference/offre-complete-nomadia.md` si tranché "offre
  complète") ;
- si le code généré doit s'intégrer dans le projet du client (pas juste un payload
  JSON isolé), pars de `snippets/client.js`/`client.py` et du langage/stack déjà
  identifié à l'étape 1 — jamais une intégration générique déconnectée de ce qui existe
  déjà chez le client ;
- **avant le premier appel réel**, reviens sur la section "niveau d'offre" du PRD :
  confirme explicitement que la clé API utilisée appartient bien à CE client (jamais
  une clé qui traîne d'un autre compte/session — voir `ONBOARDING.md` §2 et `SKILL.md`
  §-1), et indique où suivre la consommation de crédits (portail Nomadia, dashboard) —
  surtout si le client a choisi l'option "je veux savoir comment suivre ma
  consommation" lors de l'entretien. Rappelle le coût d'un appel (`SKILL.md` §2 :
  5 + ressources × jobs crédits) avant de lancer quoi que ce soit qui consomme.
