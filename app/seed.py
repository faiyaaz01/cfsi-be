import asyncio
from datetime import datetime, timezone
from app.database import get_database
from app.security import hash_password

async def seed_database():
    """Initializes collections and seeds demo accounts with hashed passwords and data into MongoDB."""
    db = get_database()

    try:
        # 1. Seed Users (passwords hashed with bcrypt)
        existing_admin = await db.users.find_one({"username": "admin"})
        if not existing_admin:
            admin_user = {
                "_id": "user-admin",
                "id": "user-admin",
                "username": "admin",
                "password_hash": hash_password("cfsiadmin"),
                "role": "admin",
                "full_name": "CFSI Chief Administrator",
                "certificate_number": None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(admin_user)

        demo_cadets = [
            {
                "username": "rahul",
                "password": "password123",
                "role": "student",
                "certificate_number": "CFSI-2023-0101",
                "full_name": "Rahul V. Patel"
            },
            {
                "username": "amitabh",
                "password": "password123",
                "role": "student",
                "certificate_number": "CFSI-2023-0102",
                "full_name": "Amitabh S. Sharma"
            },
            {
                "username": "priyanka",
                "password": "password123",
                "role": "student",
                "certificate_number": "CFSI-2023-0103",
                "full_name": "Priyanka D. Parmar"
            },
            {
                "username": "hardik",
                "password": "password123",
                "role": "student",
                "certificate_number": "CFSI-2024-0201",
                "full_name": "Hardik K. Solanki"
            },
            {
                "username": "manish",
                "password": "password123",
                "role": "student",
                "certificate_number": "CFSI-2024-0202",
                "full_name": "Manish R. Yadav"
            }
        ]

        for cadet in demo_cadets:
            existing = await db.users.find_one({"username": cadet["username"]})
            if not existing:
                u = {
                    "_id": f"user-{cadet['username']}",
                    "id": f"user-{cadet['username']}",
                    "username": cadet["username"],
                    "password_hash": hash_password(cadet["password"]),
                    "role": cadet["role"],
                    "certificate_number": cadet["certificate_number"],
                    "full_name": cadet["full_name"],
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.users.insert_one(u)

        # 2. Seed Students
        students_data = [
            {
                "_id": "stud-01",
                "id": "stud-01",
                "certificate_number": "CFSI-2023-0101",
                "roll_no": "CFSI/DFS/23/042",
                "name": "Rahul V. Patel",
                "father_name": "Vikrambhai Patel",
                "course": "Diploma In Fire Safety",
                "batch": "Batch 2022-2023",
                "passing_year": "2023",
                "grade": "Distinction (A+)",
                "percentage": "88.5%",
                "verification_status": "Verified",
                "issue_date": "15 June 2023",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80"
            },
            {
                "_id": "stud-02",
                "id": "stud-02",
                "certificate_number": "CFSI-2023-0102",
                "roll_no": "CFSI/SFO/23/018",
                "name": "Amitabh S. Sharma",
                "father_name": "Sanjay Sharma",
                "course": "Sub Fire Officer",
                "batch": "Batch 2023 (Jan - Jun)",
                "passing_year": "2023",
                "grade": "First Class (A)",
                "percentage": "82.0%",
                "verification_status": "Verified",
                "issue_date": "28 July 2023",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=200&q=80"
            },
            {
                "_id": "stud-03",
                "id": "stud-03",
                "certificate_number": "CFSI-2023-0103",
                "roll_no": "CFSI/CFS/23/089",
                "name": "Priyanka D. Parmar",
                "father_name": "Dineshbhai Parmar",
                "course": "Certificate In Fire Safety",
                "batch": "Batch 2023 (Jul - Dec)",
                "passing_year": "2023",
                "grade": "Distinction (A+)",
                "percentage": "91.2%",
                "verification_status": "Verified",
                "issue_date": "10 January 2024",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=200&q=80"
            },
            {
                "_id": "stud-04",
                "id": "stud-04",
                "certificate_number": "CFSI-2024-0201",
                "roll_no": "CFSI/IS/24/005",
                "name": "Hardik K. Solanki",
                "father_name": "Kiritkumar Solanki",
                "course": "Industrial Safety",
                "batch": "Batch 2024 (Jan - Mar)",
                "passing_year": "2024",
                "grade": "First Class (A)",
                "percentage": "79.5%",
                "verification_status": "Verified",
                "issue_date": "14 April 2024",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80"
            },
            {
                "_id": "stud-05",
                "id": "stud-05",
                "certificate_number": "CFSI-2024-0202",
                "roll_no": "CFSI/DFS/23/094",
                "name": "Manish R. Yadav",
                "father_name": "Ramesh Yadav",
                "course": "Diploma In Fire Safety",
                "batch": "Batch 2023-2024",
                "passing_year": "2024",
                "grade": "Distinction (A+)",
                "percentage": "86.4%",
                "verification_status": "Verified",
                "issue_date": "20 June 2024",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80"
            },
            {
                "_id": "stud-06",
                "id": "stud-06",
                "certificate_number": "CFSI-2024-0203",
                "roll_no": "CFSI/SFO/24/011",
                "name": "Jayesh M. Vaghela",
                "father_name": "Maheshbhai Vaghela",
                "course": "Sub Fire Officer",
                "batch": "Batch 2024 (Jan - Jun)",
                "passing_year": "2024",
                "grade": "First Class (A)",
                "percentage": "84.0%",
                "verification_status": "Verified",
                "issue_date": "18 July 2024",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=200&q=80"
            },
            {
                "_id": "stud-07",
                "id": "stud-07",
                "certificate_number": "CFSI-2022-0055",
                "roll_no": "CFSI/CFS/22/031",
                "name": "Divyesh B. Rathod",
                "father_name": "Bhaveshbhai Rathod",
                "course": "Certificate In Fire Safety",
                "batch": "Batch 2022 (Jan - Jun)",
                "passing_year": "2022",
                "grade": "First Class (B+)",
                "percentage": "74.8%",
                "verification_status": "Verified",
                "issue_date": "30 July 2022",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=200&q=80"
            },
            {
                "_id": "stud-08",
                "id": "stud-08",
                "certificate_number": "CFSI-2022-0089",
                "roll_no": "CFSI/DFS/21/077",
                "name": "Kavita N. Joshi",
                "father_name": "Nileshbhai Joshi",
                "course": "Diploma In Fire Safety",
                "batch": "Batch 2021-2022",
                "passing_year": "2022",
                "grade": "Distinction (A+)",
                "percentage": "89.0%",
                "verification_status": "Verified",
                "issue_date": "25 June 2022",
                "center_location": "CFSI Vadodara Main Campus, Gujarat",
                "photo_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=200&q=80"
            }
        ]

        for s in students_data:
            existing = await db.students.find_one({"certificate_number": s["certificate_number"]})
            if not existing:
                await db.students.insert_one(s)

        # 3. Seed 3-Slot Daily Muster Attendance
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        attendance_seed = [
            # Rahul V. Patel
            {
                "_id": "att-seed-101-1",
                "id": "att-seed-101-1",
                "certificate_number": "CFSI-2023-0101",
                "date": today_iso,
                "slot": "Slot 1",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topic_or_module": "Morning PT, Squad Marching & Hose Flaking Drill",
                "remarks": "Punctual, full gear turnout",
                "marked_by": "Chief Instructor Dave"
            },
            {
                "_id": "att-seed-101-2",
                "id": "att-seed-101-2",
                "certificate_number": "CFSI-2023-0101",
                "date": today_iso,
                "slot": "Slot 2",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topic_or_module": "NBC Hazard Codes & Chemical Protective Suits (Level-A)",
                "remarks": "Scored 100% on safety checklist test",
                "marked_by": "Chief Instructor Dave"
            },
            {
                "_id": "att-seed-101-3",
                "id": "att-seed-101-3",
                "certificate_number": "CFSI-2023-0101",
                "date": today_iso,
                "slot": "Slot 3",
                "course": "Diploma In Fire Safety",
                "status": "Present",
                "topic_or_module": "High-Rise Drill Tower: Self-Rescue & Abseiling",
                "remarks": "Clear anchor rigging technique",
                "marked_by": "Officer Rathod"
            },
            # Amitabh S. Sharma
            {
                "_id": "att-seed-102-1",
                "id": "att-seed-102-1",
                "certificate_number": "CFSI-2023-0102",
                "date": today_iso,
                "slot": "Slot 1",
                "course": "Sub Fire Officer",
                "status": "Present",
                "topic_or_module": "Incident Command Group Physical Fitness & Calisthenics",
                "remarks": "Led squad warming up",
                "marked_by": "Chief Instructor Dave"
            },
            {
                "_id": "att-seed-102-2",
                "id": "att-seed-102-2",
                "certificate_number": "CFSI-2023-0102",
                "date": today_iso,
                "slot": "Slot 2",
                "course": "Sub Fire Officer",
                "status": "Present",
                "topic_or_module": "Radio Communications & Hazmat Triage Protocol",
                "remarks": "Good radio terminology adherence",
                "marked_by": "Officer Rathod"
            },
            {
                "_id": "att-seed-102-3",
                "id": "att-seed-102-3",
                "certificate_number": "CFSI-2023-0102",
                "date": today_iso,
                "slot": "Slot 3",
                "course": "Sub Fire Officer",
                "status": "Present",
                "topic_or_module": "Smoke Diving Chamber & BA Set Duration Math",
                "remarks": "Completed labyrinth in 7m 45s",
                "marked_by": "Officer Rathod"
            },
            # Priyanka D. Parmar
            {
                "_id": "att-seed-103-1",
                "id": "att-seed-103-1",
                "certificate_number": "CFSI-2023-0103",
                "date": today_iso,
                "slot": "Slot 1",
                "course": "Certificate In Fire Safety",
                "status": "Present",
                "topic_or_module": "Hydrant Operation & Nozzle Branch Control Drills",
                "remarks": "High water pressure control test cleared",
                "marked_by": "Senior Instructor Solanki"
            },
            {
                "_id": "att-seed-103-2",
                "id": "att-seed-103-2",
                "certificate_number": "CFSI-2023-0103",
                "date": today_iso,
                "slot": "Slot 2",
                "course": "Certificate In Fire Safety",
                "status": "Present",
                "topic_or_module": "Portable Extinguisher PASS Method & CO2 Systems",
                "remarks": "Extinguished live Class-B tray in 8s",
                "marked_by": "Senior Instructor Solanki"
            },
            {
                "_id": "att-seed-103-3",
                "id": "att-seed-103-3",
                "certificate_number": "CFSI-2023-0103",
                "date": today_iso,
                "slot": "Slot 3",
                "course": "Certificate In Fire Safety",
                "status": "Late",
                "topic_or_module": "First Aid & CPR Resuscitation Practical Exam",
                "remarks": "Reported 10m late due to transport; cleared practical",
                "marked_by": "Dr. V. Joshi (Medical Officer)"
            }
        ]

        for att in attendance_seed:
            existing = await db.attendance.find_one({
                "certificate_number": att["certificate_number"],
                "date": att["date"],
                "slot": att["slot"]
            })
            if not existing:
                att["created_at"] = f"{today_iso}T08:00:00.000Z"
                await db.attendance.insert_one(att)

        # 4. Seed Results
        results_seed = [
            {
                "_id": "res-seed-101",
                "id": "res-seed-101",
                "certificate_number": "CFSI-2023-0101",
                "course": "Diploma In Fire Safety",
                "subject": "Fire Prevention, Detection & Alarm Systems",
                "marks_obtained": 89.0,
                "max_marks": 100.0,
                "grade": "A+",
                "exam_date": "2023-05-10",
                "semester_or_term": "Term Final Examination",
                "remarks": "Outstanding performance in detector placement circuitry"
            },
            {
                "_id": "res-seed-102",
                "id": "res-seed-102",
                "certificate_number": "CFSI-2023-0101",
                "course": "Diploma In Fire Safety",
                "subject": "Fire Fighting Hydraulics & Heavy Pump Calculations",
                "marks_obtained": 84.0,
                "max_marks": 100.0,
                "grade": "A",
                "exam_date": "2023-05-12",
                "semester_or_term": "Term Final Examination",
                "remarks": "Clear understanding of friction loss and relay pumping"
            },
            {
                "_id": "res-seed-103",
                "id": "res-seed-103",
                "certificate_number": "CFSI-2023-0101",
                "course": "Diploma In Fire Safety",
                "subject": "Specialized Rescue Operations & Breathing Apparatus (BA)",
                "marks_obtained": 92.0,
                "max_marks": 100.0,
                "grade": "A+",
                "exam_date": "2023-05-15",
                "semester_or_term": "Term Final Examination",
                "remarks": "Top score in simulated smoke labyrinth drill"
            },
            {
                "_id": "res-seed-104",
                "id": "res-seed-104",
                "certificate_number": "CFSI-2023-0101",
                "course": "Diploma In Fire Safety",
                "subject": "Industrial Hazards, Chemical Safety & HAZMAT Response",
                "marks_obtained": 89.0,
                "max_marks": 100.0,
                "grade": "A+",
                "exam_date": "2023-05-18",
                "semester_or_term": "Term Final Examination",
                "remarks": "Thorough knowledge of MSDS and emergency spill isolation"
            },
            {
                "_id": "res-seed-201",
                "id": "res-seed-201",
                "certificate_number": "CFSI-2023-0102",
                "course": "Sub Fire Officer",
                "subject": "Incident Command System (ICS) & Emergency Operations",
                "marks_obtained": 86.0,
                "max_marks": 100.0,
                "grade": "A",
                "exam_date": "2023-06-10",
                "semester_or_term": "Semester 2 Comprehensive",
                "remarks": "Strong leadership skills in tactical roleplay scenario"
            },
            {
                "_id": "res-seed-202",
                "id": "res-seed-202",
                "certificate_number": "CFSI-2023-0102",
                "course": "Sub Fire Officer",
                "subject": "Building By-Laws, National Building Code (NBC) & Audits",
                "marks_obtained": 80.0,
                "max_marks": 100.0,
                "grade": "A",
                "exam_date": "2023-06-12",
                "semester_or_term": "Semester 2 Comprehensive",
                "remarks": "Solid grasp of occupant load and staircase egress regulations"
            },
            {
                "_id": "res-seed-301",
                "id": "res-seed-301",
                "certificate_number": "CFSI-2023-0103",
                "course": "Certificate In Fire Safety",
                "subject": "Fire Science Basics, Chemistry of Combustion & Extinguishment",
                "marks_obtained": 94.0,
                "max_marks": 100.0,
                "grade": "A+",
                "exam_date": "2023-11-20",
                "semester_or_term": "Certificate Exit Assessment",
                "remarks": "Highest score across batch in fire tetrahedron theory"
            },
            {
                "_id": "res-seed-302",
                "id": "res-seed-302",
                "certificate_number": "CFSI-2023-0103",
                "course": "Certificate In Fire Safety",
                "subject": "First Aid, CPR, Triage & Disaster Patient Handling",
                "marks_obtained": 91.0,
                "max_marks": 100.0,
                "grade": "A+",
                "exam_date": "2023-11-22",
                "semester_or_term": "Certificate Exit Assessment",
                "remarks": "Flawless practical demo of AED and cervical spine stabilization"
            }
        ]

        for r in results_seed:
            existing = await db.results.find_one({"_id": r["_id"]})
            if not existing:
                await db.results.insert_one(r)

        # 5. Seed News Posts
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
