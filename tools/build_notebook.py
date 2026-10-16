"""Embed only selected source files; no runtime GitHub token is needed."""
import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
names = ['app.py', 'run_job.py', 'bootstrap.py', 'download_models.py', 'launch_web.py',
         'requirements.txt', 'requirements-backend.txt', 'model-lock.json', 'runtime-lock.json']
names += sorted(str(path.relative_to(ROOT)).replace('\\','/') for path in (ROOT / 'studio').glob('*.py'))
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
    for name in names:
        entry = zipfile.ZipInfo(name, (2026, 10, 16, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o644 << 16
        # Canonical LF text keeps the embedded bundle identical on Windows/Linux.
        bundle.writestr(entry, (ROOT / name).read_text(encoding='utf-8-sig').encode('utf-8'))
payload = buffer.getvalue()
encoded = base64.b64encode(payload).decode()
digest = hashlib.sha256(payload).hexdigest()


def markdown(text):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': text.splitlines(keepends=True)}


def code(text, form=False):
    return {'cell_type': 'code', 'metadata': {'cellView': 'form'} if form else {},
            'source': text.splitlines(keepends=True), 'outputs': [], 'execution_count': None}


setup = '''#@title 1. Prepare the GPU and download MiniMax
import os, sys, json, io, base64, hashlib, zipfile, subprocess, signal
from pathlib import Path
ROOT = Path('/content/minimax-music-studio')
os.environ['MUSIC_DATA_DIR'] = '/content/minimax-runtime'
os.environ['MUSIC_OUTPUT_DIR'] = '/content/minimax-output'
os.environ['PIP_CACHE_DIR'] = '/content/minimax-runtime/cache/pip'
os.environ['PYTHONPYCACHEPREFIX'] = '/content/minimax-runtime/cache/pycache'
ROOT.mkdir(parents=True, exist_ok=True)
PAYLOAD = __PAYLOAD__
data = base64.b64decode(PAYLOAD)
assert hashlib.sha256(data).hexdigest() == '__DIGEST__', 'Notebook app bundle is damaged.'
allowed = set(__NAMES__)
with zipfile.ZipFile(io.BytesIO(data)) as bundle:
    assert set(bundle.namelist()) == allowed, 'Unexpected app bundle contents.'
    assert sum(item.file_size for item in bundle.infolist()) < 2_000_000
    for name in bundle.namelist():
        target = (ROOT / name).resolve()
        assert target.is_relative_to(ROOT.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bundle.read(name))
subprocess.run([sys.executable, str(ROOT / 'bootstrap.py')], cwd=ROOT, check=True)
python = Path(os.environ['MUSIC_DATA_DIR']) / 'venv/bin/python'
def run_owned(command, input_text=None, capture=False, env=None):
    process = subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=True,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None, text=True)
    try:
        stdout, stderr = process.communicate(input_text)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
print('Ready. Fill in step 2 and run that cell to create music.')
'''.replace('__PAYLOAD__', repr(encoded)).replace('__DIGEST__', digest).replace('__NAMES__', repr(names))

generate = '''#@title 2. Make music — use this form on free Colab
style = "Product or app ad" #@param ["Product or app ad", "Camera gear / cinematic", "Food / cooking reel", "Calm background", "Energetic electronic", "My own style"]
description = "A friendly product ad. Warm synths, light drums and a small lift halfway through." #@param {type:"string"}
music_role = "Under speech" #@param ["Under speech", "Music leads the edit"]
energy = "Steady" #@param ["Gentle", "Steady", "Punchy"]
maximum_seconds = 10 #@param {type:"slider", min:5, max:90, step:1}
ending = "Finish naturally" #@param ["Finish naturally", "Repeatable groove", "Let the model choose"]
instruments = "" #@param {type:"string"}
no_singing = True #@param {type:"boolean"}
lyrics = "" #@param {type:"string"}
tempo_bpm = 0 #@param {type:"integer"}
seed = 12345 #@param {type:"integer"}
new_seed_each_time = True #@param {type:"boolean"}
# 0 tempo lets the model choose. Gentle = relaxed; Punchy = strong rhythm.
# If you enable singing, put the words in lyrics; use \\n for line breaks.
request = dict(style=style, brief=description, role=music_role, energy=energy,
               seconds=maximum_seconds, ending=ending, instruments=instruments,
               instrumental=no_singing, lyrics=lyrics.replace('\\\\n', '\\n'),
               bpm=tempo_bpm, seed=seed, randomize=new_seed_each_time)
python = Path(os.environ['MUSIC_DATA_DIR']) / 'venv/bin/python'
print('Creating music on the GPU. This can take several minutes. Backend logs: /content/minimax-runtime/logs/backend.log')
completed = run_owned([str(python), str(ROOT / 'run_job.py')], input_text=json.dumps(request), capture=True)
if completed.returncode:
    raise RuntimeError(completed.stderr[-2500:] or 'Generation stopped. Read the backend log and try a shorter request.')
result = json.loads(completed.stdout)
from IPython.display import Audio, display
display(Audio(filename=result['premiere']))
print(f"Saved {result['qa']['duration_seconds']:.2f} seconds. Seed: {result['seed']}. Listen before use.")
print('Use step 3 to download. The runtime files disappear when Colab deletes the session.')
'''

download = '''#@title 3. Download the music you want to keep
download_format = "Premiere WAV" #@param ["Premiere WAV", "Original FLAC", "Settings JSON", "Everything for this result (ZIP)"]
if 'result' not in globals():
    raise RuntimeError('Create music in step 2 first.')
if download_format == 'Everything for this result (ZIP)':
    download_path = Path(result['job']).with_suffix('.zip')
    with zipfile.ZipFile(download_path, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for key in ('premiere', 'original', 'job'):
            item = Path(result[key])
            bundle.write(item, arcname=item.name)
else:
    key = {'Premiere WAV':'premiere', 'Original FLAC':'original', 'Settings JSON':'job'}[download_format]
    download_path = Path(result[key])
print('On your PC, choose a D: folder in the browser save dialog.')
from google.colab import files
files.download(str(download_path))
'''

web = '''#@title 4. Optional: start the web UI on your domain — paid Colab / own GPU host
paid_colab_with_compute_units = False #@param {type:"boolean"}
if not paid_colab_with_compute_units:
    print('Use step 2 on free Colab. Enable this only with paid Colab and a positive compute-unit balance.')
else:
    from getpass import getpass
    # Hidden inputs are kept out of source, saved form fields and cell output.
    web_env = os.environ.copy()
    try:
        web_env['MUSIC_PUBLIC_HOST'] = input('Your Cloudflare hostname (example: colab.example.com): ').strip()
        web_env['MUSIC_UI_USER'] = input('Studio login name [music]: ').strip() or 'music'
        web_env['MUSIC_UI_PASSWORD'] = getpass('Create a studio password (at least 12 characters, hidden): ')
        web_env['CLOUDFLARE_TUNNEL_TOKEN'] = getpass('Cloudflare tunnel token (hidden): ').strip()
        web_env['MUSIC_EXTERNAL_UI_ALLOWED'] = '1'
        print('Starting the protected web UI. Stop this cell when finished.')
        web_result = run_owned([str(python), str(ROOT / 'launch_web.py')], env=web_env)
        if web_result.returncode:
            raise RuntimeError('The web launcher stopped. Check the runtime logs for details.')
    finally:
        web_env.clear()
'''

notebook = {'nbformat': 4, 'nbformat_minor': 5,
    'metadata': {'colab': {'name': 'MiniMax Music Studio.ipynb', 'provenance': [],
                           'private_outputs': True, 'toc_visible': True},
                 'accelerator': 'GPU', 'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}},
    'cells': [markdown('''# Your music studio · MiniMax Music 3
Create background music for short videos. No music theory needed.

**First:** choose **Runtime → Change runtime type → GPU**, then run step 1. Setup downloads about **11.1 GiB** of model weights. No paid model API or GitHub token is used.

**Free Colab:** fill in step 2 and generate inside this notebook. **Paid Colab with positive compute units:** step 4 can expose the full web UI at your Cloudflare domain. It asks for connection details at runtime using hidden password/token input. [Google explains the restrictions here](https://research.google.com/colaboratory/faq.html).

**Everyday words work:** “Warm piano and soft drums for a calm voice-over” or “Playful guitar and bouncy bass for a cooking reel.” Start with ten seconds, listen, then adjust.

The length is a maximum; music may end earlier. “No singing” is a creative instruction, so listen for voice-like sounds. Save the results you want before disconnecting. Check the [MiniMax model agreement](https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE), including its AI-output disclosure conditions, before publishing.
'''), code(setup, True), markdown('''## Choose the music
**Under speech** asks for a restrained lead. **Music leads the edit** asks for a clearer musical hook. **Gentle / Steady / Punchy** controls the requested energy. **Tempo 0** lets the model choose; 120 BPM is a steady dance pulse. Leave instruments blank if you are unsure.

Repeating the same seed and settings may help repeat a result, but different hardware or software can change it. Do not run steps 2 and 4 at the same time: only one backend can own the GPU.
'''), code(generate, True), code(download, True), markdown('''## Full web interface — optional, for later
The GUI adds multiple choices, advanced controls, a loop tool and a saved-results browser. Your Cloudflare tunnel route should point **your hostname → http://localhost:8188**; the private GPU backend uses port 8189.

Step 4 asks for your hostname, a login name, a studio password (at least 12 characters) and a tunnel token. Password/token entry is hidden. Values are not saved in notebook source, a form field, a file or GitHub. Keep your Cloudflare Access sign-in enabled. Rotate any tunnel token that was pasted into chat, and enter only its replacement at the hidden prompt.

The domain works while this cell and runtime are running. This is not permanent hosting. No public Gradio share link, anti-idle loop or limit-bypass code is used.
'''), code(web, True)]}
for index, cell in enumerate(notebook['cells']):
    cell['id'] = 'studio-' + str(index)
(ROOT / 'MiniMax_Music_Studio.ipynb').write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('Notebook built:', len(payload), 'embedded bytes; SHA-256', digest)
