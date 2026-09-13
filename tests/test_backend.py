import asyncio
from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.seed import seed_database
from app.security import hash_password, verify_password, create_access_token, decode_access_token

async def test_backend():
    print("\n--- 1. Testing Bcrypt Password Hashing ---")
    plain = "password123"
    hashed = hash_password(plain)
    print(f"Plain: {plain}")
    print(f"Bcrypt Hash: {hashed}")
    assert hashed != plain, "Password was not hashed!"
    assert verify_password("password123", hashed), "Password verification failed!"
    assert not verify_password("wrongpassword", hashed), "Wrong password verified!"
    print("[OK] Bcrypt hashing and salt verification PASSED!")

    print("\n--- 2. Testing JWT Tokens ---")
    token = create_access_token({"sub": "admin", "role": "admin"})
    print(f"Generated JWT: {token[:25]}... (truncated)")
    payload = decode_access_token(token)
    assert payload is not None, "Failed to decode JWT!"
    assert payload["sub"] == "admin" and payload["role"] == "admin", "JWT payload mismatch!"
    print("[OK] JWT creation and verification PASSED!")

    print("\n--- 3. Testing MongoDB Connection & Seeding ---")
    await connect_to_mongo()
    await seed_database()
    db = get_database()

    # Check admin user
    admin = await db.users.find_one({"username": "admin"})
    assert admin is not None, "Admin user not found in MongoDB!"
    assert verify_password("cfsiadmin", admin["password_hash"]), "Admin password verification failed!"
    print(f"[OK] Admin user found: {admin['username']}, Role: {admin['role']}, Hash: {admin['password_hash'][:15]}...")

    # Check student accounts
    cadet = await db.users.find_one({"username": "rahul"})
    assert cadet is not None, "Student rahul not found in MongoDB!"
    assert verify_password("password123", cadet["password_hash"]), "Cadet password verification failed!"
    print(f"[OK] Cadet found: {cadet['username']}, Certificate: {cadet['certificate_number']}")

    # Check 3-slot muster records
    muster_count = await db.attendance.count_documents({})
    assert muster_count > 0, "No attendance records found!"
    slots = await db.attendance.find({"certificate_number": "CFSI-2023-0101"}).to_list(10)
    print(f"[OK] Found {muster_count} attendance records. Rahul has {len(slots)} slots recorded.")

    # Check students verification
    student = await db.students.find_one({"certificate_number": "CFSI-2023-0101"})
    assert student is not None, "Student verification record not found!"
    print(f"[OK] Student record verified: {student['name']} ({student['course']})")

    # Check results
    res_count = await db.results.count_documents({"certificate_number": "CFSI-2023-0101"})
    assert res_count > 0, "No results found for cadet!"
    print(f"[OK] Rahul has {res_count} examination subject results.")

    await close_mongo_connection()
    print("\n[SUCCESS] ALL BACKEND CHECKS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    asyncio.run(test_backend())
