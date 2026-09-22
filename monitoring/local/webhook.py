"""Local-only Alertmanager webhook receiver for repeatable integration checks."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

events = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        event = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        events.append(event)
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        body = json.dumps(events).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)


HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
