"""CPU-only check of real Gradio defaults and result delivery; no model inference."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf
from gradio_client import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.paths import DATA, configure
from studio.ui import create_ui
import studio.ui as studio_ui


def main():
    configure()
    with tempfile.TemporaryDirectory(prefix='form-check-', dir=DATA / 'temp') as folder:
        output = Path(folder)

        class FakeEngine:
            state = 'Form regression check; GPU inference disabled.'
            calls = []

            def release(self):
                return self.state

            def generate(self, request, progress):
                self.calls.append(request)
                audio = output / 'fixture.wav'
                sf.write(audio, np.column_stack([np.sin(np.arange(4800) * 0.03) * 0.1] * 2), 48000, subtype='PCM_24')
                job = output / 'fixture.json'
                job.write_text(json.dumps({'request': request}))
                return {'premiere': str(audio), 'original': str(audio), 'job': str(job),
                        'seed': request['seed'], 'qa': {'duration_seconds': 0.1}}

        engine = FakeEngine()
        with patch.object(studio_ui, 'OUTPUTS', output):
            ui = create_ui(engine)
            try:
                ui.queue().launch(server_name='127.0.0.1', server_port=8192, share=False,
                                  prevent_thread_lock=True, allowed_paths=[str(output)])
                client = Client('http://127.0.0.1:8192', verbose=False)
                for texts in ('defaults', 'null', 'cleared'):
                    arguments = {} if texts == 'defaults' else dict.fromkeys(
                        ('brief', 'lyrics', 'key', 'instruments', 'global_details', 'arrangement'),
                        None if texts == 'null' else '')
                    # Endpoint parameters follow component labels rather than Python field names.
                    if arguments:
                        values = ['Product or app ad', arguments['brief'], 'Under speech', 'Steady', 5,
                                  'Finish naturally', True, arguments['lyrics'], 0, arguments['key'],
                                  arguments['instruments'], 12345, False, 30, 1.7, 50,
                                  arguments['global_details'], arguments['arrangement'], 1]
                        result = client.predict(*values, api_name='/generate_music')
                    else:
                        result = client.predict(api_name='/generate_music')
                    assert engine.calls[-1]['lyrics'] == '[instrumental]'
                    assert engine.calls[-1]['caption']
                    assert Path(result[2]).is_file() and Path(result[4]).is_file()
                    print(f'{texts}: request reached the engine and audio/settings were delivered')
                assert len(engine.calls) == 3
            finally:
                ui.close()
    print('PASS: real Gradio form defaults, null fields and cleared fields. No GPU inference performed.')


if __name__ == '__main__':
    main()
