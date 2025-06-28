import os
import motor.motor_asyncio
from pymongo.errors import ConnectionFailure
from loguru import logger
from config import COLLECTION_CHANNELS

# MongoDB client
client = None
db = None

# Initialize database connection
async def init_db():
    global client, db
    
    # Get MongoDB URI from environment variables
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not mongodb_uri:
        logger.error("MongoDB URI not found in environment variables")
        raise ValueError("MongoDB URI not found. Please set MONGODB_URI in .env file")
    
    try:
        # Connect to MongoDB with proper connection settings
        client = motor.motor_asyncio.AsyncIOMotorClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            maxPoolSize=10,
            retryWrites=True,
            w="majority"
        )
        
        # Ping the server to verify connection
        await client.admin.command('ping')
        
        # Get database (default to 'invitelinkguard')
        db = client.get_database('invitelinkguard')
        
        logger.info("Connected to MongoDB Atlas successfully")
        
        # Create indexes for better performance
        await create_indexes()
        
        return db
    
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

# Create database indexes
async def create_indexes():
    try:
        if db is None:
            logger.error("Database not initialized when creating indexes")
            return
            
        # Check if collection exists, create it if it doesn't
        collections = await db.list_collection_names()
        if COLLECTION_CHANNELS not in collections:
            await db.create_collection(COLLECTION_CHANNELS)
            logger.info(f"Created collection {COLLECTION_CHANNELS}")
        
        # Skip index creation for now - we'll let MongoDB create them automatically
        # This avoids potential issues with index creation
        logger.info("Skipping explicit index creation to avoid potential issues")
        return
        
    except Exception as e:
        logger.error(f"Error setting up database collections: {e}")
        # Continue execution even if collection setup fails
        # The application can still function without explicit collections

# Channel operations
async def add_linked_channels(user_id, main_channel_id, private_channel_id, message_id):
    """Add or update linked channels for a user"""
    try:
        # Current timestamp
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        
        # Calculate next update time (12 hours from now)
        next_update = now + timedelta(hours=12)
        
        # Prepare document
        document = {
            "user_id": user_id,
            "main_channel_id": main_channel_id,
            "private_channel_id": private_channel_id,
            "message_id": message_id,
            "current_invite_link": None,  # Will be set during first update
            "last_update_time": now,
            "next_update_time": next_update,
            "created_at": now,
            "updated_at": now
        }
        
        # Insert or update document
        result = await db[COLLECTION_CHANNELS].update_one(
            {"user_id": user_id, "main_channel_id": main_channel_id},
            {"$set": document},
            upsert=True
        )
        
        logger.info(f"Linked channels added/updated for user {user_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error adding linked channels: {e}")
        return False

async def remove_linked_channels(user_id, main_channel_id):
    """Remove linked channels for a user"""
    try:
        result = await db[COLLECTION_CHANNELS].delete_one(
            {"user_id": user_id, "main_channel_id": main_channel_id}
        )
        
        if result.deleted_count > 0:
            logger.info(f"Linked channels removed for user {user_id}")
            return True
        else:
            logger.warning(f"No linked channels found for user {user_id} and channel {main_channel_id}")
            return False
    
    except Exception as e:
        logger.error(f"Error removing linked channels: {e}")
        return False

async def get_user_linked_channels(user_id):
    """Get all linked channels for a user"""
    try:
        cursor = db[COLLECTION_CHANNELS].find({"user_id": user_id})
        channels = await cursor.to_list(length=None)
        return channels
    
    except Exception as e:
        logger.error(f"Error getting linked channels for user {user_id}: {e}")
        return []

async def get_channel_by_ids(user_id, main_channel_id):
    """Get linked channel by user_id and main_channel_id"""
    try:
        channel = await db[COLLECTION_CHANNELS].find_one(
            {"user_id": user_id, "main_channel_id": main_channel_id}
        )
        return channel
    
    except Exception as e:
        logger.error(f"Error getting channel: {e}")
        return None

async def update_invite_link(user_id, main_channel_id, invite_link):
    """Update invite link for a linked channel"""
    try:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        next_update = now + timedelta(hours=12)
        
        result = await db[COLLECTION_CHANNELS].update_one(
            {"user_id": user_id, "main_channel_id": main_channel_id},
            {
                "$set": {
                    "current_invite_link": invite_link,
                    "last_update_time": now,
                    "next_update_time": next_update,
                    "updated_at": now
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Invite link updated for user {user_id} and channel {main_channel_id}")
            return True
        else:
            logger.warning(f"No linked channels found for update")
            return False
    
    except Exception as e:
        logger.error(f"Error updating invite link: {e}")
        return False

async def get_channels_for_update():
    """Get all channels that need to be updated"""
    try:
        from datetime import datetime
        now = datetime.utcnow()
        
        cursor = db[COLLECTION_CHANNELS].find({"next_update_time": {"$lte": now}})
        channels = await cursor.to_list(length=None)
        return channels
    
    except Exception as e:
        logger.error(f"Error getting channels for update: {e}")
        return []