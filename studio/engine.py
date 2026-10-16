import atexit
import json
import os
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
import numpy as np
import soundfile as sf
from studio.paths import ROOT, DATA, MODELS, OUTPUTS, PYTHON, configure
from studio.graph import build
from studio.export import premiere_copy


def api(path, payload=None, timeout=20):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request('http://127.0.0.1:8189' + path, data=body,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'GPU worker rejected this request ({error.code}): ' + error.read().decode()[:1200]) from error


def inspect(path):
    data, rate = sf.read(path, always_2d=True, dtype='float32')
    if data.size == 0 or not np.isfinite(data).all() or np.max(np.abs(data)) < 1e-7:
        raise RuntimeError('Generated audio was empty, silent or invalid. Try another seed.')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', str(path),
                    '-f', 'null', '-'], check=True, capture_output=True)
    return {'duration_seconds': len(data) / rate, 'sample_rate': rate, 'channels': data.shape[1],
            'subtype': sf.info(path).subtype, 'finite': True, 'non_silent': True, 'decode_passed': True,
            'full_scale_samples': int(np.sum(np.abs(data) >= 1)), 'peak': float(np.max(np.abs(data))),
            'listening_review': 'required'}


class Engine:
    def __init__(self):
        configure()
        self.process = None
        self.log = None
        self.lock = threading.Lock()
        self.state = 'Ready. The music model loads when you generate.'
        atexit.register(self.close)

    def close(self):
        if self.process is not None and self.process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'], capture_output=True)
            else:
                self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self.process = None
        if self.log:
            self.log.close()
            self.log = None

    def release(self):
        if not self.lock.acquire(blocking=False):
            return 'Music is still generating. Wait for it to finish, then release GPU memory.'
        try:
            self.close()
            self.state = 'GPU memory released. Generate again to reload the model.'
            return self.state
        finally:
            self.lock.release()

    def start(self):
        if self.process is not None and self.process.poll() is None:
            return
        # Do not accidentally submit work to an unrelated server on this port.
        try:
            api('/system_stats', timeout=1)
        except (OSError, RuntimeError):
            pass
        else:
            raise RuntimeError('Port 8189 is already in use. Stop the other backend first.')
        if not (DATA / 'models-verified.json').exists():
            raise RuntimeError('Run notebook step 1 to download and verify the model first.')
        self.state = 'Loading MiniMax Music 3 on the GPU. The first run takes longer.'
        self.log = (DATA / 'logs/backend.log').open('a', encoding='utf-8')
        command = [PYTHON, '-m', 'studio.worker', '--listen', '127.0.0.1', '--port', '8189',
                   '--offline', '--disable-all-custom-nodes', '--disable-auto-launch', '--reserve-vram', '0.6',
                   '--models-directory', str(MODELS), '--output-directory', str(OUTPUTS / 'worker'),
                   '--temp-directory', str(DATA / 'temp/comfy'), '--user-directory', str(DATA / 'user')]
        if os.name != 'nt':
            # Colab's small system-RAM profile needs reclaimable disk-backed weights.
            command += ['--fast-disk', '--cache-none']
        worker_env = {key:value for key,value in os.environ.items()
                      if key not in ('MUSIC_UI_PASSWORD', 'CLOUDFLARE_TUNNEL_TOKEN', 'TUNNEL_TOKEN')}
        self.process = subprocess.Popen(command, cwd=ROOT, env=worker_env, stdout=self.log, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError('The GPU worker could not start. Check .runtime/logs/backend.log.')
            try:
                api('/system_stats', timeout=2)
                return
            except (OSError, RuntimeError):
                time.sleep(1)
        raise TimeoutError('GPU startup took too long. Check the backend log.')

    def generate(self, request, progress=None):
        with self.lock:
            try:
                self.start()
                self.state = 'Creating music on the GPU. Long tracks can take several minutes.'
                request = dict(request)
                if request.pop('randomize', True):
                    request['seed'] = secrets.randbelow(2147483647)
                return self._generate(request, progress)
            except Exception:
                self.close()
                self.state = 'Generation stopped. Read the error, then try again with a fresh worker.'
                raise

    def _generate(self, request, progress):
        name = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8] + '-seed' + str(request['seed'])
        job = OUTPUTS / (name + '.json')
        record = {'status': 'running', 'model': 'MiniMax Music 3 / official Comfy INT8',
                  'request': request, 'duration_is_maximum': True, 'device_requested': 'cuda'}
        started = time.monotonic()
        job.write_text(json.dumps(record, indent=2), encoding='utf-8')
        try:
            prompt_id = api('/prompt', {'prompt': build(request), 'client_id': name}, timeout=60)['prompt_id']
            record['prompt_id'] = prompt_id
            while time.monotonic() - started < 3600:
                history = api('/history/' + prompt_id).get(prompt_id)
                if history:
                    if history.get('status', {}).get('status_str') == 'error':
                        raise RuntimeError(json.dumps(history['status'].get('messages', []))[-1800:])
                    audio = history.get('outputs', {}).get('9', {}).get('audio', [])
                    if audio:
                        source = (OUTPUTS / 'worker' / audio[0].get('subfolder', '') / audio[0]['filename']).resolve()
                        if not source.is_relative_to(OUTPUTS / 'worker'):
                            raise RuntimeError('The worker returned an unexpected file path.')
                        break
                if progress:
                    progress(None, desc=f'Creating music — {int(time.monotonic()-started)} seconds elapsed')
                time.sleep(2)
            else:
                raise TimeoutError('Generation exceeded one hour. Try a shorter track.')
            original = OUTPUTS / (name + '.flac')
            premiere = OUTPUTS / (name + '-premiere.wav')
            shutil.copyfile(source, original)
            export_gain = premiere_copy(original, premiere)
            qa = inspect(premiere)
            if qa['channels'] != 2 or qa['sample_rate'] != 48000 or qa['subtype'] != 'PCM_24':
                raise RuntimeError('Unexpected Premiere export format.')
            record.update(status='succeeded', original=str(original), premiere=str(premiere), qa=qa,
                          editing_export_gain_db=export_gain)
            self.state = f"Music ready: {qa['duration_seconds']:.1f} seconds. Listen before using it."
            return {'original': str(original), 'premiere': str(premiere), 'job': str(job), 'qa': qa, 'seed': request['seed']}
        except Exception as error:
            record.update(status='failed', error=str(error))
            raise
        finally:
            record['seconds_elapsed'] = round(time.monotonic() - started, 2)
            job.write_text(json.dumps(record, indent=2), encoding='utf-8')
