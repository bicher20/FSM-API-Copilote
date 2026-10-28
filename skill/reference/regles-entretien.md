# Règles de conduite de l'entretien — à lire avant de mener le premier entretien

Ce fichier détaille ce que `SKILL.md` §0ter résume. S'applique à tout entretien mené
via `reference/sections.json` + `scripts/interview_state.py`, quel que soit l'agent qui
l'exécute (Claude Code, Cursor, Codex, ChatGPT, ou autre).

## 1. Une question à la fois, dans les mots du client, sur un ton naturel

Jamais de jargon technique à ce stade ("job", "resource", "payload", `requirements`) —
ces mots arrivent plus tard, quand on construit. Pendant l'entretien, on parle
"intervention", "technicien", "rendez-vous", "secteur". Une seule question posée à la
fois (`sections.json[].opening_question` pour ouvrir une section), jamais une liste de
5 questions d'un coup — c'est ce qui distingue un entretien d'un formulaire.

Le ton compte autant que le contenu : les `opening_question` de `sections.json` sont
déjà écrites de façon conversationnelle (pas "Section 3 : objectifs — merci de
répondre"), reprends-les telles quelles ou dans le même esprit si tu les reformules —
jamais un ton de formulaire administratif, même pressé. `options <section>` affiche
TOUJOURS un dernier numéro explicite "Autre chose à préciser" en plus des choix QCM —
présente-le comme un vrai choix de la liste au client (pas une note en petit en bas),
c'est littéralement une case à cocher pour "je veux ajouter du contexte".

Chaque section ne porte qu'UN seul sujet : le thème "entités" est volontairement scindé
en 4 sections successives (`entites_ressources`, `entites_interventions`,
`entites_lieux`, `entites_donnees`) plutôt qu'un seul QCM de 9 choix mélangeant qui est
planifié, combien de temps ça dure, où c'est, et quelles données existent déjà — ça
évite au client de se retrouver devant un mur de cases sans rapport entre elles. Garde
ce principe si tu ajoutes un jour une nouvelle question : une section = un sujet, pas
un fourre-tout.

## 1bis. Les choix non pertinents se masquent seuls — ne les redemande pas, n'en invente pas

`scripts/interview_state.py options <section>` filtre déjà automatiquement les options
devenues sans objet d'après ce que le client a répondu plus tôt (`sections.json:
options[].depends_on`) — ex. pas de question "plusieurs techniciens en même temps
(binôme)" si aucun technicien/équipe n'a été identifié en section "entités", pas de
"mobiliser moins de techniciens" en objectifs dans ce cas non plus. **Toujours appeler
`options <section>` avec `--interview ID`** (ou laisser le défaut si un seul entretien
est en cours) pour bénéficier de ce filtrage — jamais afficher une liste figée de
mémoire ou décidée par ton propre jugement : c'est le script qui sait ce qui a déjà été
répondu, pas toi. Si le client mentionne spontanément quelque chose qui a été masqué
(ex. il a des équipes en réalité, sans l'avoir coché en "entités"), c'est le signal pour
revenir corriger la section "entités" (`edit` ou un nouveau `record`) avant de continuer
— jamais court-circuiter le filtrage en passant l'id masqué à la main sans corriger la
cause. Ce mécanisme ne retire JAMAIS les options de "niveau_offre" liées à la clé
API/au suivi de crédits : ces critères sont obligatoires quel que soit le contexte.

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
plus") avant de clore la section. **Reformule, ne répète jamais la même phrase mot pour
mot** : dis précisément ce qui manque encore (le critère exact affiché par le script),
pas juste "peux-tu préciser ?" — le client doit comprendre immédiatement quoi ajouter
sans avoir à relire toute la question d'ouverture. Si le client ne sait vraiment pas
répondre à un critère (ex. volume réel pas encore connu), note-le comme tel dans le PRD
plutôt que de deviner une valeur à sa place — un "pas encore su" honnête vaut mieux
qu'un chiffre inventé qui orientera mal la construction du payload ensuite.

## 4bis. Réponse qui ne correspond pas à la question posée

Si la réponse du client ne répond manifestement pas à ce qui a été demandé (ex. un
chiffre de durée alors que la question portait sur un volume, un numéro de QCM hors de
la plage affichée), ne l'enregistre pas comme si elle couvrait le critère visé. Dis
explicitement que cette réponse ne correspond pas à la question (jamais en silence,
jamais en la forçant dans le critère le plus proche), répète la question sous une autre
forme si besoin, puis passe au point suivant si le client ne peut vraiment pas préciser
— voir §4 ci-dessus pour noter honnêtement un point resté sans réponse.

## 5. "Parler de cette section" — rouvrir une section déjà couverte

Le client peut à tout moment demander à revenir sur une section déjà marquée ● : propose
toujours cette option explicitement dans ta reformulation de clôture ("on peut aussi
revenir sur [section] plus tard si besoin"). Pour rouvrir : `record` normalement sur
cette section (ça ajoute un tour), et si la nouvelle réponse invalide un critère déjà
marqué couvert, `--unmark-criterion` avant de re-couvrir avec la bonne info.

## 5bis. "Ce qui est planifié" et la séparation non-négociable/souple

Au moment de `prd`, passe `--summary "<une ou deux phrases>"` résumant QUOI est
planifié et QUI exécute (ex. "les visites client, affectées à un technicien, un ordre
et un horaire ; les techniciens, dont la disponibilité varie") — ça s'affiche en tête
du PRD, avant le détail section par section, pour que le client retrouve l'essentiel
en un coup d'œil.

En plus (ou à la place) du `--summary` en texte libre, utilise `--entity "Nom|Statut|
Description"` (répétable, une fois par entité) pour une liste structurée par entité —
ex. `--entity "Interventions client|Planifiées|affectées à un technicien, un ordre et
un horaire" --entity "Techniciens|Disponibilité|réalisent les interventions, avec
compétences, secteur et indisponibilités variables"`. N'invente jamais le statut ou la
description d'une entité à partir des seuls labels QCM — écris-les toi-même d'après ce
que le client a réellement confirmé pendant l'entretien (section "entités" en premier
lieu, affinée par les contraintes/objectifs qui s'y rattachent).

La section "contraintes" distingue déjà automatiquement non-négociable / souple dans le
rendu de sa propre section (grâce aux choix QCM). Le PRD se termine en plus par un
**récapitulatif global** "Non négociable" / "Nice to have" qui agrège ces choix
("contraintes") avec les objectifs priorisés (section "objectifs", toujours classés
nice-to-have — un KPI n'est jamais une contrainte dure) en deux listes uniques, tous
thèmes confondus — rien à construire à la main pour ça, le script le fait depuis les
options QCM déjà enregistrées.

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
- lance `scripts/interview_state.py score` : si "offre complète requise" apparaît
  (contraintes citées qui dépassent le self-service, mais niveau d'offre non confirmé
  en offre complète), note-le dans le PRD pour que ce soit visible au moment de
  construire — jamais avancer en silence sur une hypothèse. Mais ce n'est **jamais un
  motif pour s'arrêter ou réduire l'entretien** : mène toujours la découverte du besoin
  comme si tu visais l'offre complète, questions comprises, quel que soit le niveau
  d'offre du client. Au client lui-même, présente ce point positivement, jamais comme
  une limite — ex. "ça, on sait très bien le gérer, il faudra juste qu'on te mette en
  contact avec l'équipe Nomadia pour l'offre complète" — et continue la conversation
  normalement derrière ;
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
