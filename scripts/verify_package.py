"""Verify the distributed kit against PACKAGE-MANIFEST.json (stdlib only)."""
from pathlib import Path
import hashlib
import json
import sys

root=Path(__file__).resolve().parents[1]
path=root/'PACKAGE-MANIFEST.json'
if not path.exists():
    print('PACKAGE-MANIFEST.json is missing.',file=sys.stderr)
    raise SystemExit(1)
manifest=json.loads(path.read_text(encoding='utf8'))
bad=[]
for row in manifest['files']:
    target=(root/row['path']).resolve()
    if root not in target.parents:
        bad.append({'path':row['path'],'error':'outside package'})
    elif not target.is_file():
        bad.append({'path':row['path'],'error':'missing'})
    elif hashlib.sha256(target.read_bytes()).hexdigest()!=row['sha256']:
        bad.append({'path':row['path'],'error':'changed'})
print(json.dumps({'verified':not bad,'files':len(manifest['files']),'problems':bad},ensure_ascii=False,indent=2))
raise SystemExit(1 if bad else 0)
