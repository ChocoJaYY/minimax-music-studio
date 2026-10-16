import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('MUSIC_DATA_DIR', ROOT / '.runtime')).resolve()
OUTPUTS = Path(os.environ.get('MUSIC_OUTPUT_DIR', ROOT / 'outputs')).resolve()
COMFY = Path(os.environ.get('MUSIC_COMFY_DIR', DATA / 'ComfyUI')).resolve()
MODELS = Path(os.environ.get('MUSIC_MODEL_DIR', DATA / 'models')).resolve()
PYTHON = os.environ.get('MUSIC_BACKEND_PYTHON', str(DATA / 'venv/bin/python'))


def configure():
    for directory in (DATA, OUTPUTS, DATA / 'logs', DATA / 'temp', DATA / 'user'):
        directory.mkdir(parents=True, exist_ok=True)
    for key, value in {'HF_HOME': DATA / 'cache/huggingface', 'TORCH_HOME': DATA / 'cache/torch',
                       'XDG_CACHE_HOME': DATA / 'cache', 'GRADIO_TEMP_DIR': DATA / 'temp/gradio',
                       'CUDA_CACHE_PATH': DATA / 'cache/cuda', 'PYTHONPYCACHEPREFIX': DATA / 'cache/pycache',
                       'TMPDIR': DATA / 'temp', 'TEMP': DATA / 'temp', 'TMP': DATA / 'temp'}.items():
        os.environ.setdefault(key, str(value))
    os.environ.update(GRADIO_ANALYTICS_ENABLED='False', HF_HUB_DISABLE_TELEMETRY='1',
                      DO_NOT_TRACK='1', HF_HUB_DISABLE_XET='1', PYTHONUNBUFFERED='1')
