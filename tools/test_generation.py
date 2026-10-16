"""Deliberate real CUDA generation through the protected web UI action."""
import json
import time
from pathlib import Path
from gradio_client import Client

root = Path(__file__).resolve().parents[1]
password = json.loads((root/'.runtime/test-auth.json').read_text())['password']
client = Client('http://127.0.0.1:8188', auth=('music',password), verbose=False)
started = time.monotonic()
result = client.predict('Product or app ad', 'Warm synth chords and soft crisp drums. No vocal textures.',
    'Under speech', 'Steady', 5, 'Finish naturally', True, '', 120, '', '', 67891, False,
    30, 1.7, 50, '', '', 1, api_name='/generate_music')
job = json.loads(Path(result[4]).read_text(encoding='utf-8'))
assert job['status'] == 'succeeded' and job['qa']['finite'] and job['qa']['non_silent']
assert job['qa']['sample_rate'] == 48000 and job['qa']['channels'] == 2 and job['qa']['subtype'] == 'PCM_24'
record = {'status':'succeeded', 'environment':'Windows RTX 4050 6 GB; existing isolated CUDA 13 backend',
          'route':'new repo protected Gradio action via Gradio Client', 'total_seconds':round(time.monotonic()-started,2),
          'job':Path(result[4]).name, 'qa':job['qa'], 'listening_review':'required',
          'colab_validation':'not performed by this test'}
(root/'validation/local-generation.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
