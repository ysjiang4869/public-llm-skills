import importlib.util
import json
import pathlib
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace


SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "apollo_config.py"
SPEC = importlib.util.spec_from_file_location("apollo_config", SCRIPT)
apollo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(apollo)


class ApolloConfigTest(unittest.TestCase):
    def test_public_plain_http_is_allowed(self):
        self.assertEqual(
            apollo.validate_portal_url("http://36.137.221.140:30006/"),
            "http://36.137.221.140:30006",
        )

    def test_loopback_and_cluster_service_http_are_allowed(self):
        self.assertEqual(
            apollo.validate_portal_url("http://127.0.0.1:18070/"),
            "http://127.0.0.1:18070",
        )
        self.assertEqual(
            apollo.validate_portal_url("http://apollo-portal.apollo.svc:8070"),
            "http://apollo-portal.apollo.svc:8070",
        )

    def test_portal_url_rejects_unsupported_scheme_and_embedded_credentials(self):
        with self.assertRaisesRegex(apollo.ApolloError, "absolute http\(s\) URL"):
            apollo.validate_portal_url("ftp://apollo.example.com")
        with self.assertRaisesRegex(apollo.ApolloError, "credentials must not be embedded"):
            apollo.validate_portal_url("http://user:password@apollo.example.com")

    def test_diff_categorizes_changes(self):
        result = apollo.calculate_diff(
            {"same": "1", "changed": "2", "added": "3"},
            {"same": "1", "changed": "old", "removed": "4"},
        )
        self.assertEqual(result["added"], ["added"])
        self.assertEqual(result["changed"], ["changed"])
        self.assertEqual(result["removed"], ["removed"])
        self.assertEqual(result["unchanged"], ["same"])

    def test_default_diff_does_not_expose_values(self):
        result = apollo.diff_output({"secret": "new-value"}, {"secret": "old-value"})
        rendered = str(result)
        self.assertNotIn("new-value", rendered)
        self.assertNotIn("old-value", rendered)
        self.assertIn("sha256:", rendered)

    def test_path_segment_encodes_slashes_and_spaces(self):
        self.assertEqual(apollo.path_segment("a/b c"), "a%2Fb%20c")

    def test_namespaces_lists_metadata_and_keys_without_values(self):
        class Client:
            def request(self, method, path):
                self.call = (method, path)
                return [
                    {
                        "appId": "demo",
                        "clusterName": "default",
                        "namespaceName": "application",
                        "format": "properties",
                        "isPublic": False,
                        "items": [
                            {"key": "feature.enabled", "value": "true"},
                            {"key": "password", "value": "sensitive-value"},
                        ],
                    }
                ]

        client = Client()
        args = SimpleNamespace(
            portal_url="http://apollo.example.com",
            env="DEV",
            app="demo",
            cluster="default",
        )
        result = apollo.command_namespaces(client, args)

        self.assertEqual(
            client.call,
            ("GET", "envs/DEV/apps/demo/clusters/default/namespaces"),
        )
        self.assertEqual(result["namespaceCount"], 1)
        self.assertEqual(result["namespaces"][0]["itemCount"], 2)
        self.assertEqual(result["namespaces"][0]["keys"], ["feature.enabled", "password"])
        self.assertNotIn("sensitive-value", str(result))

    def test_set_accepts_literal_value_including_empty_string(self):
        args = SimpleNamespace(
            value="new-value",
            value_stdin=False,
            value_env=None,
            value_file=None,
        )
        self.assertEqual(apollo.read_value(args), "new-value")

        args.value = ""
        self.assertEqual(apollo.read_value(args), "")

    def test_set_rejects_multiple_value_sources(self):
        args = SimpleNamespace(
            value="new-value",
            value_stdin=True,
            value_env=None,
            value_file=None,
        )
        with self.assertRaisesRegex(apollo.ApolloError, "exactly one"):
            apollo.read_value(args)

    def test_http_client_sends_consumer_token_and_query(self):
        observed = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                payload = json.dumps({"ok": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, _format, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = apollo.ApolloClient(
                f"http://127.0.0.1:{server.server_port}", "test-consumer-token"
            )
            result = client.request("GET", "apps/demo/envclusters", {"page": 0})
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(observed["path"], "/openapi/v1/apps/demo/envclusters?page=0")
        self.assertEqual(observed["authorization"], "test-consumer-token")


if __name__ == "__main__":
    unittest.main()
