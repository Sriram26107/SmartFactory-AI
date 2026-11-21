import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from smartfactory.connectors.api import build_handler
from smartfactory.live.telemetry import recent_readings
from smartfactory.workflows import list_incidents


def test_api_ingestion_and_auth(tmp_path):
    handler=build_handler('a-very-long-local-test-secret',
                          telemetry_path=tmp_path/'telemetry.db',
                          workflow_path=tmp_path/'workflows.db',
                          data_path=tmp_path/'data.db')
    server=ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    url=f'http://127.0.0.1:{server.server_port}/api/v1/telemetry'
    try:
        body=json.dumps({'machine_id':'M-001','temperature_c':91,'vibration_mm_s':8}).encode()
        request=Request(url,body,headers={'Content-Type':'application/json'},method='POST')
        try:
            urlopen(request,timeout=5)
            assert False, 'Should require token'
        except HTTPError as error:
            assert error.code==401
        request.add_header('Authorization','Bearer a-very-long-local-test-secret')
        with urlopen(request,timeout=5) as response:
            assert response.status==201
            result=json.load(response)
        assert result['workflow']['created'] is True
        assert len(recent_readings(path=tmp_path/'telemetry.db'))==1
        assert len(list_incidents(path=tmp_path/'workflows.db'))==1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_api_requires_strong_token():
    import pytest
    with pytest.raises(ValueError):
        build_handler('short')
