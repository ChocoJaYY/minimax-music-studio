"""CPU-only local checks for the real app's login and file boundaries."""
import http.cookiejar
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.paths import ROOT, DATA, OUTPUTS, configure

configure()
password = secrets.token_urlsafe(24)
env = os.environ.copy()
env['MUSIC_UI_PASSWORD'] = password
env['MUSIC_UI_USER'] = 'music'
public = OUTPUTS / 'auth-public-probe.txt'
private = DATA / 'auth-private-probe.txt'
public.write_text('output-probe', encoding='utf-8')
private.write_text('runtime-probe', encoding='utf-8')
base = 'http://127.0.0.1:8191'
process = None


def denied(opener, path):
    try:
        opener.open(base + path)
        raise AssertionError('Protected route was accessible: ' + path)
    except urllib.error.HTTPError as error:
        assert error.code in (400, 401, 403, 404), error.code


try:
    with (DATA/'logs/auth-check.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(ROOT/'app.py'), '--port', '8191'],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError('Auth-check app failed to start.')
            try:
                urllib.request.urlopen(base+'/', timeout=1)
                break
            except OSError:
                time.sleep(1)
        else:
            raise TimeoutError('Auth-check app startup timed out.')
        anon = urllib.request.build_opener()
        denied(anon, '/config')
        file_route = '/gradio_api/file='
        denied(anon, file_route+urllib.parse.quote(public.as_posix(),safe='/'))
        wrong = urllib.request.Request(base+'/login', data=urllib.parse.urlencode({'username':'music','password':'wrong'}).encode())
        try:
            anon.open(wrong)
            raise AssertionError('Wrong password was accepted.')
        except urllib.error.HTTPError as error:
            assert error.code in (400,401)
        owner = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        owner.open(urllib.request.Request(base+'/login',data=urllib.parse.urlencode({'username':'music','password':password}).encode()))
        with owner.open(base+'/config') as response:
            config = json.load(response)
        assert config['components']
        with owner.open(base+file_route+urllib.parse.quote(public.as_posix(),safe='/')) as response:
            assert response.read()==b'output-probe'
        denied(owner, file_route+urllib.parse.quote(private.as_posix(),safe='/'))
        record = {'status':'succeeded','anonymous_config_blocked':True,'anonymous_download_blocked':True,
                  'wrong_password_blocked':True,'authenticated_output_download_passed':True,
                  'private_runtime_file_blocked':True,'gpu_generation_performed':False}
        (ROOT/'validation/auth-check.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps(record))
finally:
    if process is not None and process.poll() is None:
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
        else:
            process.terminate()
        process.wait(timeout=20)
    public.unlink(missing_ok=True)
    private.unlink(missing_ok=True)
