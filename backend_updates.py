"""Identify one backend lifetime and serve pages tied to that lifetime."""
from uuid import uuid4
from fastapi.responses import HTMLResponse

BACKEND_INSTANCE = uuid4().hex

def dashboard_page(path):
    html = path.read_text(encoding='utf-8')
    marker = (f'<meta name="backend-instance" content="{BACKEND_INSTANCE}">'
              f'<script defer src="/static/backend-updates.js?v={BACKEND_INSTANCE}"></script>')
    return HTMLResponse(html.replace('</head>', marker + '</head>', 1),
                        headers={'Cache-Control': 'no-store'})
