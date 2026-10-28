# Le "cerveau" du skill — comprendre le code client avant de demander, vendre par la preuve

**Pourquoi ce fichier.** `SKILL.md` §0 Étape 1 dit déjà de regarder le code client
avant de poser une question. Ce fichier va plus loin : il décrit comment transformer ce
coup d'œil en **rapprochement systématique** (quel champ client = quel champ Nomadia,
avec un niveau de confiance explicite), et comment ne JAMAIS transformer ça en argument
commercial gonflé. Deux manières de perdre la confiance d'un client : lui redemander ce
que son propre code dit déjà, et lui promettre un gain qu'on n'a pas mesuré.

## 1. Exploiter l'agent qui exécute ce skill, pas juste poser des questions

Ce skill tourne toujours À L'INTÉRIEUR d'un agent de code (Claude Code, Cursor, Codex,
ou autre) qui a déjà accès à des outils de lecture/recherche sur le repo du client :
grep, lecture de fichier, inspection d'un schéma de base de données ou d'un modèle
ORM. **Utilise ces outils en premier**, avant d'écrire la moindre question au client :

1. Cherche les tables/modèles/entités qui ressemblent à des interventions, des
   techniciens/ressources, des lieux (migrations SQL, modèles Django/Rails/Prisma,
   schémas GraphQL, fichiers `types.ts`/`models.py`, etc.).
2. Extrais la liste des noms de colonnes/champs trouvés pour chacun (pas leur valeur,
   juste leur nom).
3. Passe cette liste à `scripts/match_data_model.py match --input <fichier.json>` (le
   fichier d'entrée est une simple liste JSON de chaînes que TU écris toi-même à partir
   de ce que tu as trouvé — ce script ne lit jamais le repo lui-même, c'est toi qui lui
   donnes la matière).
4. Le script répond avec un niveau de confiance par champ :
   - **Haute confiance** : ne redemande JAMAIS cette correspondance au client — annonce-
     la directement, dans la même phrase de raisonnement que tu utilises déjà
     (`reference/regles-entretien.md` §0) : "je vois une colonne `technicien_id` dans ta
     table interventions, je la mappe sur une `Resource` Nomadia — dis-moi si je me
     trompe." C'est une annonce suivie d'une porte de sortie, jamais une question fermée
     qui lui fait répéter ce que son code dit déjà.
   - **Confiance moyenne** : propose la correspondance MAIS fais confirmer
     explicitement avant de l'enregistrer dans le PRD — ne la traite jamais comme
     acquise tant que le client n'a pas dit oui.
   - **Aucune correspondance** : pose la question directement, il n'y a rien à déduire
     du nom du champ.
5. Dans tous les cas, le nom d'un champ ne dit rien de sa VALEUR réelle ni de son
   format — avant d'écrire le payload final, vérifie un exemple de donnée réelle (une
   ligne de la table, un exemple de réponse API existante) contre `reference/
   entities.md`, jamais seulement le nom de la colonne.

Ce mécanisme réduit directement le nombre de questions posées au client à ce qui est
*réellement* ambigu — c'est ça, "un vrai cerveau qui comprend la demande" : pas plus de
QCM, mais moins de questions inutiles parce que le code a déjà répondu à une partie.

## 2. Vendre par la preuve, jamais par la promesse

**Règle stricte, sans exception** : n'affiche jamais un pourcentage de gain, une
estimation de ROI, ou une formulation du type "ça réduit généralement vos coûts de X%"
si ce chiffre n'a pas été **mesuré sur un payload réel de CE client**, via un vrai appel
à l'API (test ou production). Pas de moyenne sectorielle, pas de benchmark générique,
pas de chiffre "habituellement observé" — un développeur ne livre pas un chiffre qu'il
n'a pas fait tourner, une bonne vente ne promet pas un résultat qu'elle n'a pas montré.

**Ce qui est autorisé, et qui est en réalité bien plus convaincant** :
- Une fois un payload réel exécuté pour ce client (volume réel ou représentatif), lire
  le résultat retourné par l'API (taux d'allocation, trajet/temps, heures sup) et le
  présenter TEL QUEL — "sur ton vrai volume, 5 interventions sur 5 ont été allouées,
  ratio trajet/temps de 91%" — un fait mesuré, jamais une promesse à l'avance.
- Pour montrer l'effet d'un objectif (ex. "limiter le nombre de techniciens mobilisés"),
  utilise `scripts/compare_scenarios.py` avec clé API (deux scénarios du même payload,
  un avec `shift_penalty` à 0 et un avec `shift_penalty` > 0) et cite le résultat
  renvoyé — "en activant ce levier sur TON payload, le nombre de ressources mobilisées
  est passé de 7 à 5" est un delta mesuré, pas une estimation. Ce mode consomme un
  appel réel par scénario : accord explicite du client avant de lancer, comme toujours
  pour un appel qui consomme (voir le script lui-même et `SKILL.md` §2). `scripts/
  recommend_improvements.py` aide à repérer quel levier tester en premier d'après
  l'objectif prioritaire du client.
- Ne jamais mentionner le coût en crédits comme argument de vente ou de comparaison —
  ce sujet reste strictement opérationnel : seule l'étape "avant un premier appel réel"
  de `reference/regles-entretien.md` §7 (confirmer la clé API, rappeler le coût d'un
  appel) en parle, et uniquement pour que le client ne soit jamais surpris par une
  consommation, jamais pour vendre quoi que ce soit.

**Conséquence sur l'enchaînement après le PRD** : dès que le volume du besoin est
raisonnable pour un test réel (voir `reference/decouverte-besoin.md` thème 4) et qu'une
clé API test est disponible, propose d'enchaîner directement sur un vrai appel plutôt
que de laisser le PRD comme seul livrable — "je peux te montrer ça tourner vraiment sur
ton cas plutôt que de te laisser juste le document, tu veux qu'on lance ça maintenant ?"
C'est la vraie différence avec un cahier des charges abstrait : on peut prouver, pas
juste décrire. Si le client préfère attendre, rien d'insistant — le PRD reste complet et
utilisable seul.

## 3. Penser comme un développeur ET comme une direction commerciale, en même temps

Chaque mécanisme détecté pendant l'entretien doit être évalué sur deux axes à la fois,
jamais un seul :
- **Faisabilité technique réelle** : ce mécanisme existe-t-il en self-service
  (`reference/entities.md`) ou seulement en offre complète (`reference/
  offre-complete-nomadia.md`) ? Quel champ exact, quel format, quel piège connu
  (`troubleshooting.md`) ?
- **Impact business pour CE client** : ce mécanisme répond-il à l'objectif qu'il a
  réellement priorisé (`reference/kpis-metier.md`), ou est-ce un détail secondaire
  qu'il a mentionné en passant ? Un développeur qui ignore cette question construit un
  payload techniquement correct mais qui ne résout pas le vrai problème du client ; une
  direction commerciale qui ignore la faisabilité promet quelque chose que l'API ne
  fait pas.

Dans l'ordre de ce que tu dis au client : la conséquence technique d'abord (ce que son
code/sa réponse implique), l'angle business ensuite, **jamais l'inverse** — annoncer un
bénéfice avant d'avoir vérifié que c'est techniquement faisable est exactement le genre
de promesse non tenue que ce fichier interdit en §2.
