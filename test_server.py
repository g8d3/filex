#!/usr/bin/env python3
"""Tests for the filex file server."""

import os
import sys
import json
import time
import http.server
import tempfile
import threading
import unittest
from http.client import HTTPConnection

import serve_md


def read_all(conn, path):
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read()
    return resp.status, resp.getheaders(), body


class TestFileServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="filex_test_")
        os.makedirs(os.path.join(cls.tmpdir, "sub"))
        os.makedirs(os.path.join(cls.tmpdir, ".hidden"))
        with open(os.path.join(cls.tmpdir, "test.txt"), "w") as f:
            f.write("hello world")
        with open(os.path.join(cls.tmpdir, "test.md"), "w") as f:
            f.write("# Title\n\nHello *world*")
        with open(os.path.join(cls.tmpdir, "script.py"), "w") as f:
            f.write("def foo():\n    pass\n")
        with open(os.path.join(cls.tmpdir, "sub", "nested.txt"), "w") as f:
            f.write("nested")
        with open(os.path.join(cls.tmpdir, ".gitignore"), "w") as f:
            f.write("*.log")

        # Start server on a random port
        import socket
        cls.sock = socket.socket()
        cls.sock.bind(("127.0.0.1", 0))
        cls.port = cls.sock.getsockname()[1]
        cls.sock.close()

        cls.server = http.server.HTTPServer(("127.0.0.1", cls.port), serve_md.Handler)
        serve_md.Handler.root_dir = cls.tmpdir
        serve_md.Handler.real_root = os.path.realpath(cls.tmpdir)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def conn(self):
        c = HTTPConnection("127.0.0.1", self.port, timeout=5)
        return c

    def test_root_returns_html(self):
        c = self.conn()
        status, headers, body = read_all(c, "/")
        c.close()
        self.assertEqual(status, 200)
        h = {k.lower(): v for k, v in headers}
        ct = h.get("content-type", "")
        self.assertIn("text/html", ct)
        self.assertIn(b"toolbar", body)

    def test_text_file(self):
        c = self.conn()
        status, headers, body = read_all(c, "/test.txt")
        c.close()
        self.assertEqual(status, 200)
        self.assertIn(b"hello world", body)

    def test_markdown_file(self):
        c = self.conn()
        status, headers, body = read_all(c, "/test.md")
        c.close()
        self.assertEqual(status, 200)
        self.assertIn(b"marked", body)  # should use marked.js template

    def test_python_file_highlighted(self):
        c = self.conn()
        status, headers, body = read_all(c, "/script.py")
        c.close()
        self.assertEqual(status, 200)
        self.assertIn(b"highlight", body)

    def test_nested_file(self):
        c = self.conn()
        status, headers, body = read_all(c, "/sub/nested.txt")
        c.close()
        self.assertEqual(status, 200)
        self.assertIn(b"nested", body)

    def test_dotfile(self):
        c = self.conn()
        status, headers, body = read_all(c, "/.gitignore")
        c.close()
        self.assertEqual(status, 200)
        self.assertIn(b"*.log", body)

    def test_post_saves_file(self):
        c = self.conn()
        data = "content=new+text"
        c.request("POST", "/test.txt", body=data,
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp = c.getresponse()
        body = resp.read()
        c.close()
        self.assertEqual(resp.status, 200)

        with open(os.path.join(self.tmpdir, "test.txt")) as f:
            self.assertEqual(f.read(), "new text")

        # Restore
        with open(os.path.join(self.tmpdir, "test.txt"), "w") as f:
            f.write("hello world")

    def test_directory_json(self):
        c = self.conn()
        status, headers, body = read_all(c, "/?format=json")
        c.close()
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIsInstance(data, list)
        names = [e["name"] for e in data]
        self.assertIn("test.txt", names)
        self.assertIn("sub", names)

    def test_range_request(self):
        c = self.conn()
        c.request("GET", "/test.txt", headers={"Range": "bytes=0-4"})
        resp = c.getresponse()
        body = resp.read()
        c.close()
        # Text files serve full HTML with code content, not raw bytes
        # Range requests are supported for media files (video/audio)
        self.assertIn(resp.status, (200, 206))

    def test_path_traversal_blocked(self):
        c = self.conn()
        status, headers, body = read_all(c, "/../../../etc/passwd")
        c.close()
        self.assertIn(status, (404, 403))

    def test_dir_json_has_size_and_date(self):
        c = self.conn()
        status, headers, body = read_all(c, "/?format=json")
        c.close()
        data = json.loads(body)
        self.assertIsInstance(data, list)
        for e in data:
            self.assertIn("name", e)
            self.assertIn("size", e)
            self.assertIn("date", e)

    def test_script_py_has_ace_editor(self):
        c = self.conn()
        status, headers, body = read_all(c, "/script.py")
        c.close()
        self.assertIn(b"ace", body.lower())

    def test_404_for_nonexistent(self):
        c = self.conn()
        status, headers, body = read_all(c, "/nonexistent.xyz")
        c.close()
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
