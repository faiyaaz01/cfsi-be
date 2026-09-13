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

        # 3. Clean up and remove any demo students and demo student login accounts from MongoDB
        demo_student_ids = [
            "262701", "262702", "262703", "262704", "262705", "262706", "262707", "262708"
        ]
        demo_student_names = [
            "Aarav N. Sharma", "Diya K. Patel", "Rohan S. Mehta", "Ananya R. Desai",
            "Virendra M. Solanki", "Sneha P. Joshi", "Karan B. Rathod", "Pooja N. Dave",
            "Pooja B. Joshi", "Harshit V. Parmar", "Neha T. Chauhan"
        ]
        await db.students.delete_many({
            "$or": [
                {"id": {"$in": demo_student_ids}},
                {"roll_no": {"$in": ["01", "02", "03", "04", "05", "06", "07", "08"]}},
                {"name": {"$in": demo_student_names}}
            ]
        })
        await db.users.delete_many({
            "role": "student",
            "$or": [
                {"username": {"$in": demo_student_ids}},
                {"student_id": {"$in": demo_student_ids}},
                {"full_name": {"$in": demo_student_names}}
            ]
        })
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

        # 4. Seed News Posts
        news_seed = [
            {
                "_id": "news-01",
                "id": "news-01",
                "title": "Admissions Open for Academic Year 2024-25 — Diploma & Certificate Batches",
                "category": "Announcement",
                "date": "2024-08-20",
                "excerpt": "Applications are now invited for Government-recognized Diploma in Fire Safety (1 Year) and Sub Fire Officer programs. Limited seats available per batch.",
                "content": "Central Fire Safety Institute (CFSI), Vadodara announces the commencement of admissions for the upcoming session. Candidates who have passed 10th/12th or ITI are eligible to enroll for Certificate and Diploma programs. Practical training includes high-altitude rappelling, smoke chamber search and rescue, and industrial chemical fire drills. Scholarship concessions are available for merit students and children of defense/police personnel.",
                "image_url": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1000&q=80",
                "author": "Admissions Directorate",
                "is_pinned": True
            },
            {
                "_id": "news-02",
                "id": "news-02",
                "title": "CFSI Conducts Mega Live Fire & Search Rescue Drill in Collaboration with GIDC Vadodara",
                "category": "Event",
                "date": "2024-08-12",
                "excerpt": "Over 120 cadets successfully executed complex live hydrocarbon fire suppression and mass casualty evacuation in a simulated plant blackout drill.",
                "content": "A joint industrial disaster response drill was coordinated between CFSI senior instructors and Vadodara Industrial Safety authorities. Cadets operated high-capacity foam branches, mobile water monitors, and hydraulic rescue cutters to simulate real refinery emergencies. State safety inspectors praised the agility and discipline of CFSI student rescue squads.",
                "image_url": "https://images.unsplash.com/photo-1517524008697-84bbe3c3fd98?auto=format&fit=crop&w=1000&q=80",
                "author": "Chief Training Officer",
                "is_pinned": False
            },
            {
                "_id": "news-03",
                "id": "news-03",
                "title": "CFSI Awarded Best Fire Safety Vocational Training Institute in Western India by IFSMA",
                "category": "News",
                "date": "2024-07-28",
                "excerpt": "Recognized for 100% practical ground drill curriculum, modern breathing apparatus training facility, and stellar placement records across petrochemical hubs.",
                "content": "The International Fire & Safety Management Association (IFSMA) presented the prestigious Western Regional Excellence Award to Central Fire Safety Institute Vadodara during the 15th National Fire Congress in New Delhi. The honor celebrates our continuous commitment to zero-fatality industrial safety education and ground drill standards.",
                "image_url": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1000&q=80",
                "author": "Institute Directorate",
                "is_pinned": False
            },
            {
                "_id": "news-04",
                "id": "news-04",
                "title": "Upcoming National Fire Safety Week — Free Public Awareness & Fire Extinguisher Clinic",
                "category": "Event",
                "date": "2024-09-05",
                "excerpt": "Join us at CFSI Vadodara campus for interactive safety workshops, home LPG gas safety demonstrations, and hands-on extinguisher training.",
                "content": "As part of our civic outreach initiative, CFSI faculty and senior trainees will host a 2-day open workshop for school teachers, factory supervisors, and housing society managers. Participants will learn PASS fire extinguisher usage, emergency CPR, and primary burn triage with free participation certificates.",
                "image_url": "https://images.unsplash.com/photo-1577495508048-b635879837f1?auto=format&fit=crop&w=1000&q=80",
                "author": "Community Outreach Cell",
                "is_pinned": False
            }
        ]

        for n in news_seed:
            existing = await db.news_posts.find_one({"_id": n["_id"]})
            if not existing:
                await db.news_posts.insert_one(n)

        print("[MongoDB] CFSI collections initialized and demo data seeded successfully.")
    except Exception as e:
        print(f"[MongoDB ERROR] Error seeding database: {e}")
        raise e

if __name__ == "__main__":
    from app.database import connect_to_mongo
    async def main():
        await connect_to_mongo()
        await seed_database()
    asyncio.run(main())
