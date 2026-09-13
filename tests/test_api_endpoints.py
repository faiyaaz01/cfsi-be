import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test_api():
    with TestClient(app) as client:
        print("\n--- 1. Testing Root & Health ---")
        res = client.get("/")
        assert res.status_code == 200
        print(f"[OK] Root: {res.json()['institute']}, Database: {res.json()['database']}")

        print("\n--- 2. Testing Unauthenticated Cadet Record Access Denial ---")
        # Cadet registry must require login!
        res = client.get("/api/students/262701")
        assert res.status_code == 401, f"Expected 401 Unauthorized for unauthenticated request, got {res.status_code}"
        print("[OK] Unauthenticated cadet request properly rejected with 401 Unauthorized!")

        print("\n--- 3. Testing Admin & Student Login (Student ID 262701) ---")
        login_res = client.post("/api/auth/login", json={"username": "admin@cfsi.com", "password": "Password@1"})
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        admin_data = login_res.json()
        admin_token = admin_data["access_token"]
        assert admin_data["role"] == "admin"
        print(f"[OK] Admin logged in successfully as {admin_data['user']['username']}! Role: {admin_data['role']}")

        # Student login using Student ID format 2627<rollno> (262701)
        student_login = client.post("/api/auth/login", json={"username": "262701", "password": "Student@1"})
        assert student_login.status_code == 200, f"Student login failed: {student_login.text}"
        student_data = student_login.json()
        assert student_data["role"] == "student"
        assert student_data["user"]["student_id"] == "262701"
        print(f"[OK] Student logged in successfully with Student ID '{student_data['user']['username']}'! Name: {student_data['user']['full_name']}")

        headers_admin = {"Authorization": f"Bearer {admin_token}"}

        print("\n--- 4. Testing Cadet Record Retrieval (After Login) ---")
        cadet_res = client.get("/api/students/262701", headers=headers_admin)
        assert cadet_res.status_code == 200
        cadet_json = cadet_res.json()
        assert cadet_json["name"] == "Aarav N. Sharma"
        assert cadet_json["batch"] == "Batch 2026-2027"
        assert cadet_json["id"] == "262701"
        print(f"[OK] Retrieved Cadet: {cadet_json['name']}, Batch: {cadet_json['batch']}, ID: {cadet_json['id']}")

        print("\n--- 5. Testing 3-Slot Daily Muster Attendance Bulk Save ---")
        muster_records = [
            {
                "studentId": "262701",
                "rollNo": "01",
                "date": "2026-09-13",
                "slot": "Slot 1",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topicOrModule": "Smoke Diving & BA Mask Drill",
                "remarks": "Punctual, fully geared"
            },
            {
                "studentId": "262701",
                "rollNo": "01",
                "date": "2026-09-13",
                "slot": "Slot 2",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topicOrModule": "Foam Branch Ratio Calculations",
                "remarks": "Passed practical quiz"
            },
            {
                "studentId": "262701",
                "rollNo": "01",
                "date": "2026-09-13",
                "slot": "Slot 3",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topicOrModule": "Tower Repelling Drill",
                "remarks": "Clean descent"
            }
        ]
        bulk_res = client.post("/api/attendance/bulk", json={"records": muster_records}, headers=headers_admin)
        assert bulk_res.status_code == 200, f"Bulk muster save failed: {bulk_res.text}"
        saved_muster = bulk_res.json()
        assert len(saved_muster) == 3
        assert "studentId" in saved_muster[0]
        assert saved_muster[0]["studentId"] == "262701"
        print(f"[OK] Successfully saved {len(saved_muster)} muster slots in MongoDB with studentId: {saved_muster[0]['studentId']}")

        print("\n--- 6. Testing Attendance Query & Single Upsert ---")
        get_res = client.get("/api/attendance?date=2026-09-13", headers=headers_admin)
        assert get_res.status_code == 200
        records = get_res.json()
        assert len(records) >= 3

        # Single record update
        single_res = client.post("/api/attendance", json={
            "studentId": "262701",
            "rollNo": "01",
            "date": "2026-09-14",
            "slot": "Slot 1",
            "course": "Diploma In Fire Safety",
            "status": "Absent",
            "remarks": "Medical leave"
        }, headers=headers_admin)
        assert single_res.status_code == 201
        created_single = single_res.json()
        assert created_single["status"] == "Absent"
        assert created_single["studentId"] == "262701"
        print(f"[OK] Single attendance upsert verified: {created_single['id']}")

        print("\n--- 7. Testing Attendance Deletion & Purge Endpoints ---")
        # Delete single record
        del_res = client.delete(f"/api/attendance/{created_single['id']}", headers=headers_admin)
        assert del_res.status_code == 204
        print(f"[OK] Attendance record {created_single['id']} deleted.")

        # Clear day attendance
        day_del_res = client.delete("/api/attendance/day/2026-09-13", headers=headers_admin)
        assert day_del_res.status_code == 200
        assert day_del_res.json()["deleted"] >= 3
        print(f"[OK] Cleared day attendance for 2026-09-13.")

        # Clear all attendance
        all_del_res = client.delete("/api/attendance", headers=headers_admin)
        assert all_del_res.status_code == 200
        print(f"[OK] Cleared all attendance records in MongoDB.")

        print("\n--- 8. Testing 48-Hour Lock Window Policy ---")
        from datetime import datetime, timezone, timedelta
        past_49h = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
        
        # Create record backdated to 49 hours ago (uploaded 49h ago)
        locked_post = client.post("/api/attendance", json={
            "studentId": "262701",
            "rollNo": "01",
            "date": "2026-09-10",
            "slot": "Slot 1",
            "course": "Diploma In Fire Safety",
            "status": "Present",
            "uploadedAt": past_49h
        }, headers=headers_admin)
        assert locked_post.status_code == 201
        locked_rec = locked_post.json()
        assert locked_rec["isLocked"] is True, f"Expected isLocked=True, got {locked_rec['isLocked']}"
        print(f"[OK] Record backdated 49h is flagged isLocked=True (uploaded: {locked_rec['uploadedAt']})")

        # Attempt to modify locked record via PUT -> Must return 403
        edit_res = client.put(f"/api/attendance/{locked_rec['id']}", json={"status": "Absent"}, headers=headers_admin)
        assert edit_res.status_code == 403, f"Expected 403 for locked edit, got {edit_res.status_code}: {edit_res.text}"
        print("[OK] PUT edit on 48h-expired record correctly rejected with 403 Forbidden!")

        # Attempt to delete locked record -> Must return 403
        del_locked = client.delete(f"/api/attendance/{locked_rec['id']}", headers=headers_admin)
        assert del_locked.status_code == 403, f"Expected 403 for locked delete, got {del_locked.status_code}"
        print("[OK] DELETE on 48h-expired record correctly rejected with 403 Forbidden!")

        # Attempt to upsert same locked slot via POST -> Must return 403
        upsert_locked = client.post("/api/attendance", json={
            "studentId": "262701",
            "date": "2026-09-10",
            "slot": "Slot 1",
            "course": "Diploma In Fire Safety",
            "status": "Absent"
        }, headers=headers_admin)
        assert upsert_locked.status_code == 403, f"Expected 403 for locked upsert, got {upsert_locked.status_code}"
        print("[OK] POST upsert on 48h-expired slot correctly rejected with 403 Forbidden!")

        # Clean up test database
        client.delete("/api/attendance", headers=headers_admin)

        print("\n--- 9. Testing Real-Time Broadcaster & Stream Endpoint ---")
        from app.routers.attendance import broadcaster
        import asyncio
        async def check_broadcaster():
            q = await broadcaster.subscribe()
            await broadcaster.broadcast({"event": "attendance_updated", "test": True})
            msg = await asyncio.wait_for(q.get(), timeout=1.0)
            assert msg["event"] == "attendance_updated"
            broadcaster.unsubscribe(q)
        asyncio.run(check_broadcaster())
        print("[OK] Real-time Broadcaster pub/sub event verified!")

        print("\n[SUCCESS] ALL REST API ENDPOINTS & 48H LOCKING TESTED SUCCESSFULLY!\n")

if __name__ == "__main__":
    test_api()
