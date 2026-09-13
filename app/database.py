import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import mongomock_motor
from app.config import settings

logger = logging.getLogger("cfsi.database")

class DatabaseManager:
    client = None
    db: AsyncIOMotorDatabase = None
    is_mock: bool = False

db_manager = DatabaseManager()

async def connect_to_mongo():
    """Initializes connection to MongoDB (or mock fallback if local mongod is offline)."""
    try:
        real_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=2000
        )
        # Verify server is responding
        await real_client.admin.command("ping")
        db_manager.client = real_client
        db_manager.db = real_client[settings.MONGODB_DB_NAME]
        db_manager.is_mock = False
        print(f"[MongoDB] Connected to live MongoDB: {settings.MONGODB_URL}/{settings.MONGODB_DB_NAME}")
    except Exception as exc:
        print(f"[MongoDB NOTICE] Could not reach MongoDB at '{settings.MONGODB_URL}': {exc}")
        print(f"[MongoDB] Using in-memory MongoDB driver (mongomock-motor).")
        print(f"[MongoDB TIP] To persist data, configure MONGODB_URL in cfsi-be/.env or launch mongod.")
        mock_client = mongomock_motor.AsyncMongoMockClient()
        db_manager.client = mock_client
        db_manager.db = mock_client[settings.MONGODB_DB_NAME]
        db_manager.is_mock = True

    # Setup indexes
    await setup_indexes()

async def setup_indexes():
    """Ensures necessary MongoDB indexes exist."""
    db = get_database()
    try:
        # Drop obsolete legacy indexes if present
        try:
            student_indexes = await db.students.index_information()
            if "certificate_number_1" in student_indexes:
                await db.students.drop_index("certificate_number_1")
                logger.info("Dropped obsolete index 'certificate_number_1' from students collection.")
        except Exception as drop_e:
            logger.warning(f"Could not inspect or drop obsolete student index: {drop_e}")

        try:
            user_indexes = await db.users.index_information()
            if "certificate_number_1" in user_indexes:
                await db.users.drop_index("certificate_number_1")
        except Exception as drop_e:
            pass

        await db.users.create_index("username", unique=True)
        await db.students.create_index("id", unique=True)
        await db.students.create_index("roll_no")
        await db.attendance.create_index([("student_id", 1), ("date", 1), ("slot", 1)])
        await db.news_posts.create_index("date")
    except Exception as e:
        logger.warning(f"Index creation notice: {e}")

async def close_mongo_connection():
    """Closes MongoDB connection on shutdown."""
    if db_manager.client:
        db_manager.client.close()
        print("[MongoDB] Connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    """Dependency / helper to retrieve the active MongoDB database."""
    if db_manager.db is None:
        mock_client = mongomock_motor.AsyncMongoMockClient()
        db_manager.client = mock_client
        db_manager.db = mock_client[settings.MONGODB_DB_NAME]
        db_manager.is_mock = True
    return db_manager.db
