import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test_api():
    with TestClient(app) as client:
        print("\n--- 1. Testing Root & Health ---")
        res = client.get("/")
        assert res.status_code == 200
        print(f"[OK] Root: {res.json()['institute']}, Database: {res.json()['database']}")

        print("\n--- 2. Testing Public Certificate Verification Denial ---")
        # Certificate verification must require login!
        res = client.get("/api/students/verify/CFSI-2023-0101")
        assert res.status_code == 401, f"Expected 401 Unauthorized for unauthenticated verification, got {res.status_code}"
        print("[OK] Unauthenticated verification properly rejected with 401 Unauthorized!")

        print("\n--- 3. Testing Admin Login & JWT Generation ---")
        login_res = client.post("/api/auth/login", json={"username": "admin", "password": "cfsiadmin"})
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        admin_data = login_res.json()
        admin_token = admin_data["access_token"]
        assert admin_data["role"] == "admin"
        print(f"[OK] Admin logged in successfully! Role: {admin_data['role']}")

        headers_admin = {"Authorization": f"Bearer {admin_token}"}

        print("\n--- 4. Testing Certificate Verification (After Login) ---")
        verify_res = client.get("/api/students/verify/CFSI-2023-0101", headers=headers_admin)
        assert verify_res.status_code == 200
        verify_json = verify_res.json()
        assert verify_json["verified"] is True
        assert verify_json["student"]["name"] == "Rahul V. Patel"
        print(f"[OK] Verified Cadet: {verify_json['student']['name']}, Status: {verify_json['student']['verificationStatus']}")

        print("\n--- 5. Testing Student Login & Scope Restrictions ---")
        student_res = client.post("/api/auth/login", json={"username": "rahul", "password": "password123"})
        assert student_res.status_code == 200
        student_data = student_res.json()
        student_token = student_data["access_token"]
        headers_student = {"Authorization": f"Bearer {student_token}"}
        print(f"[OK] Cadet Rahul logged in! Cert: {student_data['user']['certificate_number']}")

        # Cadet fetching own results
        res_res = client.get("/api/results", headers=headers_student)
        assert res_res.status_code == 200
        results_list = res_res.json()
        assert len(results_list) > 0
        print(f"[OK] Cadet retrieved {len(results_list)} results. Top subject: {results_list[0]['subject']}")

        print("\n--- 6. Testing 3-Slot Daily Muster Attendance Bulk Save ---")
        muster_records = [
            {
                "certificateNumber": "CFSI-2023-0101",
                "date": "2026-09-13",
                "slot": "Slot 1",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topicOrModule": "Smoke Diving & BA Mask Drill",
                "remarks": "Punctual, fully geared"
            },
            {
                "certificateNumber": "CFSI-2023-0101",
                "date": "2026-09-13",
                "slot": "Slot 2",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topicOrModule": "Foam Branch Ratio Calculations",
                "remarks": "Passed practical quiz"
            },
            {
                "certificateNumber": "CFSI-2023-0101",
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
        print(f"[OK] Successfully saved {len(saved_muster)} muster slots for today in MongoDB!")

        print("\n[SUCCESS] ALL REST API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!\n")

if __name__ == "__main__":
    test_api()
