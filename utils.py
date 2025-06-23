import asyncio
from datetime import datetime, timedelta
from pyrogram import errors
from loguru import logger

from database import update_invite_link, get_channel_by_ids

# Create new invite link for private channel
async def create_invite_link(bot, private_channel_id):
    """Create a new invite link for the private channel"""
    try:
        # Create new invite link
        invite_link = await bot.create_chat_invite_link(
            chat_id=private_channel_id,
            creates_join_request=False,  # Direct join
            member_limit=0  # No limit
        )
        
        logger.info(f"Created new invite link for channel {private_channel_id}")
        return invite_link.invite_link
    
    except errors.ChatAdminRequired:
        logger.error(f"Bot is not admin in channel {private_channel_id}")
        return None
    
    except errors.UserNotParticipant:
        logger.error(f"Bot is not a member of channel {private_channel_id}")
        return None
    
    except Exception as e:
        logger.error(f"Error creating invite link: {e}")
        return None

# Revoke old invite link
async def revoke_invite_link(bot, private_channel_id, invite_link):
    """Revoke an old invite link for the private channel"""
    if not invite_link:
        logger.warning(f"No invite link to revoke for channel {private_channel_id}")
        return True
    
    try:
        # Revoke the old invite link
        await bot.revoke_chat_invite_link(
            chat_id=private_channel_id,
            invite_link=invite_link
        )
        
        logger.info(f"Revoked old invite link for channel {private_channel_id}")
        return True
    
    except errors.ChatAdminRequired:
        logger.error(f"Bot is not admin in channel {private_channel_id}")
        return False
    
    except errors.UserNotParticipant:
        logger.error(f"Bot is not a member of channel {private_channel_id}")
        return False
    
    except errors.InviteHashExpired:
        logger.warning(f"Invite link already expired for channel {private_channel_id}")
        return True  # Consider it a success since it's already expired
    
    except Exception as e:
        logger.error(f"Error revoking invite link: {e}")
        return False

# Update message in main channel with new invite link
async def update_main_message(bot, main_channel_id, message_id, invite_link):
    """Update the message in the main channel with the new invite link"""
    try:
        # Format the message with the new invite link
        message_text = f"🔐 **Private Channel Access**\n\n🔗 **New Invite Link:**\n{invite_link}\n\n⏱ **Updated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n🤖 Powered by @InviteLinkGuardBot"
        
        # Edit the message
        await bot.edit_message_text(
            chat_id=main_channel_id,
            message_id=message_id,
            text=message_text
        )
        
        logger.info(f"Updated message in channel {main_channel_id}")
        return True
    
    except errors.MessageNotModified:
        logger.warning(f"Message not modified in channel {main_channel_id} (content is the same)")
        return True  # Consider it a success
    
    except errors.MessageIdInvalid:
        logger.error(f"Invalid message ID {message_id} in channel {main_channel_id}")
        return False
    
    except errors.ChannelInvalid:
        logger.error(f"Invalid channel {main_channel_id}")
        return False
    
    except errors.ChatAdminRequired:
        logger.error(f"Bot is not admin in channel {main_channel_id}")
        return False
    
    except errors.UserNotParticipant:
        logger.error(f"Bot is not a member of channel {main_channel_id}")
        return False
    
    except Exception as e:
        logger.error(f"Error updating message: {e}")
        return False

# Check if user is admin in channel
async def is_user_admin(bot, user_id, channel_id):
    """Check if a user is an admin in a channel"""
    try:
        # Get chat member info
        chat_member = await bot.get_chat_member(channel_id, user_id)
        
        # Check if user is an admin or owner
        return chat_member.status in ["administrator", "creator"]
    
    except errors.UserNotParticipant:
        logger.warning(f"User {user_id} is not a member of channel {channel_id}")
        return False
    
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

# Check if bot is admin in channel with required permissions
async def is_bot_admin_with_permissions(bot, channel_id):
    """Check if the bot is an admin in the channel with required permissions"""
    try:
        # Get bot's ID
        bot_id = (await bot.get_me()).id
        
        # Get chat member info
        chat_member = await bot.get_chat_member(channel_id, bot_id)
        
        # Check if bot is an admin
        if chat_member.status not in ["administrator", "creator"]:
            return False
        
        # If bot is an admin, check for required permissions
        if chat_member.status == "administrator":
            # For main channel: can_edit_messages
            # For private channel: can_invite_users
            # We'll check specific permissions in the command handlers
            return True
        
        # If bot is the creator, it has all permissions
        return True
    
    except errors.UserNotParticipant:
        logger.warning(f"Bot is not a member of channel {channel_id}")
        return False
    
    except Exception as e:
        logger.error(f"Error checking bot admin status: {e}")
        return False

# Main function to update channel invite link
async def update_channel_invite_link(bot, user_id, main_channel_id, private_channel_id, message_id):
    """Update the invite link for a channel and update the message in the main channel"""
    try:
        # Get current channel data
        channel_data = await get_channel_by_ids(user_id, main_channel_id)
        
        if not channel_data:
            logger.warning(f"No channel data found for user {user_id} and channel {main_channel_id}")
            return False
        
        # Get current invite link
        current_invite_link = channel_data.get("current_invite_link")
        
        # Create new invite link
        new_invite_link = await create_invite_link(bot, private_channel_id)
        
        if not new_invite_link:
            logger.error(f"Failed to create new invite link for channel {private_channel_id}")
            return False
        
        # Update message in main channel
        message_updated = await update_main_message(bot, main_channel_id, message_id, new_invite_link)
        
        if not message_updated:
            logger.error(f"Failed to update message in channel {main_channel_id}")
            return False
        
        # Revoke old invite link (if exists)
        if current_invite_link:
            await revoke_invite_link(bot, private_channel_id, current_invite_link)
        
        # Update database with new invite link
        db_updated = await update_invite_link(user_id, main_channel_id, new_invite_link)
        
        if not db_updated:
            logger.error(f"Failed to update database for user {user_id} and channel {main_channel_id}")
            return False
        
        logger.info(f"Successfully updated invite link for user {user_id} and channel {main_channel_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error in update_channel_invite_link: {e}")
        return False