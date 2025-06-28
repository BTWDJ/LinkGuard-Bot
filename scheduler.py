import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from database import get_channels_for_update
from utils import update_channel_invite_link
from config import UPDATE_INTERVAL_HOURS

# Global scheduler instance
scheduler = None

# Setup scheduler
async def setup_scheduler(bot):
    global scheduler
    
    # Create scheduler if it doesn't exist
    if scheduler is None:
        scheduler = AsyncIOScheduler()
        
        # Add job to check for updates every 5 minutes
        scheduler.add_job(
            process_link_updates,
            IntervalTrigger(minutes=5),
            args=[bot],
            id="link_update_job",
            replace_existing=True
        )
        
        # Start scheduler
        scheduler.start()
        logger.info(f"Scheduler started with update interval of {UPDATE_INTERVAL_HOURS} hours")
    
    # Run initial update check
    await process_link_updates(bot)

# Process link updates
async def process_link_updates(bot):
    try:
        # Get channels that need to be updated
        try:
            channels = await get_channels_for_update()
        except Exception as db_error:
            logger.error(f"Database error when getting channels for update: {db_error}")
            return
        
        if not channels:
            logger.debug("No channels need updating at this time")
            return
        
        logger.info(f"Found {len(channels)} channels that need updating")
        
        # Process each channel
        for channel in channels:
            try:
                # Validate channel data
                required_fields = ["user_id", "main_channel_id", "private_channel_id", "message_id"]
                if not all(field in channel for field in required_fields):
                    logger.warning(f"Channel data missing required fields: {channel}")
                    continue
                
                # Extract channel data
                user_id = channel["user_id"]
                main_channel_id = channel["main_channel_id"]
                private_channel_id = channel["private_channel_id"]
                message_id = channel["message_id"]
                
                # Update invite link
                success = await update_channel_invite_link(
                    bot,
                    user_id,
                    main_channel_id,
                    private_channel_id,
                    message_id
                )
                
                if success:
                    logger.info(f"Successfully updated invite link for user {user_id} and channel {main_channel_id}")
                else:
                    logger.warning(f"Failed to update invite link for user {user_id} and channel {main_channel_id}")
                
                # Add a small delay between updates to avoid rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing channel update: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error in process_link_updates: {e}")
        # Continue running the bot even if there's an error in the update process