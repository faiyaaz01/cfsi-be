"""Isolated authentication/authorization integration tests; no live database writes."""
import asyncio
import unittest
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from app.main import app
from app.database import get_database
from app.security import hash_password, create_access_token

class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient().auth_tests
        await self.db.users.create_index('username', unique=True)
        await self.db.users.insert_one({'_id':'admin-id','username':'administrator','password_hash':hash_password('GoodPassword123'),'role':'admin','full_name':'Admin','is_active':True})
        await self.db.students.insert_one({'id':'262701','roll_no':'01','name':'Test Student','father_name':'F','course':'Fire Safety','batch':'Batch 2026-2027','passing_year':'2027','grade':'A','percentage':'80%','verification_status':'Verified','issue_date':'1 Jan 2027','center_location':'Vadodara'})
        app.dependency_overrides[get_database] = lambda: self.db
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        self.admin = await self.login('administrator')

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()

    async def login(self, username):
        res = await self.client.post('/api/auth/token', data={'username':username,'password':'GoodPassword123'})
        self.assertEqual(res.status_code, 200, res.text)
        return {'Authorization':'Bearer '+res.json()['access_token']}

    async def create(self, role):
        res = await self.client.post('/api/users', headers=self.admin, json={'username':role+'user','password':'GoodPassword123','role':role,'full_name':role,'student_id':'262701' if role=='student' else None})
        self.assertEqual(res.status_code,201,res.text)
        self.assertNotIn('password_hash',res.json())
        return res.json()

    async def test_user_crud_and_role_access(self):
        for role in ['teacher','student']:
            user = await self.create(role)
            headers = await self.login(role+'user')
            self.assertEqual((await self.client.get('/api/users',headers=headers)).status_code,403)
            self.assertEqual((await self.client.post('/api/users',headers=headers,json={'username':'unauthorized','password':'GoodPassword123','role':'admin','full_name':'X'})).status_code,403)
            self.assertEqual((await self.client.get('/api/auth/me',headers=headers)).json()['role'],role)
            self.assertEqual((await self.client.get('/api/users/'+user['id'],headers=self.admin)).status_code,200)
            changed = await self.client.patch('/api/users/'+user['id'],headers=self.admin,json={'full_name':'Updated'})
            self.assertEqual(changed.status_code,200,changed.text)
            self.assertEqual((await self.client.get('/api/auth/me',headers=headers)).status_code,401)
            headers = await self.login(role+'user')
            self.assertEqual((await self.client.delete('/api/users/'+user['id'],headers=self.admin)).status_code,204)
            self.assertEqual((await self.client.get('/api/auth/me',headers=headers)).status_code,401)

    async def test_invalid_tokens_logout_and_self_protection(self):
        for path in ['/api/users','/api/students','/api/attendance']:
            self.assertEqual((await self.client.get(path)).status_code,401)
        expired = create_access_token({'sub':'administrator','user_id':'admin-id'},timedelta(seconds=-1))
        for token in ['invalid', expired]:
            self.assertEqual((await self.client.get('/api/auth/me',headers={'Authorization':'Bearer '+token})).status_code,401)
        self.assertEqual((await self.client.delete('/api/users/admin-id',headers=self.admin)).status_code,409)
        self.assertEqual((await self.client.patch('/api/users/admin-id',headers=self.admin,json={'role':'teacher'})).status_code,409)
        self.assertEqual((await self.client.post('/api/auth/logout',headers=self.admin)).status_code,204)
        self.assertEqual((await self.client.get('/api/auth/me',headers=self.admin)).status_code,401)

    async def test_teacher_write_student_isolation_and_validation(self):
        await self.create('teacher'); await self.create('student')
        teacher = await self.login('teacheruser'); student = await self.login('studentuser')
        record = {'studentId':'262702','rollNo':'02','date':'2026-09-13','slot':'Slot 1','course':'Fire Safety','status':'Present'}
        res = await self.client.post('/api/attendance',headers=teacher,json=record)
        self.assertEqual(res.status_code,201,res.text)
        self.assertEqual((await self.client.post('/api/attendance',headers=student,json=record)).status_code,403)
        self.assertEqual((await self.client.get('/api/attendance?student_id=262702',headers=student)).json(),[])
        self.assertEqual((await self.client.get('/api/students/262702',headers=student)).status_code,403)
        duplicate = await self.client.post('/api/users',headers=self.admin,json={'username':'teacheruser','password':'GoodPassword123','role':'teacher','full_name':'Teacher'})
        self.assertEqual(duplicate.status_code,409)
        self.assertEqual((await self.client.patch('/api/users/admin-id',headers=self.admin,json={'role':'superadmin'})).status_code,422)
        bad = await self.client.post('/api/auth/token',data={'username':'administrator','password':'wrong'})
        self.assertEqual(bad.status_code,401)
        user = (await self.client.get('/api/users',headers=self.admin)).json()
        student_id = next(u['id'] for u in user if u['role']=='student')
        await self.client.patch('/api/users/'+student_id,headers=self.admin,json={'is_active':False})
        self.assertEqual((await self.client.get('/api/auth/me',headers=student)).status_code,401)
        self.assertEqual((await self.client.get('/api/news')).status_code,200)

if __name__ == '__main__':
    unittest.main()
