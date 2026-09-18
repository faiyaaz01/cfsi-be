import asyncio
from datetime import datetime, timezone
from app.database import get_database
from app.security import hash_password

async def seed_database():
    """Initializes collections and seeds demo accounts with hashed passwords and data into MongoDB."""
    db = get_database()

    try:
        # 1. Seed Institutional Administrator Account (Password hashed with bcrypt)
        from app.config import settings
        if settings.BOOTSTRAP_ADMIN_PASSWORD and not await db.users.find_one({"role": "admin"}):
            await db.users.insert_one({
                "_id": "user-admin", "username": settings.BOOTSTRAP_ADMIN_USERNAME,
                "password_hash": hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
                "role": "admin", "full_name": "CFSI Administrator", "is_active": True,
                "token_version": 0,
            })

        if not await db.users.find_one({"role": "teacher"}):
            await db.users.insert_one({
                "_id": "user-teacher",
                "username": "teacher@cfsi.com",
                "password_hash": hash_password("Teacher@1"),
                "role": "teacher",
                "full_name": "Senior Safety Instructor",
                "is_active": True,
                "token_version": 0,
            })

        # 2. Clean up legacy student records and student users
        try:
            student_indexes = await db.students.index_information()
            if "certificate_number_1" in student_indexes:
                await db.students.drop_index("certificate_number_1")
        except Exception:
            pass

        try:
            user_indexes = await db.users.index_information()
            if "certificate_number_1" in user_indexes:
                await db.users.drop_index("certificate_number_1")
        except Exception:
            pass

        await db.students.delete_many({
            "$or": [
                {"certificate_number": {"$exists": True}},
                {"id": {"$regex": "^stud-"}}
            ]
        })
        await db.users.delete_many({
            "role": "student",
            "$or": [
                {"username": {"$regex": "^(CFSI-202|user-student-rahul)"}},
                {"certificate_number": {"$exists": True}}
            ]
        })

        # 3. Clean up and remove any old legacy demo mock students from MongoDB by mock name only
        demo_student_names = [
            "Aarav N. Sharma", "Diya K. Patel", "Rohan S. Mehta", "Ananya R. Desai",
            "Virendra M. Solanki", "Sneha P. Joshi", "Karan B. Rathod", "Pooja N. Dave",
            "Pooja B. Joshi", "Harshit V. Parmar", "Neha T. Chauhan"
        ]
        await db.students.delete_many({
            "name": {"$in": demo_student_names}
        })
        await db.users.delete_many({
            "role": "student",
            "full_name": {"$in": demo_student_names}
        })
        # Clear any demo unsplash photo URLs from students and user accounts
        await db.students.update_many(
            {"photo_url": {"$regex": "unsplash"}},
            {"$set": {"photo_url": None}}
        )
        await db.users.update_many(
            {"photo_url": {"$regex": "unsplash"}},
            {"$set": {"photo_url": None}}
        )
        await db.system_meta.update_one(
            {"_id": "initial_seed_done"},
            {"$set": {"initialized": True, "demo_students_removed": True}},
            upsert=True
        )

        # 3. Clean up any legacy demo attendance records
        await db.attendance.delete_many({
            "$or": [
                {"id": {"$regex": "^att-seed-"}},
                {"id": {"$regex": "^att-today-"}}
            ]
        })
        # Clean up any legacy results collection if present
        await db.results.drop()

        # 4. Clean up any legacy demo news posts
        await db.news_posts.delete_many({
            "id": {"$in": ["news-01", "news-02", "news-03", "news-04"]}
        })

        # 5. Clean up any legacy demo web content (courses, drills, photos, videos)
        await db.web_courses.delete_many({
            "id": {"$in": ["cfs-01", "dfs-02", "pgdfs-03", "ffsi-04"]}
        })
        await db.web_drills.delete_many({
            "id": {"$in": ["tr-01", "tr-02", "tr-03"]}
        })
        await db.web_photos.delete_many({
            "id": {"$regex": "^img-(0|1)"}
        })
        await db.web_videos.delete_many({
            "id": {"$regex": "^vid-(0|1)"}
        })

        print("[MongoDB] CFSI collections initialized and demo data purged successfully.")
    except Exception as e:
        print(f"[MongoDB ERROR] Error seeding database: {e}")
        raise e

if __name__ == "__main__":
    from app.database import connect_to_mongo
    async def main():
        await connect_to_mongo()
        await seed_database()
    asyncio.run(main())
