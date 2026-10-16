import json
import subprocess
import uuid
import numpy as np
import soundfile as sf
from studio.paths import OUTPUTS
from studio.engine import inspect


def loop_candidate(source, bpm, bars, start):
    if not source or not 20 <= float(bpm) <= 300 or not 1 <= int(bars) <= 32 or float(start) < 0:
        raise ValueError('Choose a track, a tempo from 20 to 300, and 1–32 bars.')
    output = OUTPUTS / ('loop-' + uuid.uuid4().hex[:12] + '.wav')
    converted = OUTPUTS / ('loop-source-' + uuid.uuid4().hex[:12] + '.wav')
    try:
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-i',
                        str(source), '-ar', '48000', '-ac', '2', '-c:a', 'pcm_f32le', str(converted)], check=True)
        audio, rate = sf.read(converted, dtype='float32', always_2d=True)
        count = round(int(bars) * 4 * 60 / float(bpm) * rate)
        offset, fade = round(float(start) * rate), round(0.08 * rate)
        if offset + count + fade > len(audio):
            raise ValueError('Not enough audio after that start point. Use fewer bars or start earlier.')
        phrase = audio[offset:offset+count+fade]
        result = phrase[:count].copy()
        weight = np.linspace(0, 1, fade, dtype='float32')[:, None]
        result[:fade] = phrase[count:count+fade] * (1-weight) + phrase[:fade] * weight
        sf.write(output, result, rate, subtype='PCM_24')
        qa = inspect(output)
        output.with_suffix('.json').write_text(json.dumps({'kind': 'loop candidate', 'source': str(source),
            'bpm_supplied': bpm, 'bars_4_4': bars, 'start_seconds': start, 'qa': qa}, indent=2), encoding='utf-8')
        return str(output)
    finally:
        converted.unlink(missing_ok=True)
