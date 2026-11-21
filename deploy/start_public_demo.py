"""Run a free temporary HTTPS demo; Ctrl+C stops only its own child processes."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloudflared', required=True, type=Path)
    parser.add_argument('--port',type=int,default=8002)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    # Complete the operator's review before establishing any public connection.
    sys.path.insert(0,str(root))
    from backend.privacy import operator_config, release_issues
    issues=release_issues(operator_config())
    if issues:
        sys.exit('Public launch blocked: privacy/operator review is incomplete ('+', '.join(issues)+'). See PRIVACY_REVIEW.md. Personal uploads remain disabled regardless of this review.')
    runtime=root/'deploy/runtime';runtime.mkdir(parents=True,exist_ok=True)
    if not (root/'dist/index.html').is_file():
        sys.exit('Run npm run build first.')
    if not args.cloudflared.is_file():sys.exit('Official cloudflared executable was not found.')
    with socket.socket() as check:
        try:check.bind(('127.0.0.1',args.port))
        except OSError:sys.exit('Port is in use. Stop the previous public demo before restarting.')
    state=runtime/'public-demo.json'
    if state.exists():
        previous=json.loads(state.read_text())
        # Avoid replacing a tunnel still running while its API is initializing.
        pid = previous.get('launcher_pid')
        if pid and os.name == 'nt':
            listing = subprocess.run(['tasklist','/FI',f'PID eq {int(pid)}','/FO','CSV','/NH'],capture_output=True,text=True)
            if f'"{int(pid)}"' in listing.stdout:
                sys.exit('A demo launcher is already running. Stop it before restarting.')
    secret=runtime/'session-secret.txt'
    if not secret.exists():secret.write_text(secrets.token_hex(32))
    state.write_text(json.dumps({'launcher_pid':os.getpid(),'status':'starting'}))
    children=[]
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    try:
        with (runtime/'tunnel.log').open('w',encoding='utf-8') as tunnel_log, (runtime/'api.log').open('w',encoding='utf-8') as api_log:
            tunnel=subprocess.Popen([str(args.cloudflared.resolve()),'tunnel','--url',f'http://127.0.0.1:{args.port}',
                '--protocol','http2','--no-autoupdate'],stdout=tunnel_log,stderr=subprocess.STDOUT,creationflags=flags)
            children.append(tunnel)
            origin=None
            for _ in range(90):
                if tunnel.poll() is not None:raise RuntimeError('Tunnel exited. See deploy/runtime/tunnel.log.')
                log=(runtime/'tunnel.log').read_text(encoding='utf-8',errors='replace')
                match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',log)
                if match:origin=match.group(0);break
                time.sleep(1)
            if not origin:raise RuntimeError('No public tunnel URL was returned. See deploy/runtime/tunnel.log.')
            env={**os.environ,'OSTEOLENS_PUBLIC_MODE':'1','OSTEOLENS_PUBLIC_ORIGIN':origin,
                'OSTEOLENS_SESSION_SECRET_FILE':str(secret),'OSTEOLENS_REPORT_DATA_DIR':str(root/'backend/data/public-reports')}
            api=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(args.port),
                '--workers','1','--no-access-log','--proxy-headers','--forwarded-allow-ips','127.0.0.1'],cwd=root,env=env,
                stdout=api_log,stderr=subprocess.STDOUT,creationflags=flags)
            children.append(api)
            ready=False
            for _ in range(45):
                if api.poll() is not None:raise RuntimeError('API exited. See deploy/runtime/api.log.')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/health',timeout=2) as response:
                        ready=response.status==200
                    if ready:break
                except OSError:time.sleep(1)
            if not ready:raise RuntimeError('API did not become ready.')
            state.write_text(json.dumps({'launcher_pid':os.getpid(),'api_pid':api.pid,'tunnel_pid':tunnel.pid,
                'url':origin,'status':'running','port':args.port},indent=2))
            print(f'Public demo: {origin}\nKeep this computer awake and connected. Ctrl+C stops this demo.',flush=True)
            while all(process.poll() is None for process in children):time.sleep(2)
            raise RuntimeError('A demo service stopped. Check logs and restart the launcher.')
    except KeyboardInterrupt:print('Stopping public demo.',flush=True)
    finally:
        for process in reversed(children):
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                else:
                    process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill()
        state.write_text(json.dumps({'status':'stopped'}))


if __name__=='__main__':main()
