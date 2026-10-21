import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import server


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DATA_DIR': self.data.name, 'UPLOAD_KEY': 'test-key'})
        self.env.start()
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.env.stop()
        self.data.cleanup()

    def request(self, method, path, body=None, key=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port)
        headers = {}
        if key:
            headers['Authorization'] = f'Bearer {key}'
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_upload_page_is_available(self):
        status, _, body = self.request('GET', '/upload')
        self.assertEqual(status, 200)
        self.assertIn(b'Enviar ficheiro', body)

    def test_upload_requires_key(self):
        status, _, body = self.request('POST', '/upload?name=libg.so', b'file')
        self.assertEqual(status, 401)
        self.assertIn('error', json.loads(body))

    def test_upload_then_download_returns_identical_bytes(self):
        original = b'Brawl Stars binary' * 100000
        status, _, body = self.request('POST', '/upload?name=libg.so', original, 'test-key')
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(body)['url'], '/download')
        status, headers, downloaded = self.request('GET', '/download')
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, original)
        self.assertIn('libg.so', headers['Content-Disposition'])

    def test_latest_upload_replaces_previous_download(self):
        self.request('POST', '/upload?name=first.bin', b'first', 'test-key')
        self.request('POST', '/upload?name=second.bin', b'second', 'test-key')
        status, headers, body = self.request('GET', '/download')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'second')
        self.assertIn('second.bin', headers['Content-Disposition'])

    def test_download_without_upload_is_not_found(self):
        status, _, _ = self.request('GET', '/download')
        self.assertEqual(status, 404)


if __name__ == '__main__':
    unittest.main()
