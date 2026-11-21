"""Single-process public demo controls; local development keeps its local owner."""
from contextvars import ContextVar
import asyncio
import hashlib
import hmac
import os
import re
import secrets
import time
from collections import deque

from starlette.responses import JSONResponse

report_owner = ContextVar('report_owner', default='local')
PUBLIC_MODE = os.getenv('OSTEOLENS_PUBLIC_MODE', '0') == '1'
PUBLIC_ORIGIN = os.getenv('OSTEOLENS_PUBLIC_ORIGIN', '').rstrip('/')
secret_path = os.getenv('OSTEOLENS_SESSION_SECRET_FILE')
if secret_path:
    from pathlib import Path
    SESSION_SECRET = Path(secret_path).read_text().strip()
else:
    SESSION_SECRET = os.getenv('OSTEOLENS_SESSION_SECRET', '')
if PUBLIC_MODE and (len(SESSION_SECRET) < 32 or not PUBLIC_ORIGIN.startswith('https://')):
    raise RuntimeError('Public mode requires an HTTPS public origin and a session secret of at least 32 characters.')


class PublicAccessMiddleware:
    def __init__(self, app):
        self.app = app
        self.requests = {}
        self.active = 0
        self.last_cleanup = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not PUBLIC_MODE or not scope['path'].startswith('/api/'):
            return await self.app(scope, receive, send)
        from starlette.requests import Request
        request = Request(scope, receive)
        try:
            length = int(request.headers.get('content-length', '0'))
        except ValueError:
            return await JSONResponse({'detail': 'Invalid content length.'}, 400)(scope, receive, send)
        if length > 21*1024*1024:
            return await JSONResponse({'detail': 'Request body is too large.'}, 413)(scope, receive, send)
        origin = request.headers.get('origin')
        if origin and origin != PUBLIC_ORIGIN:
            return await JSONResponse({'detail': 'Origin not permitted.'}, 403)(scope, receive, send)
        if request.method not in {'GET', 'HEAD', 'OPTIONS'} and origin != PUBLIC_ORIGIN:
            return await JSONResponse({'detail': 'Use this website to submit requests.'}, 403)(scope, receive, send)
        # The reverse proxy is the only exposed service. Uvicorn trusts only that proxy.
        address = scope.get('client', ('unknown',))[0]
        now = time.monotonic()
        self.requests = {key: value for key, value in self.requests.items() if value and now-value[-1] < 60}
        if len(self.requests) >= 2048 and address not in self.requests:
            return await JSONResponse({'detail': 'Server busy. Try later.'}, 429)(scope, receive, send)
        history = self.requests.setdefault(address, deque(maxlen=60))
        while history and now-history[0] >= 60:
            history.popleft()
        if len(history) >= 60:
            return await JSONResponse({'detail': 'Too many requests. Wait one minute.'}, 429)(scope, receive, send)
        history.append(now)
        expensive = request.method == 'POST'
        if expensive and self.active >= 2:
            return await JSONResponse({'detail': 'The research server is busy. Try again shortly.'}, 429)(scope, receive, send)
        cookie = request.cookies.get('osteolens_session', '')
        parts = cookie.split('.')
        valid = len(parts) == 2 and re.fullmatch(r'[a-f0-9]{64}', parts[0]) and hmac.compare_digest(parts[1], self.sign(parts[0]))
        owner = parts[0] if valid else secrets.token_hex(32)
        token = report_owner.set(owner)
        if expensive:
            self.active += 1
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers.append((b'cache-control', b'no-store'))
                if not valid:
                    value = f'osteolens_session={owner}.{self.sign(owner)}; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=86400'
                    headers.append((b'set-cookie', value.encode()))
                message = {**message, 'headers': headers}
            await send(message)
        try:
            if expensive:
                chunks = []
                size = 0
                deadline = time.monotonic() + 45
                while True:
                    try:
                        message = await asyncio.wait_for(receive(), timeout=max(.01,deadline-time.monotonic()))
                    except asyncio.TimeoutError:
                        return await JSONResponse({'detail': 'Upload timed out.'}, 408)(scope, receive, secure_send)
                    if message['type'] == 'http.disconnect':
                        return
                    chunk = message.get('body', b'')
                    size += len(chunk)
                    if size > 21*1024*1024:
                        return await JSONResponse({'detail': 'Request body is too large.'}, 413)(scope, receive, secure_send)
                    chunks.append(chunk)
                    if not message.get('more_body', False):
                        break
                original_receive = receive
                delivered = False
                body = b''.join(chunks)
                async def buffered_receive():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {'type':'http.request', 'body':body, 'more_body':False}
                    return await original_receive()
                receive = buffered_receive
            if now-self.last_cleanup > 300:
                self.last_cleanup = now
                from backend.report_store import purge_expired_reports
                await asyncio.to_thread(purge_expired_reports)
            await self.app(scope, receive, secure_send)
        finally:
            report_owner.reset(token)
            if expensive:
                self.active -= 1

    @staticmethod
    def sign(value):
        return hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
