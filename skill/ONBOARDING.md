# Démarrage rapide — pour un client qui reçoit ce skill

## 0. Environnements disponibles

**⚠️ Confirmé directement par Nomadia le 23/10/2026 — versions explicitement
annoncées comme non définitives à cette date, à revérifier avant toute mise en
production.**

| Environnement | Portail (obtenir/gérer sa clé API) | API |
|---|---|---|
| **Test** (actif) | https://scheduler-api-test.nomadia-app.com/dashboard | https://scheduler-api-test.nomadia-app.com/api |
| **Prod** (**pas encore actif**) | https://scheduler-api.nomadia-app.com/dashboard | https://scheduler-api.nomadia-app.com/api |

**Utiliser l'environnement de test pour tout développement/démo tant que la prod
n'est pas confirmée active** — cibler le domaine prod aujourd'hui échoue avec une
erreur DNS (`Name or service not known`), pas une erreur d'authentification : ce
n'était pas un problème de clé ni de payload, le domaine prod n'a simplement pas
encore de service actif derrière.

`snippets/client.py` et `client.js` ciblent le test par défaut, surchargeable via la
variable d'environnement `NOMADIA_BASE_URL` (utile le jour où la prod devient active).

Ce document couvre tout le trajet entre "je viens de recevoir ce dossier" et "j'ai une
vraie réponse de l'API entre les mains". Si tu es un agent IA qui découvre ce skill
pour la première fois dans une conversation, suis ces étapes toi-même avec
l'utilisateur plutôt que de les réexpliquer de zéro.

## 1. Installer le skill

Selon l'agent IA utilisé :

**Claude Code :**
```bash
mkdir -p ~/.claude/skills
cp -r skill ~/.claude/skills/nomadia-scheduler-api
```
Le skill n'est visible qu'au **prochain démarrage** de l'agent — pas dans la session
en cours au moment de la copie.

**Cursor / autre agent** : copier le dossier `skill/` à l'endroit où cet agent
cherche ses skills/règles/contexte (voir sa propre documentation) — le contenu de
`SKILL.md` et des fichiers qu'il référence reste valable quel que soit l'agent (voir
la note "agent-agnostique" en tête de `SKILL.md`).

## 2. Configurer sa clé API Nomadia

1. Obtenir une clé sur le portail Nomadia Scheduler (essai ou abonnement).
2. **Ne jamais l'écrire en dur dans un fichier**, surtout pas dans un fichier qui
   pourrait être commité ou partagé. La charger en variable d'environnement avant
   chaque session de travail :
   ```bash
   export NOMADIA_API_KEY="ta_clé_ici"
   ```
3. Si la clé a été partagée une fois en clair (dans un chat, un email...), la
   considérer comme compromise et la régénérer sur le portail Nomadia après usage.

## 3. Premier test — sans consommer de crédits

Avant tout appel réel, vérifier qu'un payload d'exemple est valide et voir à quoi
ressemblent les recommandations :
```bash
python3 skill/scripts/doctor.py skill/examples/01_minimal.json
```
Ça ne fait aucun appel réseau — uniquement de la validation locale + des
recommandations basées sur la configuration.

## 4. Premier vrai appel API

```bash
python3 -c "
import os, json, urllib.request, urllib.error

key = os.environ['NOMADIA_API_KEY']
with open('skill/examples/01_minimal.json') as f:
    payload = json.load(f)
payload.pop('_comment', None)

req = urllib.request.Request(
    'https://scheduler-api-test.nomadia-app.com/api/schedule',
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'x-api-key': key},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print('HTTP', resp.status)
        body = resp.read().decode('utf-8')
        with open('/tmp/nomadia_response.json', 'w') as out:
            out.write(body)
        print('Sauvegardé dans /tmp/nomadia_response.json')
except urllib.error.HTTPError as e:
    print('HTTP ERROR', e.code)
    print(e.read().decode('utf-8', errors='replace')[:1000])
except urllib.error.URLError as e:
    print('URL ERROR', e.reason)
"
```

Puis analyser le résultat avec les recommandations :
```bash
python3 skill/scripts/doctor.py skill/examples/01_minimal.json --response /tmp/nomadia_response.json
```

## 5. Et après ?

- Besoin métier réel à modéliser → `SKILL.md` §0 (la procédure complète) et
  §-1bis/étape 2bis pour mapper l'objectif client à la configuration à activer.
- Un exemple proche de ton cas d'usage → `examples/README.md`.
- Une erreur ou un résultat inattendu → `troubleshooting.md`.
- Un problème avec le skill lui-même → voir `FEEDBACK.md` (hors de ce dossier,
  fourni séparément par la personne qui t'a donné ce skill).

## Environnement sans accès réseau externe

Si l'agent IA tourne dans un environnement cloud/sandbox qui bloque les appels HTTPS
sortants vers des domaines externes (proxy avec liste blanche), l'étape 4 échouera
avec une erreur réseau (ex. `502`, `connection refused`) même avec une clé valide et un
payload correct. Ce n'est pas un problème de configuration du skill — faire l'appel
réel depuis un poste/environnement qui a un accès réseau normal.

## Erreur DNS ("Name or service not known" / "could not resolve host")

**Cause la plus probable : tu cibles encore le domaine prod
(`scheduler-api.nomadia-app.com`) alors qu'il n'est pas encore actif** — vérifie
d'abord que tu utilises bien `scheduler-api-test.nomadia-app.com` (voir §0
ci-dessus). C'est ce qui s'est produit lors des premiers tests de ce skill : la
même erreur DNS a été reproduite, et Nomadia a confirmé par email que la prod n'était
simplement pas encore activée.

Si l'erreur persiste malgré le bon domaine (test), vérifier avec un résolveur public :
```bash
dig @1.1.1.1 scheduler-api-test.nomadia-app.com
# ou si dig n'est pas installé :
nslookup scheduler-api-test.nomadia-app.com 1.1.1.1
```
Si ça ne résout toujours rien, le problème est local (VPN, proxy d'entreprise,
filtrage réseau, `/etc/hosts`) — essayer depuis un autre réseau (partage de connexion
mobile, par exemple) pour confirmer.
