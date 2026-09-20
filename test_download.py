import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,AsyncMock
import httpx
from assemble_client import assemble
from portal import home_html
import gateway

class DownloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_installer_manifest_and_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=b'MZ-installer-fixture'
            (root/'client.part01').write_bytes(data)
            (root/'client-manifest.json').write_text(json.dumps({'filename':'StudyPilotC-Setup.exe','parts':['client.part01'],'sha256':hashlib.sha256(data).hexdigest()}))
            self.assertEqual(assemble(root).name,'StudyPilotC-Setup.exe')
            app=gateway.create_app(gateway.Config(database=str(root/'access.sqlite3')),AsyncMock())
            with patch.object(gateway,'__file__',str(root/'gateway.py')):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    response=await client.get('/download')
                    self.assertEqual(response.content,data)
                    self.assertIn('StudyPilotC-Setup.exe',response.headers['content-disposition'])
    async def test_verified_archive_is_served_without_api_or_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=b'PK\x03\x04fixture'
            (root/'client.part01').write_bytes(data)
            (root/'client-manifest.json').write_text(json.dumps({'parts':['client.part01'],'sha256':hashlib.sha256(data).hexdigest()}))
            self.assertEqual(assemble(root).read_bytes(),data)
            upstream=AsyncMock();app=gateway.create_app(gateway.Config(database=str(root/'access.sqlite3')),upstream)
            with patch.object(gateway,'__file__',str(root/'gateway.py')):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    self.assertIn('href="/download"',(await client.get('/')).text)
                    response=await client.get('/download')
                    self.assertEqual(response.status_code,200);self.assertEqual(response.content,data)
                    self.assertIn('attachment',response.headers['content-disposition'])
            upstream.assert_not_awaited()
    def test_corrupt_archive_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'client.part01').write_bytes(b'corrupt')
            (root/'client-manifest.json').write_text(json.dumps({'parts':['client.part01'],'sha256':'0'*64}))
            with self.assertRaises(ValueError):assemble(root)
            self.assertFalse((root/'downloads/StudyPilotC.zip').exists())
    def test_download_url_must_be_https_and_escaped(self):
        self.assertNotIn('href="javascript:',home_html('javascript:alert(1)'))
        self.assertIn('&quot;',home_html('https://example.com/file?x="test"'))
