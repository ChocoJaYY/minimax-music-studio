"""Deterministic guided briefs: no external writing service or extra model."""
import math

PRESETS = {
    'Product or app ad': 'Modern electronic instrumental, warm synth chords, rounded bass, clean crisp drums.',
    'Camera gear / cinematic': 'Cinematic electronic instrumental, spacious synths, deep restrained bass pulse, detailed percussion.',
    'Food / cooking reel': 'Playful upbeat instrumental, plucked guitar, light piano, bouncy bass and small dry percussion.',
    'Calm background': 'Gentle instrumental with warm electric piano, soft pads and light percussion.',
    'Energetic electronic': 'Driving electronic instrumental, tight drums, rhythmic synths and controlled bass.',
    'My own style': '',
}
ENERGY = {'Gentle': 'Low energy, soft attacks and plenty of space.',
          'Steady': 'Steady medium energy with a clear pulse.',
          'Punchy': 'High energy with strong rhythmic accents and edit points.'}
ENDINGS = {'Finish naturally': 'Resolve the final phrase and leave a short natural decay.',
           'Repeatable groove': 'Use a repeating groove and even phrasing without a final crash; intended for later loop editing.',
           'Let the model choose': ''}


def make_request(style='Product or app ad', brief='', role='Under speech', energy='Steady',
                 seconds=30, ending='Finish naturally', instrumental=True, lyrics='',
                 bpm=0, key='', instruments='', seed=12345, randomize=True,
                 steps=30, guidance=1.7, top_k=50, global_details='', arrangement=''):
    # Untouched/cleared Gradio textboxes may arrive as None, including hidden lyrics.
    texts = [brief, lyrics, key, instruments, global_details, arrangement]
    if any(text is not None and not isinstance(text, str) for text in texts):
        raise ValueError('Please use plain text for the brief, lyrics and optional music details.')
    brief, lyrics, key, instruments, global_details, arrangement = [
        '' if text is None else text for text in texts
    ]
    numbers = [seconds, bpm, seed, steps, guidance, top_k]
    if not all(math.isfinite(float(x)) for x in numbers):
        raise ValueError('Please use ordinary numbers in the controls.')
    if not 5 <= float(seconds) <= 300:
        raise ValueError('Choose a maximum length from 5 to 300 seconds.')
    if not 0 <= int(bpm) <= 300 or not 0 <= int(seed) <= 2147483647:
        raise ValueError('Tempo must be 0–300 and the seed 0–2147483647.')
    if not 4 <= int(steps) <= 60 or not 1 <= float(guidance) <= 4 or not 1 <= int(top_k) <= 16384:
        raise ValueError('Use 4–60 steps, guidance 1–4 and variety 1–16384.')
    if style not in PRESETS or energy not in ENERGY or ending not in ENDINGS:
        raise ValueError('Choose one of the styles, energy levels and endings shown.')
    if role not in ('Under speech', 'Music leads the edit'):
        raise ValueError('Choose how the music will be used.')
    if not instrumental and not lyrics.strip():
        raise ValueError('Add the words you want sung, or turn on “No singing”.')
    if not (PRESETS[style] or brief.strip() or global_details.strip()):
        raise ValueError('Describe your own style first. For example: warm piano and soft drums.')
    texts = [brief, lyrics, key, instruments, global_details, arrangement]
    if any(len(text) > 10000 for text in texts) or sum(map(len, texts)) > 15000:
        raise ValueError('Please shorten the brief or lyrics before generating.')
    global_text = global_details.strip() or ' '.join(filter(None, [PRESETS[style], brief.strip(), ENERGY[energy]]))
    if bpm:
        global_text += f' Tempo: {int(bpm)} BPM.'
    if key.strip():
        global_text += f' Key and scale: {key.strip()}.'
    vocal = ('Instrumental, no singing, speech, humming, choir or vocal textures.' if instrumental
             else 'Lead vocals following the supplied lyrics. Keep the words clear.')
    arrangement_text = arrangement.strip() or ('Keep the lead restrained and leave room for spoken dialogue.'
                                               if role == 'Under speech' else 'Use a clear musical hook and changes that can carry picture edits.')
    if instruments.strip():
        arrangement_text += ' Instruments: ' + instruments.strip() + '.'
    arrangement_text += ' ' + ENDINGS[ending]
    caption = f'Global Metadata: {global_text}\nVocal Details: {vocal}\nArrangement: {arrangement_text.strip()}'
    return {'caption': caption, 'lyrics': '[instrumental]' if instrumental else lyrics.strip(),
            'seconds': float(seconds), 'seed': int(seed), 'randomize': bool(randomize),
            'steps': int(steps), 'guidance': float(guidance), 'top_k': int(top_k),
            'instrumental': bool(instrumental)}
