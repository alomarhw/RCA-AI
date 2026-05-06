from http.client import HTTPConnection
from threading import Thread
from time import sleep

from rca_ai.platform import ResearchPaperPlatform
from rca_ai.server import RCAAIRequestHandler
from http.server import ThreadingHTTPServer


def test_server_serves_browser_ui_and_demo_api(tmp_path):
    class Handler(RCAAIRequestHandler):
        app = ResearchPaperPlatform(tmp_path / "data")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    sleep(0.01)
    host, port = server.server_address
    try:
        connection = HTTPConnection(host, port)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        assert response.status == 200
        assert "RCA-AI Research Writing Platform" in body

        connection.request("POST", "/demo", body='{"name":"Demo"}', headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        assert response.status == 201
        assert "Demo" in body
    finally:
        server.shutdown()
        server.server_close()
