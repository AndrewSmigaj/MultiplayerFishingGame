import logging
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from ..config import settings

log = logging.getLogger(__name__)

# Global variable to hold the client and database instances
db_client: MongoClient | None = None
db: Database | None = None

def connect_to_db():
    """Establishes connection to the MongoDB database."""
    global db_client, db
    if db_client is None:
        log.info(f"Connecting to MongoDB at {settings.MONGO_URI}...")
        try:
            db_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
            # The ismaster command is cheap and does not require auth.
            db_client.admin.command('ismaster')
            db = db_client[settings.MONGO_DB_NAME]
            log.info(f"Successfully connected to MongoDB database: {settings.MONGO_DB_NAME}")
        except ConnectionFailure as e:
            log.error(f"Could not connect to MongoDB: {e}")
            db_client = None
            db = None
            # Depending on the application, you might want to raise an exception
            # or handle this more gracefully (e.g., retry logic).
            raise ConnectionFailure("Failed to connect to MongoDB") from e
        except Exception as e:
            log.error(f"An unexpected error occurred during MongoDB connection: {e}")
            db_client = None
            db = None
            raise

def get_db() -> Database:
    """Returns the database instance, connecting if necessary."""
    if db is None:
        connect_to_db()
    if db is None:
        # This should ideally not happen if connect_to_db raises on failure
        raise ConnectionFailure("Database connection is not available.")
    return db

def close_db_connection():
    """Closes the MongoDB connection."""
    global db_client, db
    if db_client:
        log.info("Closing MongoDB connection.")
        db_client.close()
        db_client = None
        db = None

# Consider initializing the connection when the app starts
# and closing it when it shuts down using Flask's app context or teardown requests.
# For simplicity now, get_db() connects on first access.
