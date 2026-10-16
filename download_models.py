import hashlib
import json
import os
from huggingface_hub import hf_hub_download
from studio.paths import ROOT, DATA, MODELS, configure

configure()
lock = json.loads((ROOT / 'model-lock.json').read_text(encoding='utf-8-sig'))
ledger_path = DATA / 'models-verified.json'
old = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
verified = []
for item in lock['files']:
    print('Model file:', item['file'], flush=True)
    target = hf_hub_download(repo_id=lock['repo'], revision=lock['revision'], filename=item['file'],
                             local_dir=str(MODELS), token=os.environ.get('HF_TOKEN') or False)
    from pathlib import Path
    path = Path(target)
    stat = path.stat()
    cached = next((entry for entry in old.get('files', []) if entry['file'] == item['file']), {})
    if not (stat.st_size == item['size'] and cached.get('mtime_ns') == stat.st_mtime_ns and cached.get('sha256') == item['sha256']):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024**2), b''):
                digest.update(block)
        if stat.st_size != item['size'] or digest.hexdigest() != item['sha256']:
            raise RuntimeError('Model integrity check failed: ' + item['file'])
    verified.append({**item, 'mtime_ns': stat.st_mtime_ns})
ledger_path.write_text(json.dumps({'revision': lock['revision'], 'files': verified}, indent=2), encoding='utf-8')
print('All model checks passed.', flush=True)
