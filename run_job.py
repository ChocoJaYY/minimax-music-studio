"""Notebook/agent client. JSON request on stdin; logs on stderr; result JSON on stdout."""
import json
import sys
from studio.engine import Engine
from studio.prompts import make_request

engine = Engine()
try:
    request = make_request(**json.load(sys.stdin))
    print(json.dumps(engine.generate(request)), flush=True)
finally:
    engine.close()
