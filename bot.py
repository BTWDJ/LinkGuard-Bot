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
    "LinkGuardRobot",
    api_id=os.getenv("API_ID"),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Main function to start the bot
async def main():
    logger.info("Starting Link Guard Robot...")
    
    try:
        # Initialize database connection
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Continuing without database connection - some features may not work")
    
    # Register message handlers
    register_handlers(bot)
    
    # Start the bot
    try:
        await bot.start()
        logger.info("Bot started successfully!")
        me = await bot.get_me()
        logger.info(f"Bot username is @{me.username} ({me.id})")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return
    
    try:
        # Setup scheduler for link updates
        await setup_scheduler(bot)
        logger.info("Scheduler setup completed")
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}")
        logger.warning("Continuing without scheduler - automatic link updates will not work")
    
    # Start keep-alive web server for Replit
    if os.getenv("REPLIT_DB_URL"):
        logger.info("Running on Replit, starting keep-alive server")
        keep_alive()
    
    logger.info("Bot is now running! Press Ctrl+C to stop")
    
    # Keep the bot running
    await asyncio.Event().wait()

# Entry point
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot stopped due to critical error: {e}")
    finally:
        # Ensure proper cleanup
        try:
            loop.run_until_complete(bot.stop())
            logger.info("Bot stopped gracefully")
        except:
            pass