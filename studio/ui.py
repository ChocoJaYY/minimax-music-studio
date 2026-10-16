import json
from pathlib import Path
import gradio as gr
from studio.prompts import PRESETS, ENERGY, ENDINGS, make_request
from studio.paths import OUTPUTS
from studio.audio_tools import loop_candidate


def create_ui(engine, preview=False):
    def generate(*values, progress=gr.Progress()):
        if preview:
            raise gr.Error('This is the layout preview. Start the GPU application to generate music.')
        *request_values, variations = values
        try:
            if not 1 <= int(variations) <= 4:
                raise ValueError('Choose one to four results to compare.')
            request = make_request(*request_values)
            results = []
            for number in range(int(variations)):
                take_request = dict(request)
                take_request['seed'] = (request['seed'] + number) % 2147483648
                progress(None, desc=f'Creating choice {number+1} of {int(variations)}')
                results.append(engine.generate(take_request, progress))
            return (gr.update(choices=[(f"Choice {i+1} · seed {r['seed']}", str(i)) for i, r in enumerate(results)], value='0'),
                    results, *select('0', results))
        except Exception as error:
            raise gr.Error(str(error)) from error

    def select(index, records):
        if not records:
            return None, None, None, None, 'No music selected yet.'
        item = records[int(index or 0)]
        for key in ('premiere', 'original', 'job'):
            if not Path(item[key]).resolve().is_relative_to(OUTPUTS):
                raise gr.Error('Choose a file saved by this studio.')
        return item['premiere'], item['premiere'], item['original'], item['job'], f"{item['qa']['duration_seconds']:.1f} seconds · seed {item['seed']}. Listen before using it in an edit."

    def library():
        records = []
        for path in sorted(OUTPUTS.glob('*.json'), key=lambda p:p.stat().st_mtime, reverse=True):
            try:
                item = json.loads(path.read_text(encoding='utf-8'))
                if item.get('status') == 'succeeded' and Path(item['premiere']).is_file():
                    records.append({'premiere': item['premiere'], 'original': item['original'],
                                    'job': str(path), 'qa': item['qa'], 'seed': item['request']['seed']})
            except (ValueError, OSError, KeyError):
                continue
            if len(records) == 50:
                break
        return gr.update(choices=[(Path(r['premiere']).stem, str(i)) for i,r in enumerate(records)], value='0' if records else None), records

    def panel():
        chosen = gr.Dropdown(label='Choose a result', choices=[], interactive=True)
        records = gr.State([])
        audio = gr.Audio(label='Listen to your music', type='filepath', interactive=False)
        with gr.Row():
            wav = gr.File(label='For Premiere — WAV', interactive=False)
            original = gr.File(label='Original audio — FLAC', interactive=False)
            job = gr.File(label='Settings and checks — JSON', interactive=False)
        status = gr.Textbox(label='Result', interactive=False)
        chosen.change(select, [chosen, records], [audio, wav, original, job, status], api_visibility='private')
        return chosen, records, audio, wav, original, job, status

    with gr.Blocks(title='ChocoJaYY Music Studio · MiniMax Music 3') as ui:
        gr.Markdown('# Music for your next edit\nPowered by **MiniMax Music 3** · Choose a starting point, describe the feeling, then make a few choices to compare.')
        if preview:
            gr.Markdown('**Layout preview — generation is disabled here.**')
        with gr.Row():
            status = gr.Textbox(value=engine.state, label='Studio status', interactive=False, scale=5)
            release = gr.Button('Free GPU memory', scale=1)
        release.click(engine.release, outputs=status, api_visibility='private', queue=False)
        gr.Timer(3).tick(lambda: engine.state, outputs=status, api_visibility='private', queue=False, show_progress='hidden')
        with gr.Tabs():
            with gr.Tab('Make music'):
                with gr.Row():
                    style = gr.Dropdown(list(PRESETS), value='Product or app ad', label='What are you editing?', info='Choose a starting style. You can describe something different below.')
                    role = gr.Radio(['Under speech', 'Music leads the edit'], value='Under speech', label='What should the music do?', info='Under speech keeps the musical lead more restrained. You still adjust volume in Premiere.')
                brief = gr.Textbox(label='Describe the feeling you want', lines=3, placeholder='Example: A bright ad for a delivery app. Friendly synths, light drums, a small lift halfway through.', info='Use everyday words: warm, playful, tense, soft, futuristic. Mention sounds you want or want to avoid.')
                with gr.Row():
                    energy = gr.Radio(list(ENERGY), value='Steady', label='How much energy?', info='Gentle = relaxed. Steady = clear pulse. Punchy = strong rhythm for fast edits.')
                    seconds = gr.Slider(5, 90, value=30, step=1, label='Maximum length (seconds)', info='Start with 10–30 seconds. The music can finish earlier. Longer requests take more time and memory.')
                with gr.Row():
                    ending = gr.Dropdown(list(ENDINGS), value='Finish naturally', label='How should it end?', info='Repeatable groove makes a loop-friendly request. Use the Loop tool to trim and check the join.')
                    variations = gr.Slider(1, 4, value=1, step=1, label='How many choices?', info='Choices generate one after another to save GPU memory.')
                instrumental = gr.Checkbox(True, label='No singing — instrumental only', info='On by default for background music. Some results may still contain voice-like sounds; listen before use.')
                lyrics = gr.Textbox(label='Words to sing — only when singing is enabled', lines=4, placeholder='[verse]\nYour first line\n[chorus]\nYour chorus line', info='Put each section label on its own line. Leave musical instructions in the description, not in the lyrics.', visible=False)
                instrumental.change(lambda checked: gr.update(visible=not checked), instrumental, lyrics, api_visibility='private')
                with gr.Accordion('More control — optional', open=False):
                    instruments = gr.Textbox(label='Instruments or sounds', placeholder='Example: soft piano, warm synth, deep bass, light hand percussion', info='Leave blank to follow the starting style.')
                    with gr.Row():
                        bpm = gr.Number(value=0, minimum=0, maximum=300, precision=0, label='Exact tempo — optional', info='0 lets the model choose. BPM means beats per minute: about 80 is relaxed; 120 is a steady dance pulse.')
                        key = gr.Textbox(label='Musical key — optional', placeholder='Example: D minor', info='Leave blank if you do not know. Minor often feels darker; major often feels brighter. This is a request, not a guarantee.')
                    with gr.Row():
                        seed = gr.Number(value=12345, minimum=0, maximum=2147483647, precision=0, label='Variation number (seed)', info='Reuse a number with the same settings to try repeating a result. Hardware/software changes can still alter it.')
                        randomize = gr.Checkbox(True, label='Pick a new variation number each time')
                    with gr.Row():
                        steps = gr.Slider(4, 60, value=30, step=1, label='Audio detail steps', info='30 follows the official workflow. More steps take longer and do not always improve music.')
                        guidance = gr.Slider(1, 4, value=1.7, step=0.1, label='How strongly to follow the brief', info='1.7 is the starting value. Higher settings can sound less natural.')
                        top_k = gr.Slider(1, 100, value=50, step=1, label='Pattern variety', info='50 is the starting value. Lower values narrow the model’s choices; higher values allow more variety.')
                with gr.Accordion('Write a detailed music brief — optional', open=False):
                    global_details = gr.Textbox(label='Overall style and mood', lines=3, placeholder='Example: Electronic pop, 120 BPM, warm and confident. Start simple, build gently, finish cleanly.', info='When filled, this replaces the starting style and short description. Exact tempo/key above still apply.')
                    arrangement = gr.Textbox(label='How the sounds should change', lines=3, placeholder='Example: Begin with soft synth chords. Bring in drums after two seconds. Add a bright melody halfway through.', info='Describe the beginning, middle and ending in plain English. These are creative requests; results can vary.')
                gr.Markdown('Generated music needs a listening check. The model may finish early or interpret the brief loosely. Original audio and a 48 kHz / 24-bit Premiere WAV are saved separately.')
                button = gr.Button('Create music', variant='primary', interactive=not preview)
                results = panel()
                send = gr.Button('Use this result in the Loop tool')
                inputs = [style, brief, role, energy, seconds, ending, instrumental, lyrics, bpm, key,
                          instruments, seed, randomize, steps, guidance, top_k, global_details, arrangement, variations]
                button.click(generate, inputs, list(results), api_name='generate_music', concurrency_id='gpu', concurrency_limit=1)
            with gr.Tab('Loop tool'):
                gr.Markdown('A loop repeats a short phrase. This tool assumes **four beats per bar**. The supplied tempo must match the actual music. Listen to the repeated join before calling it finished.')
                source = gr.Audio(label='Music to loop — send a result here or upload audio', sources=['upload'], type='filepath')
                with gr.Row():
                    loop_bpm = gr.Number(value=120, minimum=20, maximum=300, label='Actual tempo (BPM)', info='Use the measured tempo. At 120 BPM, four bars last eight seconds.')
                    bars = gr.Slider(1, 32, value=4, step=1, label='How many bars?', info='A bar is a group of four beats in this tool.')
                    start = gr.Number(value=0, minimum=0, label='Start at (seconds)', info='Choose the start of a strong beat. The source needs a little extra audio after the phrase.')
                loop_button = gr.Button('Make a loop candidate')
                loop_audio = gr.Audio(label='Listen to the join', interactive=False)
                loop_file = gr.File(label='Loop WAV', interactive=False)
                def make_loop(*args):
                    try:
                        path = loop_candidate(*args)
                        return path, path
                    except Exception as error:
                        raise gr.Error(str(error)) from error
                loop_button.click(make_loop, [source, loop_bpm, bars, start], [loop_audio, loop_file], api_name='prepare_loop')
            with gr.Tab('Saved music'):
                gr.Markdown('These files belong to this runtime. **Download the tracks you want before disconnecting Colab.** If saving to this PC, choose a folder on D:.')
                refresh = gr.Button('Show saved music')
                saved = panel()
                refresh.click(library, outputs=[saved[0], saved[1]], api_visibility='private')
            with gr.Tab('Help'):
                gr.Markdown('''### A good first try
Choose **Product or app ad**, **Under speech**, **Steady**, and **10 seconds**. Keep **No singing** on. Describe one or two sounds, then create music.

### Useful descriptions
- Camera gear: “A confident camera ad. Deep bass pulse, clean electronic percussion, spacious synths.”
- Food: “A playful cooking reel. Bouncy bass, plucked guitar, light drums, cheerful ending.”
- Voice-over: “Soft warm piano and gentle pads. No busy melody. Leave space for speaking.”

### If something goes wrong
No GPU: choose **Runtime → Change runtime type → GPU** in Colab. Out of memory: close other model jobs, free GPU memory and try a shorter request. A new seed can help with a poor musical result; it does not fix missing memory.

### Before publishing
Listen for unwanted voices, distortion and awkward endings. Check the MiniMax Music 3 Community License, including its public-output disclosure conditions. Resampling to a Premiere WAV does not add musical detail.

### Colab and your domain
Free Colab uses the notebook’s generation form. External web UI use is for a paid Colab runtime with a positive compute-unit balance, or a GPU host you control. The domain works only while its runtime and tunnel are running. There is no keep-alive or limit-bypass code.''')
        send.click(lambda path:path, results[3], source, api_visibility='private')
    return ui
