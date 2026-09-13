import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.seed import seed_database
from app.security import hash_password, verify_password, create_access_token, decode_access_token

async def test_backend():
    print("\n--- 1. Testing Bcrypt Password Hashing ---")
    plain = "Password@1"
    hashed = hash_password(plain)
    print(f"Plain: {plain}")
    print(f"Bcrypt Hash: {hashed}")
    assert hashed != plain, "Password was not hashed!"
    assert verify_password("Password@1", hashed), "Password verification failed!"
    assert not verify_password("wrongpassword", hashed), "Wrong password verified!"
    print("[OK] Bcrypt hashing and salt verification PASSED!")

    print("\n--- 2. Testing JWT Tokens ---")
    token = create_access_token({"sub": "admin@cfsi.com", "role": "admin"})
    print(f"Generated JWT: {token[:25]}... (truncated)")
    payload = decode_access_token(token)
    assert payload is not None, "Failed to decode JWT!"
    assert payload["sub"] == "admin@cfsi.com" and payload["role"] == "admin", "JWT payload mismatch!"
    print("[OK] JWT creation and verification PASSED!")

    print("\n--- 3. Testing MongoDB Connection & Seeding ---")
    await connect_to_mongo()
    await seed_database()
    db = get_database()

    # Check institutional admin user
    admin = await db.users.find_one({"username": "admin@cfsi.com"})
    assert admin is not None, "Admin user 'admin@cfsi.com' not found in MongoDB!"
    assert verify_password("Password@1", admin["password_hash"]), "Admin password verification failed!"
    print(f"[OK] Admin user found: {admin['username']}, Role: {admin['role']}, Hash: {admin['password_hash'][:15]}...")

    # Check that legacy demo mock accounts and demo seeds are purged
    demo_count = await db.attendance.count_documents({"id": {"$regex": "^att-seed-"}})
    assert demo_count == 0, f"Expected 0 demo attendance seeds, found {demo_count}"
    print(f"[OK] Clean attendance registry: 0 mock demo seeds present.")

    # Check students verification registry
    student = await db.students.find_one({"certificate_number": "CFSI-2023-0101"})
    assert student is not None, "Student verification record not found!"
    print(f"[OK] Student record verified: {student['name']} ({student['course']})")

    # Test dynamic record creation and query
    test_att_id = "att-test-verification"
    await db.attendance.delete_many({"id": test_att_id})
    await db.attendance.insert_one({
        "id": test_att_id,
        "certificate_number": "CFSI-2023-0101",
        "date": "2026-09-13",
        "slot": "Slot 1",
        "course": "Diploma In Fire Safety",
        "status": "Present",
        "topic_or_module": "Test Operational Drill",
        "marked_by": "Chief Instructor Dave"
    })
    saved_att = await db.attendance.find_one({"id": test_att_id})
    assert saved_att is not None and saved_att["status"] == "Present"
    print(f"[OK] Dynamic drill muster record successfully created and verified in MongoDB.")
    await db.attendance.delete_one({"id": test_att_id})

    # Test dynamic exam score creation and query
    test_res_id = "res-test-verification"
    await db.results.delete_many({"id": test_res_id})
    await db.results.insert_one({
        "id": test_res_id,
        "certificate_number": "CFSI-2023-0101",
        "course": "Diploma In Fire Safety",
        "subject": "Fire Prevention & Codes",
        "marks_obtained": 88,
        "max_marks": 100,
        "grade": "Distinction (A+)"
    })
    saved_res = await db.results.find_one({"id": test_res_id})
    assert saved_res is not None and saved_res["marks_obtained"] == 88
    print(f"[OK] Dynamic examination score successfully created and verified in MongoDB.")
    await db.results.delete_one({"id": test_res_id})

    await close_mongo_connection()
    print("\n[SUCCESS] ALL BACKEND CHECKS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    asyncio.run(test_backend())
