import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = patch.object(server, 'STORAGE', Path(self.temp.name))
        self.storage.start()
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.storage.stop()
        self.temp.cleanup()

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port)
        connection.request(method, path, body=body)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_upload_page_is_available(self):
        status, _, body = self.request('GET', '/upload')
        self.assertEqual(status, 200)
        self.assertIn(b'Enviar ficheiro', body)

    def test_upload_then_download_returns_identical_bytes_without_key(self):
        original = b'Brawl Stars binary' * 100000
        status, _, body = self.request('POST', '/upload?name=libg.so', original)
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(body)['url'], '/download')
        status, headers, downloaded = self.request('GET', '/download')
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, original)
        self.assertIn('libg.so', headers['Content-Disposition'])

    def test_new_upload_replaces_previous_download(self):
        self.request('POST', '/upload?name=first.bin', b'first')
        self.request('POST', '/upload?name=second.bin', b'second')
        status, headers, body = self.request('GET', '/download')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'second')
        self.assertIn('second.bin', headers['Content-Disposition'])

    def test_download_without_upload_is_not_found(self):
        status, _, _ = self.request('GET', '/download')
        self.assertEqual(status, 404)


if __name__ == '__main__':
    unittest.main()
