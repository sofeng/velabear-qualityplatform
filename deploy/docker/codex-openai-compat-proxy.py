#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, urlunsplit


def normalize_target_base_url(value: str) -> str:
    normalized = str(value or '').strip().rstrip('/')
    if not normalized:
        return ''
    parsed = urlsplit(normalized)
    path = parsed.path.rstrip('/')
    lowered_path = path.lower()
    for suffix in ('/v1/chat/completions', '/chat/completions', '/v1/responses', '/responses'):
        if lowered_path.endswith(suffix):
            trimmed_path = path[: -len(suffix)].rstrip('/')
            return urlunsplit((parsed.scheme, parsed.netloc, trimmed_path, '', '')).rstrip('/')
    return normalized


TARGET_BASE_URL = normalize_target_base_url(os.environ.get('TESTHUB_CODEX_PROVIDER_BASE_URL', ''))
LISTEN_HOST = os.environ.get('TESTHUB_CODEX_COMPAT_PROXY_HOST', '127.0.0.1').strip() or '127.0.0.1'
LISTEN_PORT = int(os.environ.get('TESTHUB_CODEX_COMPAT_PROXY_PORT', '18080') or 18080)
API_KEY = os.environ.get('OPENAI_API_KEY', '')

HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
}

UNSUPPORTED_CHAT_FIELDS = {
    'reasoning_effort',
    'verbosity',
    'store',
    'metadata',
    'parallel_tool_calls',
}


def normalize_path(path: str) -> str:
    if path == '/v1/chat/completions':
        return '/chat/completions'
    if path == '/v1/models':
        return '/models'
    return path


def normalize_message_content(content):
    if isinstance(content, str) or content is None:
        return content or ''
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get('text') or item.get('content') or ''
                if isinstance(text, str):
                    parts.append(text)
        return '\n'.join(part for part in parts if part)
    return str(content)


def normalize_chat_payload(raw_body: bytes) -> bytes:
    if not raw_body:
        return raw_body
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except Exception:
        return raw_body
    if not isinstance(payload, dict):
        return raw_body

    for field_name in UNSUPPORTED_CHAT_FIELDS:
        payload.pop(field_name, None)

    messages = payload.get('messages')
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            if message.get('role') == 'developer':
                message['role'] = 'system'
            if 'content' in message:
                message['content'] = normalize_message_content(message.get('content'))

    if os.environ.get('TESTHUB_CODEX_COMPAT_PROXY_DEBUG') == '1':
        sys.stderr.write(
            '[testhub-codex-proxy] chat payload keys='
            f'{sorted(payload.keys())} '
            f"stream={payload.get('stream')} "
            f"model={payload.get('model')} "
            f"roles={[message.get('role') for message in payload.get('messages', []) if isinstance(message, dict)]}\n"
        )
        sys.stderr.flush()

    return json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class CompatProxyHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, _format, *args):
        return

    def do_GET(self):
        if self.path == '/health':
            self.respond_bytes(200, b'ok', 'text/plain')
            return
        self.forward(None)

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or '0')
        raw_body = self.rfile.read(length) if length else b''
        if self.path in {'/chat/completions', '/v1/chat/completions'}:
            raw_body = normalize_chat_payload(raw_body)
        self.forward(raw_body)

    def forward(self, body):
        if not TARGET_BASE_URL:
            self.respond_json(502, {'error': {'message': 'TESTHUB_CODEX_PROVIDER_BASE_URL is required'}})
            return

        url = TARGET_BASE_URL + normalize_path(self.path)
        headers = {}
        for name, value in self.headers.items():
            lower_name = name.lower()
            if lower_name in HOP_BY_HOP_HEADERS or lower_name in {'host', 'content-length'}:
                continue
            headers[name] = value
        headers['Content-Type'] = headers.get('Content-Type') or 'application/json'
        if 'Authorization' not in headers and API_KEY:
            headers['Authorization'] = f'Bearer {API_KEY}'

        try:
            request = urllib.request.Request(url, data=body, method=self.command, headers=headers)
            with urllib.request.urlopen(request, timeout=180) as response:
                self.relay_response(response.status, response.headers, response)
        except urllib.error.HTTPError as exc:
            self.relay_response(exc.code, exc.headers, exc)
        except Exception as exc:
            if os.environ.get('TESTHUB_CODEX_COMPAT_PROXY_DEBUG') == '1':
                sys.stderr.write(f'[testhub-codex-proxy] forward error {type(exc).__name__}: {exc}\n')
                sys.stderr.flush()
            self.respond_json(502, {'error': {'message': str(exc), 'type': 'testhub_proxy_error'}})

    def relay_response(self, status_code, headers, response):
        content_type = headers.get('Content-Type') or 'application/json'
        if content_type.startswith('text/event-stream'):
            self.send_response(status_code)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'close')
            self.end_headers()
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
            return

        body = response.read()
        self.respond_bytes(status_code, body, content_type)

    def respond_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.respond_bytes(status_code, body, 'application/json')

    def respond_bytes(self, status_code, body, content_type):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), CompatProxyHandler)
    server.serve_forever()


if __name__ == '__main__':
    main()
