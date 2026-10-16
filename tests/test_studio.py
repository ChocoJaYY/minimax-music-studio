import ast
import base64
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import soundfile as sf
from studio.prompts import make_request
from studio.graph import build
import studio.audio_tools as audio_tools
from studio.export import premiere_copy


class InputChecks(unittest.TestCase):
    def test_instrumental_ignores_lyric_words_and_uses_tag(self):
        request = make_request(instrumental=True, lyrics='These words must not be sung')
        self.assertEqual(request['lyrics'], '[instrumental]')
        self.assertNotIn('These words', request['caption'])
        self.assertIn('no singing', request['caption'])

    def test_invalid_requests_fail_before_gpu_work(self):
        for values in ({'seconds': 0}, {'seconds': float('nan')}, {'guidance': 9},
                       {'seed': -1}, {'instrumental': False, 'lyrics': ''}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                make_request(**values)

    def test_creative_controls_reach_native_graph(self):
        request = make_request(bpm=128, key='D minor', instruments='soft piano', steps=24,
                               guidance=1.9, top_k=40, seconds=12, seed=9, randomize=False)
        graph = build(request)
        self.assertIn('128 BPM', graph['4']['inputs']['caption'])
        self.assertIn('D minor', graph['4']['inputs']['caption'])
        self.assertEqual(graph['7']['inputs']['steps'], 24)
        self.assertEqual(graph['4']['inputs']['top_k'], 40)
        self.assertEqual(graph['4']['inputs']['max_duration'], 12)


class LoopChecks(unittest.TestCase):
    def test_editing_export_protects_peaks_and_keeps_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'source.wav', Path(folder)/'edit.wav'
            data = np.tile(np.array([1.4, -1.4, 0.2, -0.2], dtype='float32'), 8000)
            sf.write(source, np.column_stack((data,data)), 32000, subtype='FLOAT')
            original = source.read_bytes()
            gain = premiere_copy(source, output)
            audio, rate = sf.read(output, always_2d=True)
            self.assertLess(gain, 0)
            self.assertLessEqual(np.max(np.abs(audio)), 0.980001)
            self.assertEqual(rate, 48000)
            self.assertEqual(source.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                premiere_copy(source, output)

    def test_loop_preserves_length_format_and_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.wav'
            rate = 48000
            wave = (0.2*np.sin(2*np.pi*240*np.arange(rate*10)/rate)).astype('float32')
            sf.write(source, np.column_stack((wave, wave)), rate, subtype='FLOAT')
            original = hashlib.sha256(source.read_bytes()).hexdigest()
            with patch.object(audio_tools, 'OUTPUTS', root):
                result = Path(audio_tools.loop_candidate(str(source), 120, 4, 0))
                with self.assertRaises(ValueError):
                    audio_tools.loop_candidate(str(source), 120, 32, 0)
            info = sf.info(result)
            self.assertEqual(info.frames, rate*8)
            self.assertEqual((info.samplerate, info.channels, info.subtype), (48000, 2, 'PCM_24'))
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original)


class NotebookChecks(unittest.TestCase):
    def test_notebook_has_no_saved_outputs_or_credentials_and_matches_sources(self):
        root = Path(__file__).resolve().parents[1]
        notebook = json.loads((root/'MiniMax_Music_Studio.ipynb').read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                self.assertFalse(cell['outputs'])
                ast.parse(''.join(cell['source']))
        setup = ''.join(notebook['cells'][1]['source'])
        assignment = next(node for node in ast.parse(setup).body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id=='PAYLOAD' for target in node.targets))
        payload = base64.b64decode(ast.literal_eval(assignment.value))
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            for name in bundle.namelist():
                self.assertNotIn('..', Path(name).parts)
                self.assertEqual(bundle.read(name), (root/name).read_text(encoding='utf-8-sig').encode('utf-8'), 'Rebuild the notebook after source edits.')
                self.assertNotIn(b'eyJhIjoi', bundle.read(name), 'A tunnel credential may have been embedded.')


if __name__ == '__main__':
    unittest.main()
