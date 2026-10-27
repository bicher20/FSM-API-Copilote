#!/usr/bin/env python3
"""
Package le skill pour remise à un client — exécutable en CLI, sans dépendance.

Automatise la checklist de distribution du README (section "Distribuer ce skill à un
client") : copie `skill/` dans `dist/`, retire les caches Python, et produit un .zip
prêt à envoyer, nommé avec la version exacte du skill — pour toujours savoir ce qu'un
client donné a réellement reçu si un problème remonte.

Le matériel strictement interne (ex: argumentaire commercial vs Timefold) vit dans
`internal/` à la racine du repo, PAS dans `skill/` — donc il n'est jamais copié ici
par construction, même si ce script n'est pas utilisé (ex: un agent qui clone le repo
et copie `skill/` directement). EXCLUDE_RELATIVE_PATHS ci-dessous reste un filet de
sécurité si un fichier interne finissait un jour par erreur dans `skill/`.

Usage :
    python3 scripts/package_for_client.py
    python3 scripts/package_for_client.py --client "Acme Logistique"

Sortie : dist/<slug>-v<version>/  (dossier)  et  dist/<slug>-v<version>.zip  (archive)
"""
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skill"
DIST_DIR = REPO_ROOT / "dist"

# Filet de sécurité : si un fichier interne finissait un jour par erreur dans skill/
# (au lieu de internal/, où il devrait être), il serait quand même exclu ici.
EXCLUDE_RELATIVE_PATHS: set[str] = set()
EXCLUDE_DIR_NAMES = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc"}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "nomadia"


def read_skill_version() -> str:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(.+)$", text, re.MULTILINE)
    if not m:
        print("[ERROR] impossible de lire 'version:' dans skill/SKILL.md")
        sys.exit(1)
    return m.group(1).strip()


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(SKILL_DIR).as_posix()
    if rel in EXCLUDE_RELATIVE_PATHS:
        return True
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def copy_skill(dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    copied, skipped = [], []
    for src in SKILL_DIR.rglob("*"):
        if src.is_dir():
            continue
        if should_exclude(src):
            skipped.append(src.relative_to(SKILL_DIR).as_posix())
            continue
        rel = src.relative_to(SKILL_DIR)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel.as_posix())
    return copied, skipped


def make_zip(folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in folder.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(folder.parent))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--client", default=None, help="nom du client (sert à nommer le package)")
    parser.add_argument("--out", default=str(DIST_DIR), help="dossier de sortie (défaut: dist/)")
    args = parser.parse_args()

    version = read_skill_version()
    base_name = slugify(args.client) if args.client else "nomadia"
    pkg_name = f"{base_name}-v{version}"

    out_dir = Path(args.out)
    pkg_dir = out_dir / pkg_name / "skill"
    zip_path = out_dir / f"{pkg_name}.zip"

    if pkg_dir.parent.exists():
        shutil.rmtree(pkg_dir.parent)

    copied, skipped = copy_skill(pkg_dir)
    make_zip(pkg_dir.parent, zip_path)

    print(f"Package : {pkg_dir.parent}")
    print(f"Archive : {zip_path}")
    print(f"Version du skill : {version}")
    print(f"{len(copied)} fichier(s) copié(s), {len(skipped)} exclu(s) :")
    for s in skipped:
        print(f"  - exclu : {s}")
    print("\nRappel : fournir la clé API Nomadia au client séparément (jamais dans ce "
          "package), et noter le nom du client + la version envoyée pour le suivi.")


if __name__ == "__main__":
    main()
