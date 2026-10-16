"""CUDA-only native backend. Memory offload is allowed; CPU inference is not."""
import os
import runpy
import sys
from studio.paths import COMFY, DATA, configure

configure()
lock_path = os.environ.get('STUDIO_GPU_LOCK', str(DATA / 'gpu.lock'))
lease = open(lock_path, 'a+b')
lease.seek(0, 2)
if lease.tell() == 0:
    lease.write(b'0')
    lease.flush()
lease.seek(0)
try:
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    raise RuntimeError('Another studio owns the GPU. Release that model first.')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')
sys.path.insert(0, str(COMFY))
os.chdir(COMFY)
namespace = runpy.run_path(str(COMFY / 'main.py'), run_name='minimax_studio_backend')
import torch
import comfy.model_management as memory
if not torch.cuda.is_available():
    raise RuntimeError('A CUDA GPU is required. Choose a GPU runtime in Colab.')
memory.text_encoder_device = memory.get_torch_device
loop, server, start = namespace['start_comfyui']()
try:
    loop.run_until_complete(start())
finally:
    server.asset_manager.shutdown()
