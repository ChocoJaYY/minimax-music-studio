"""Resample in float before applying gain protection to the editing copy."""
import math
import subprocess
import uuid
import numpy as np
import soundfile as sf
from studio.paths import DATA, configure


def premiere_copy(source, destination):
    configure()
    intermediate = DATA / 'temp' / ('export-' + uuid.uuid4().hex + '.wav')
    try:
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-i',
                        str(source), '-ar', '48000', '-ac', '2', '-c:a', 'pcm_f32le', str(intermediate)], check=True)
        audio, rate = sf.read(intermediate, dtype='float32', always_2d=True)
        if audio.size == 0 or not np.isfinite(audio).all():
            raise ValueError('The generated audio is empty or invalid.')
        peak = float(np.max(np.abs(audio)))
        if peak < 1e-7:
            raise ValueError('The generated audio is silent.')
        gain = min(1.0, 0.98 / peak)
        with open(destination, 'xb') as stream:
            sf.write(stream, audio * gain, rate, format='WAV', subtype='PCM_24')
        return round(20 * math.log10(gain), 5)
    finally:
        intermediate.unlink(missing_ok=True)
