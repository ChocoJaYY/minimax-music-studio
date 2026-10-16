"""Prepare a Linux/Colab runtime without replacing its working CUDA PyTorch."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from studio.paths import DATA, COMFY, MODELS, OUTPUTS, configure


def run(*args, **kwargs):
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    configure()
    if sys.platform != 'linux':
        raise RuntimeError('This installer is for a Linux GPU runtime, including Colab.')
    # Fail before downloads if no GPU or incompatible runtime is selected.
    run(sys.executable, '-c', "import torch; from packaging.version import Version; assert torch.cuda.is_available(), 'Choose a GPU runtime in Colab'; assert Version(torch.__version__.split('+')[0]) >= Version('2.8'), 'Use a Colab runtime with PyTorch 2.8 or newer'; x=torch.randn(16,16,device='cuda'); y=x@x; torch.cuda.synchronize(); assert bool(torch.isfinite(y).all()); print('GPU:',torch.cuda.get_device_name(), 'PyTorch:',torch.__version__)")
    if shutil.disk_usage(DATA).free < 18 * 1024**3 and not (DATA / 'models-verified.json').exists():
        raise RuntimeError('Please free at least 18 GiB on the runtime disk before setup.')
    lock = json.loads((ROOT / 'runtime-lock.json').read_text())
    if not (COMFY / '.git').exists():
        COMFY.mkdir(parents=True, exist_ok=True)
        run('git', 'init', str(COMFY))
        run('git', '-C', str(COMFY), 'remote', 'add', 'origin', lock['comfy_repository'])
        run('git', '-C', str(COMFY), 'fetch', '--depth', '1', 'origin', lock['comfy_revision'])
        run('git', '-C', str(COMFY), 'checkout', '--detach', 'FETCH_HEAD')
    revision = subprocess.check_output(['git', '-C', str(COMFY), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != lock['comfy_revision']:
        raise RuntimeError('The backend revision differs from runtime-lock.json. Use a fresh runtime directory.')
    environment = DATA / 'venv'
    if not (environment / 'bin/python').exists():
        # Reuse the managed runtime's CUDA stack; keep all added packages in a venv.
        venv.EnvBuilder(system_site_packages=True, with_pip=False).create(environment)
    python = environment / 'bin/python'
    run(python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', ROOT / 'requirements.txt',
        '-r', ROOT / 'requirements-backend.txt', '-c', ROOT / 'requirements.txt')
    if not shutil.which('ffmpeg'):
        run('apt-get', 'update', '-qq')
        run('apt-get', 'install', '-y', '-qq', 'ffmpeg')
    print('Downloading pinned MiniMax weights and checking SHA-256. About 11.1 GiB.', flush=True)
    run(python, ROOT / 'download_models.py')
    run(python, '-m', 'studio.worker', '--quick-test-for-ci', '--offline', '--disable-all-custom-nodes',
        '--disable-auto-launch', '--models-directory', MODELS, '--output-directory', OUTPUTS / 'worker',
        '--user-directory', DATA / 'user', '--temp-directory', DATA / 'temp/comfy', '--fast-disk', '--cache-none', cwd=ROOT)
    snapshot = subprocess.check_output([str(python), '-m', 'pip', 'freeze'], text=True)
    (DATA / 'environment.txt').write_text(snapshot, encoding='utf-8')
    print('Setup finished. Run the notebook music form next.', flush=True)


if __name__ == '__main__':
    main()
