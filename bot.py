import os
import asyncio
from pyrogram import Client
from dotenv import load_dotenv
from loguru import logger

# Import modules
from config import setup_logging
from database import init_db
from handlers import register_handlers
from scheduler import setup_scheduler
from keep_alive import keep_alive

# Load environment variables
load_dotenv()

# Configure logging
setup_logging()

# Bot initialization
bot = Client(
    "InviteLinkGuardBot",
    api_id=os.getenv("API_ID"),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Main function to start the bot
async def main():
    logger.info("Starting InviteLink Guard Bot...")
    
    # Initialize database connection
    await init_db()
    
    # Register message handlers
    register_handlers(bot)
    
    # Start the bot
    await bot.start()
    logger.info("Bot started successfully!")
    
    # Setup scheduler for link updates
    await setup_scheduler(bot)
    
    # Start keep-alive web server for Replit
    if os.getenv("REPLIT_DB_URL"):
        logger.info("Running on Replit, starting keep-alive server")
        keep_alive()
    
    # Keep the bot running
    await asyncio.Event().wait()

# Entry point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")