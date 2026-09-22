"""Unit and integration tests for private self-hosted image uploads."""
import io
from pathlib import Path
import unittest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from app.main import app
from app.database import get_database
from app.security import hash_password

class ImageUploadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient().upload_tests
        await self.db.users.create_index('username', unique=True)
        await self.db.users.insert_one({
            '_id': 'admin-test-id',
            'username': 'adminuser',
            'password_hash': hash_password('TestPassword123'),
            'role': 'admin',
            'full_name': 'Admin User',
            'is_active': True
        })
        await self.db.users.insert_one({
            '_id': 'student-test-id',
            'username': 'studentuser',
            'password_hash': hash_password('TestPassword123'),
            'role': 'student',
            'full_name': 'Student User',
            'is_active': True
        })
        app.dependency_overrides[get_database] = lambda: self.db
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        
        # Login admin
        admin_res = await self.client.post('/api/auth/token', data={'username': 'adminuser', 'password': 'TestPassword123'})
        self.admin_headers = {'Authorization': 'Bearer ' + admin_res.json()['access_token']}
        
        # Login student
        student_res = await self.client.post('/api/auth/token', data={'username': 'studentuser', 'password': 'TestPassword123'})
        self.student_headers = {'Authorization': 'Bearer ' + student_res.json()['access_token']}

        self.uploaded_files_to_cleanup = []

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
        for filename in self.uploaded_files_to_cleanup:
            p = uploads_dir / filename
            if p.exists():
                p.unlink(missing_ok=True)

    async def test_upload_requires_authentication(self):
        files = {'file': ('test.jpg', b'\xFF\xD8\xFF\xE0\x00\x10JFIF', 'image/jpeg')}
        res = await self.client.post('/api/web/upload-image', files=files)
        self.assertEqual(res.status_code, 401)

    async def test_upload_requires_admin_role(self):
        files = {'file': ('test.jpg', b'\xFF\xD8\xFF\xE0\x00\x10JFIF', 'image/jpeg')}
        res = await self.client.post('/api/web/upload-image', headers=self.student_headers, files=files)
        self.assertEqual(res.status_code, 403)

    async def test_successful_image_upload_and_static_serve(self):
        image_content = b'\xFF\xD8\xFF\xE0\x00\x10JFIF_SAMPLE_IMAGE_DATA'
        files = {'file': ('sample.jpg', image_content, 'image/jpeg')}
        res = await self.client.post('/api/web/upload-image', headers=self.admin_headers, files=files)
        self.assertEqual(res.status_code, 201, res.text)
        
        data = res.json()
        self.assertIn('url', data)
        self.assertIn('filename', data)
        self.assertTrue(data['url'].startswith('/api/uploads/'))
        self.assertTrue(data['filename'].endswith('.jpg'))
        
        self.uploaded_files_to_cleanup.append(data['filename'])

        # Verify file exists on local disk in uploads/
        uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
        saved_file = uploads_dir / data['filename']
        self.assertTrue(saved_file.exists())
        self.assertEqual(saved_file.read_bytes(), image_content)

        # Verify StaticFiles serving via /api/uploads
        get_res = await self.client.get(data['url'])
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.content, image_content)

    async def test_reject_invalid_file_extension(self):
        files = {'file': ('virus.exe', b'bad_binary_content', 'application/octet-stream')}
        res = await self.client.post('/api/web/upload-image', headers=self.admin_headers, files=files)
        self.assertEqual(res.status_code, 400)
        self.assertIn('Allowed formats', res.json()['detail'])

    async def test_reject_empty_file(self):
        files = {'file': ('empty.png', b'', 'image/png')}
        res = await self.client.post('/api/web/upload-image', headers=self.admin_headers, files=files)
        self.assertEqual(res.status_code, 400)
