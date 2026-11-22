"""Privacy restrictions for the research prototype; not a compliance certification."""
import json
import os
from pathlib import Path
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
NOTICE_VERSION = '2026-11-22.2'
QUESTIONS = {
    'compare_tumours': 'How do osteosarcoma and Ewing sarcoma differ?',
    'imaging': 'What imaging modalities are used to assess a suspected bone tumour?',
    'transition': 'What does a wide zone of transition mean in bone imaging?',
    'benign_malignant': 'How are benign bone tumours different from malignant ones?',
    'case_summary': 'Explain the available information for this case.',
    'heatmap': 'Explain what the heatmap is showing.',
    'source_label': 'What does the source label tell us, and what does it not tell us?',
    'limitations': 'What limitations matter when interpreting this model output?',
}


def operator_config():
    path = Path(os.getenv('OSTEOLENS_PRIVACY_CONFIG', ROOT / 'deploy/runtime/privacy-config.json'))
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError): return {}


def release_issues(config):
    required = ('controller_name', 'privacy_email', 'technical_data_legal_basis',
                'provider_transfer_assessment', 'technical_data_retention', 'reviewed_by', 'reviewed_on')
    missing = [name for name in required if not isinstance(config.get(name), str) or not config[name].strip()
               or config[name].strip().lower() in {'pending','todo','tbd'}]
    if '@' not in (config.get('privacy_email') or ''): missing.append('valid_privacy_email')
    if config.get('approved_for_research_demo') is not True: missing.append('operator_review')
    return sorted(set(missing))


def privacy_status():
    config = operator_config()
    fields = ('controller_name','privacy_email','technical_data_legal_basis','provider_transfer_assessment','technical_data_retention')
    return {'notice_version': NOTICE_VERSION, 'mode': 'research_and_on_device_reports',
            'personal_uploads_enabled': False, 'on_device_reports_enabled': True, 'free_text_chat_enabled': True,
            **{key:config.get(key) or None for key in fields}, 'release_ready': not release_issues(config)}


class PrivacyGuardMiddleware:
    """Reject legacy upload/chat paths before multipart parsing or body buffering."""
    def __init__(self, app): self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope, receive, send)
        path = scope['path'].rstrip('/')
        async def privacy_send(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers.extend([
                    (b'referrer-policy', b'no-referrer'), (b'x-content-type-options', b'nosniff'),
                    (b'permissions-policy', b'camera=(), microphone=(), geolocation=()'),
                    (b'content-security-policy', b"default-src 'self'; script-src 'self'; worker-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"),
                ])
                if path.startswith('/api') or path in {'', '/index.html'}:
                    headers = [(k,v) for k,v in headers if k.lower() != b'cache-control']
                    headers.append((b'cache-control', b'no-store'))
                message = {**message, 'headers':headers}
            await send(message)
        if path == '/api/reports' and scope['method'] == 'GET':
            return await JSONResponse({'reports': [], 'mode': 'published_examples_only'})(scope, receive, privacy_send)
        if (path.startswith('/api/reports') and not path.startswith('/api/reports/examples/')) or path == '/api/assistant/chat':
            return await JSONResponse({'detail':'Personal report uploads and free-text submissions are disabled. Use published research examples.',
                                       'code':'personal_data_processing_disabled'},403)(scope, receive, privacy_send)
        if scope['method'] in {'POST','PUT','PATCH'}:
            headers = dict(scope['headers'])
            try: length = int(headers.get(b'content-length', b'0'))
            except ValueError: length = 99999
            max_length = 8192 if path == '/api/assistant/research' else 0
            if length > max_length or b'transfer-encoding' in headers:
                return await JSONResponse({'detail':'This research endpoint does not accept document content.'},413)(scope, receive, privacy_send)
        await self.app(scope, receive, privacy_send)
