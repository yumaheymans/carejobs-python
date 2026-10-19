"""Offline tests: a local HTTP server stands in for CareJobs.Now."""

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from carejobs import CareJobs, CareJobsError


def ok(structured, text="summary"):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": text}], "structuredContent": structured},
    }


class Stub:
    """Serves one canned reply and records what it was sent."""

    def __init__(self, body, status=200, content_type="application/json", delay=0.0):
        self.seen = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                stub.seen.append({"headers": dict(self.headers), "body": json.loads(raw)})
                time.sleep(delay)
                payload = body if isinstance(body, str) else json.dumps(body)
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(payload.encode())))
                    self.end_headers()
                    self.wfile.write(payload.encode())
                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class ErrorTests(unittest.TestCase):
    def stub(self, *args, **kwargs):
        stub = Stub(*args, **kwargs)
        self.addCleanup(stub.close)
        return stub

    def test_sends_the_documented_request(self):
        stub = self.stub(ok({"total": 0, "pay": None, "jobs": [], "more": ""}))
        cj = CareJobs(base_url=stub.url, user_agent="my-app/2")
        result = cj.search_jobs("icu", min_hourly_usd=50, remote=True)
        sent = stub.seen[0]
        self.assertEqual(sent["headers"]["Content-Type"], "application/json")
        self.assertEqual(sent["headers"]["Accept"], "application/json, text/event-stream")
        self.assertEqual(sent["headers"]["User-Agent"], "my-app/2")
        self.assertEqual(sent["body"]["method"], "tools/call")
        self.assertEqual(
            sent["body"]["params"],
            {
                "name": "search_healthcare_jobs",
                "arguments": {"query": "icu", "min_hourly_usd": 50, "remote": True},
            },
        )
        self.assertEqual(result.text, "summary")
        self.assertEqual(result["total"], 0)

    def test_reads_an_event_stream_answer(self):
        body = "event: message\ndata: " + json.dumps(ok({"total": 7})) + "\n\n"
        stub = self.stub(body, content_type="text/event-stream")
        self.assertEqual(CareJobs(base_url=stub.url).search_jobs()["total"], 7)

    def test_http_error(self):
        stub = self.stub("slow down", status=429, content_type="text/plain")
        with self.assertRaises(CareJobsError) as caught:
            CareJobs(base_url=stub.url).get_job_market()
        self.assertEqual(caught.exception.code, "http")
        self.assertEqual(caught.exception.status, 429)

    def test_rpc_error(self):
        stub = self.stub({"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "Unknown tool: x"}})
        with self.assertRaises(CareJobsError) as caught:
            CareJobs(base_url=stub.url).get_job_market()
        self.assertEqual(caught.exception.code, "rpc")
        self.assertEqual(caught.exception.rpc_code, -32602)
        self.assertEqual(str(caught.exception), "Unknown tool: x")

    def test_tool_error(self):
        stub = self.stub(
            {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "Unknown kind 'x'."}], "isError": True}}
        )
        with self.assertRaises(CareJobsError) as caught:
            CareJobs(base_url=stub.url).get_pay()
        self.assertEqual(caught.exception.code, "tool")
        self.assertEqual(caught.exception.tool, "get_healthcare_pay")
        self.assertEqual(str(caught.exception), "Unknown kind 'x'.")

    def test_protocol_errors(self):
        for body in ("<html>hi</html>", {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}):
            stub = self.stub(body)
            with self.assertRaises(CareJobsError) as caught:
                CareJobs(base_url=stub.url).get_job_market()
            self.assertEqual(caught.exception.code, "protocol")

    def test_network_error(self):
        stub = Stub(ok({}))
        url = stub.url
        stub.close()  # nothing listens on this port any more
        with self.assertRaises(CareJobsError) as caught:
            CareJobs(base_url=url, timeout=2).get_job_market()
        self.assertEqual(caught.exception.code, "network")

    def test_timeout(self):
        stub = self.stub(ok({}), delay=1.0)
        with self.assertRaises(CareJobsError) as caught:
            CareJobs(base_url=stub.url, timeout=0.2).get_job_market()
        self.assertEqual(caught.exception.code, "timeout")


if __name__ == "__main__":
    unittest.main()
