import argparse
import os
from studio.paths import OUTPUTS, DATA, configure

configure()
from studio.engine import Engine
from studio.ui import create_ui

parser = argparse.ArgumentParser()
parser.add_argument('--preview', action='store_true', help='Local layout preview with generation disabled.')
parser.add_argument('--port', type=int, default=8188)
args = parser.parse_args()
password = os.environ.get('MUSIC_UI_PASSWORD', '')
if not args.preview and len(password) < 12:
    raise RuntimeError('Set MUSIC_UI_PASSWORD to at least 12 characters before exposing the web UI.')
engine = Engine()
ui = create_ui(engine, args.preview)
ui.queue(max_size=8, default_concurrency_limit=1).launch(
    server_name='127.0.0.1', server_port=args.port, share=False, inbrowser=False,
    auth=None if args.preview else (os.environ.get('MUSIC_UI_USER', 'chocojayy'), password),
    allowed_paths=[str(OUTPUTS)], blocked_paths=[str(DATA)])
