"""Paid Colab / own-host web launcher. Secrets are environment-only."""
import hashlib
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from studio.paths import ROOT, DATA, PYTHON, configure


def main():
    configure()
    if os.environ.get('MUSIC_EXTERNAL_UI_ALLOWED') != '1':
        raise RuntimeError('Use the notebook form on free Colab. External UI is for paid Colab with positive compute units, or your own GPU host.')
    token = os.environ.get('CLOUDFLARE_TUNNEL_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Add CLOUDFLARE_TUNNEL_TOKEN to Colab Secrets and allow this notebook to read it.')
    if len(os.environ.get('MUSIC_UI_PASSWORD', '')) < 12:
        raise RuntimeError('Add MUSIC_UI_PASSWORD to Colab Secrets: at least 12 characters.')
    lock = json.loads((ROOT / 'runtime-lock.json').read_text())['cloudflared']
    binary = DATA / 'cloudflared'
    if not binary.exists() or hashlib.sha256(binary.read_bytes()).hexdigest() != lock['sha256']:
        with urllib.request.urlopen(lock['url'], timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != lock['sha256']:
            raise RuntimeError('The Cloudflare download did not pass its SHA-256 check.')
        binary.write_bytes(data)
        binary.chmod(0o700)
    # The token never enters command arguments, notebook source or app/worker env.
    ui_env = os.environ.copy()
    ui_env.pop('CLOUDFLARE_TUNNEL_TOKEN', None)
    tunnel_env = os.environ.copy()
    tunnel_env.pop('MUSIC_UI_PASSWORD', None)
    tunnel_env['TUNNEL_TOKEN'] = tunnel_env.pop('CLOUDFLARE_TUNNEL_TOKEN')
    ui = tunnel = None
    with (DATA / 'logs/web.log').open('a') as app_log, (DATA / 'logs/tunnel.log').open('a') as tunnel_log:
        try:
            ui = subprocess.Popen([PYTHON, str(ROOT / 'app.py')], cwd=ROOT, env=ui_env,
                                  stdout=app_log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if ui.poll() is not None:
                    raise RuntimeError('The web UI could not start. Check .runtime/logs/web.log.')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8188/', timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(1)
            else:
                raise TimeoutError('The web UI did not become ready.')
            tunnel = subprocess.Popen([str(binary), 'tunnel', '--no-autoupdate', '--loglevel', 'warn', 'run'],
                                      env=tunnel_env, stdout=tunnel_log, stderr=subprocess.STDOUT, start_new_session=True)
            print('Local web UI ready; Cloudflare is connecting. Open https://colab.chocojayy.me and sign in as chocojayy.', flush=True)
            print('This is a temporary runtime, not permanent hosting. Stop this cell to stop the app and tunnel.', flush=True)
            while ui.poll() is None and tunnel.poll() is None:
                time.sleep(2)
            raise RuntimeError('The web UI or tunnel stopped. Check the runtime logs.')
        finally:
            for process in (tunnel, ui):
                if process and process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=10)


if __name__ == '__main__':
    main()
