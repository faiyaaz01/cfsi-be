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
        await db.users.create_index("username", unique=True)
        await db.students.create_index("certificate_number", unique=True)
        await db.attendance.create_index([("certificate_number", 1), ("date", 1), ("slot", 1)])
        await db.results.create_index("certificate_number")
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
