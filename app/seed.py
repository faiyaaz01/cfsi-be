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

        # 3. Seed Batch 2026-2027 Students (Student IDs formatted as 2627<rollno>)
        students_data = [
            {
                "_id": "262701",
                "id": "262701",
                "roll_no": "01",
                "name": "Aarav N. Sharma",
                "father_name": "Naresh Sharma",
                "mother_name": "Sunita Sharma",
                "birth_date": "2004-05-14",
                "course": "Diploma In Fire Safety",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "Distinction (A+)",
                "percentage": "89.5%",
                "verification_status": "Verified",
                "issue_date": "15 June 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80",
                "present_address": "B-402, Shivalik Heights, Waghodia Road, Vadodara, Gujarat - 390019",
                "student_phone": "+91 98765 43210",
                "father_phone": "+91 98765 11111",
                "mother_phone": "+91 98765 22222",
                "category": "General",
                "aadhar_card": "4532 8901 2345",
                "email": "aarav.sharma@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            },
            {
                "_id": "262702",
                "id": "262702",
                "roll_no": "02",
                "name": "Diya K. Patel",
                "father_name": "Kiritkumar Patel",
                "mother_name": "Bhavanaben Patel",
                "birth_date": "2004-09-22",
                "course": "Sub Fire Officer",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "First Class (A)",
                "percentage": "84.0%",
                "verification_status": "Verified",
                "issue_date": "28 July 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=200&q=80",
                "present_address": "12, Gokul Residency, Alkapuri, Vadodara, Gujarat - 390007",
                "student_phone": "+91 98234 56789",
                "father_phone": "+91 98234 11111",
                "mother_phone": "+91 98234 22222",
                "category": "OBC",
                "aadhar_card": "7890 1234 5678",
                "email": "diya.patel@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            },
            {
                "_id": "262703",
                "id": "262703",
                "roll_no": "03",
                "name": "Rohan S. Mehta",
                "father_name": "Suresh Mehta",
                "mother_name": "Geeta Mehta",
                "birth_date": "2003-12-05",
                "course": "Certificate In Fire Safety",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "Distinction (A+)",
                "percentage": "92.0%",
                "verification_status": "Verified",
                "issue_date": "10 January 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=200&q=80",
                "present_address": "Flat 301, Pushpak Complex, Manjalpur, Vadodara - 390011",
                "student_phone": "+91 97123 45678",
                "father_phone": "+91 97123 11111",
                "mother_phone": "+91 97123 22222",
                "category": "General",
                "aadhar_card": "2345 6789 0123",
                "email": "rohan.mehta@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            },
            {
                "_id": "262704",
                "id": "262704",
                "roll_no": "04",
                "name": "Ananya R. Desai",
                "father_name": "Rajesh Desai",
                "mother_name": "Meenaben Desai",
                "birth_date": "2005-03-18",
                "course": "Industrial Safety",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "First Class (A)",
                "percentage": "81.5%",
                "verification_status": "Verified",
                "issue_date": "14 April 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=200&q=80",
                "present_address": "45, Vasant Vihar, Gotri Road, Vadodara - 390021",
                "student_phone": "+91 98456 78901",
                "father_phone": "+91 98456 11111",
                "mother_phone": "+91 98456 22222",
                "category": "General",
                "aadhar_card": "3456 7890 1234",
                "email": "ananya.desai@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            },
            {
                "_id": "262705",
                "id": "262705",
                "roll_no": "05",
                "name": "Virendra M. Solanki",
                "father_name": "Maheshbhai Solanki",
                "mother_name": "Hansaben Solanki",
                "birth_date": "2004-01-30",
                "course": "Diploma In Fire Safety",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "Distinction (A+)",
                "percentage": "87.2%",
                "verification_status": "Verified",
                "issue_date": "20 June 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80",
                "present_address": "Block C-104, Sardar Nagar Society, Karelibaug, Vadodara - 390018",
                "student_phone": "+91 98980 12345",
                "father_phone": "+91 98980 11111",
                "mother_phone": "+91 98980 22222",
                "category": "SC",
                "aadhar_card": "5678 9012 3456",
                "email": "virendra.solanki@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            },
            {
                "_id": "262706",
                "id": "262706",
                "roll_no": "06",
                "name": "Sneha P. Joshi",
                "father_name": "Pradeep Joshi",
                "mother_name": "Kalpanaben Joshi",
                "birth_date": "2004-11-12",
                "course": "Sub Fire Officer",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "First Class (A)",
                "percentage": "83.8%",
                "verification_status": "Verified",
                "issue_date": "18 July 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=200&q=80",
                "present_address": "8, Nilkanth Bunglows, Sayajigunj, Vadodara - 390005",
                "student_phone": "+91 99123 45678",
                "father_phone": "+91 99123 11111",
                "mother_phone": "+91 99123 22222",
                "category": "General",
                "aadhar_card": "6789 0123 4567",
                "email": "sneha.joshi@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            },
            {
                "_id": "262707",
                "id": "262707",
                "roll_no": "07",
                "name": "Karan B. Rathod",
                "father_name": "Bhaveshbhai Rathod",
                "mother_name": "Urmilaben Rathod",
                "birth_date": "2003-08-25",
                "course": "Certificate In Fire Safety",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "First Class (B+)",
                "percentage": "78.5%",
                "verification_status": "Verified",
                "issue_date": "30 July 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80",
                "present_address": "Plot 77, Maruti Green, Makarpura, Vadodara - 390014",
                "student_phone": "+91 97234 56780",
                "father_phone": "+91 97234 11111",
                "mother_phone": "+91 97234 22222",
                "category": "ST",
                "aadhar_card": "7890 3456 1234",
                "email": "karan.rathod@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            },
            {
                "_id": "262708",
                "id": "262708",
                "roll_no": "08",
                "name": "Pooja N. Dave",
                "father_name": "Nileshbhai Dave",
                "mother_name": "Rekhaben Dave",
                "birth_date": "2004-07-08",
                "course": "Industrial Safety",
                "batch": "Batch 2026-2027",
                "passing_year": "2027",
                "grade": "Distinction (A+)",
                "percentage": "90.4%",
                "verification_status": "Verified",
                "issue_date": "25 June 2027",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80",
                "present_address": "A-12, Radhika Township, New VIP Road, Vadodara - 390022",
                "student_phone": "+91 98790 12345",
                "father_phone": "+91 98790 11111",
                "mother_phone": "+91 98790 22222",
                "category": "EWS",
                "aadhar_card": "8901 2345 6789",
                "email": "pooja.dave@gmail.com",
                "nationality": "Indian",
                "state": "Gujarat"
            }
        ]

        student_pwd_hash = hash_password("Student@1")
        for s in students_data:
            # Upsert into students collection
            await db.students.update_one(
                {"id": s["id"]},
                {"$set": s},
                upsert=True
            )
            # Upsert student login account with Student ID as username (e.g. 262701)
            await db.users.update_one(
                {"username": s["id"]},
                {
                    "$set": {
                        "username": s["id"],
                        "student_id": s["id"],
                        "role": "student",
                        "full_name": s["name"],
                        "photo_url": s["photo_url"],
                        "is_active": True,
                        "token_version": 0,
                    },
                    "$setOnInsert": {
                        "_id": f"user-student-{s['id']}",
                        "password_hash": student_pwd_hash
                    }
                },
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
