"""Copy the two custom skills into an explicitly selected agent skills folder."""
from pathlib import Path
import argparse
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
NAMES=('cartoon-blender-production','cartoon-visual-qa')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dest',type=Path,required=True,help='Your project .agents/skills directory or another chosen skill directory')
parser.add_argument('--dry-run',action='store_true')
args=parser.parse_args()
dest=args.dest.expanduser().resolve()
for name in NAMES:
    if not (ROOT/'skills'/name/'SKILL.md').is_file():
        parser.error('Incomplete source skill: '+name)
    if (dest/name).exists():
        parser.error('Target already exists; select another destination: '+str(dest/name))
if not args.dry_run:
    dest.mkdir(parents=True,exist_ok=True)
    for name in NAMES:
        shutil.copytree(ROOT/'skills'/name,dest/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
print(json.dumps({'dry_run':args.dry_run,'skills':list(NAMES),'destination':str(dest)},ensure_ascii=False,indent=2))
