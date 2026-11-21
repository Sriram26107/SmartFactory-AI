"""Authenticated, local-first read-only ingestion API.

POST /api/v1/telemetry with JSON; POST /api/v1/datasets/<name> with CSV.
GET /api/v1/health. Never issues commands to machines.
"""
import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from smartfactory.live.telemetry import save_reading, validate
from smartfactory.workflows import process_telemetry
from smartfactory.integration import SCHEMAS, import_csv

MAX_BODY = 8_000_000

def build_handler(token, telemetry_path=None, workflow_path=None, data_path=None):
    if not token or len(token) < 16:
        raise ValueError('SMARTFACTORY_API_TOKEN must contain at least 16 characters')
    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code, payload):
            body = json.dumps(payload).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def _authorized(self):
            return hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+token)
        def _body(self):
            size = self.headers.get('Content-Length')
            if size is None or not size.isdigit() or int(size) > MAX_BODY:
                raise ValueError('Content-Length required and <= 8 MB')
            return self.rfile.read(int(size))
        def do_GET(self):
            if not self._authorized():
                return self._reply(401, {'error':'Unauthorized'})
            if self.path == '/api/v1/health':
                return self._reply(200, {'status':'ready'})
            return self._reply(404, {'error':'Not found'})
        def do_POST(self):
            if not self._authorized():
                return self._reply(401, {'error':'Unauthorized'})
            try:
                if self.path == '/api/v1/telemetry':
                    if self.headers.get('Content-Type','').split(';')[0].strip() != 'application/json':
                        return self._reply(415, {'error':'Expected application/json'})
                    payload = json.loads(self._body().decode('utf-8'))
                    validate(payload)
                    reading = save_reading(payload, source='api', path=telemetry_path)
                    workflow = process_telemetry(payload, source='api', path=workflow_path)
                    return self._reply(201, {'reading':reading, 'workflow':workflow})
                prefix = '/api/v1/datasets/'
                if self.path.startswith(prefix):
                    name = self.path[len(prefix):]
                    if name not in SCHEMAS:
                        return self._reply(404, {'error':'Unknown dataset'})
                    if self.headers.get('Content-Type','').split(';')[0].strip() not in ('text/csv','application/csv'):
                        return self._reply(415, {'error':'Expected text/csv'})
                    count = import_csv(name, self._body(), path=data_path)
                    return self._reply(201, {'dataset':name, 'rows':count})
                return self._reply(404, {'error':'Not found'})
            except (ValueError, UnicodeDecodeError) as exc:
                return self._reply(400, {'error':str(exc)})
            except Exception:
                self.log_error('Unexpected ingestion error')
                return self._reply(500, {'error':'Internal server error'})
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    server=ThreadingHTTPServer((args.host,args.port),build_handler(os.getenv('SMARTFACTORY_API_TOKEN','')))
    print(f'Local ingestion API listening at http://{args.host}:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
