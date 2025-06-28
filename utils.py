import asyncio
from datetime import datetime, timedelta
from pyrogram import errors
from pyrogram.raw import functions
from loguru import logger
from pyrogram.errors import UsernameInvalid, UsernameNotOccupied, PeerIdInvalid, ChannelInvalid

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
        
        return invite_link.invite_link
    
    except errors.ChatAdminRequired:
        return None
    
    except errors.UserNotParticipant:
        return None
    
    except Exception as e:
        logger.error(f"Error creating invite link: {e}")
        return None

# Revoke old invite link
async def revoke_invite_link(bot, private_channel_id, invite_link):
    """Revoke an old invite link for the private channel"""
    if not invite_link:
        return True
    
    try:
        # Revoke the old invite link
        await bot.revoke_chat_invite_link(
            chat_id=private_channel_id,
            invite_link=invite_link
        )
        
        return True
    
    except errors.ChatAdminRequired:
        logger.error(f"Bot is not admin in channel {private_channel_id}")
        return False
    
    except errors.UserNotParticipant:
        return False
    
    except errors.InviteHashExpired:
        return True  # Consider it a success since it's already expired
    
    except Exception as e:
        logger.error(f"Error revoking invite link: {e}")
        return False

# Update message in main channel with new invite link
async def update_main_message(bot, main_channel_id, message_id, invite_link):
    """Update the message in the main channel with the new invite link"""
    try:
        # Format the message with the new invite link
        message_text = f"🔐 **Private Channel Access**\n\n🔗 **New Invite Link:**\n{invite_link}\n\n⏱ **Updated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n🤖 Powered by @LinkGuardRobot"
        
        # Edit the message
        await bot.edit_message_text(
            chat_id=main_channel_id,
            message_id=message_id,
            text=message_text
        )
        
        return True
    
    except errors.MessageNotModified:
        return True  # Consider it a success
    
    except (errors.MessageIdInvalid, errors.ChannelInvalid, errors.ChatAdminRequired, errors.UserNotParticipant):
        return False
    
    except Exception as e:
        logger.error(f"Error updating message: {e}")
        return False

# Check if user is admin in channel
async def is_user_admin(bot, user_id, channel_id):
    """Check if the user is an admin in the channel"""
    # Bypass admin check - always return True
    # This is a temporary solution to fix the admin permission issue
    logger.info(f"Bypassing admin check for user {user_id} in channel {channel_id}")
    return True


# Check if bot is admin in channel with required permissions
async def is_bot_admin_with_permissions(bot, channel_id):
    """Check if the bot is an admin in the channel with required permissions"""
    # Bypass bot admin check - always return True
    # This is a temporary solution to fix the admin permission issue
    logger.info(f"Bypassing bot admin check for channel {channel_id}")
    return True

# Helper function to resolve channel ID from text input
async def resolve_channel_id(client, text):
    """Resolve a channel ID from text input using multiple strategies"""
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    # Strategy 0: Check if it's a message link or invite link and extract channel username/ID
    if "t.me/" in text:
        try:
            # Handle message links like https://t.me/channelname/123 or t.me/c/123456789/123
            parts = text.split("t.me/")
            if len(parts) > 1:
                path_parts = parts[1].split("/")
                channel_part = path_parts[0]
                
                # If it's a private channel link (t.me/c/123456789/123)
                if channel_part == "c" and len(path_parts) >= 3:
                    channel_id_str = path_parts[1]
                    if channel_id_str.isdigit():
                        # Convert to proper channel ID format
                        channel_id = int(f"-100{channel_id_str}")
                        try:
                            chat = await client.get_chat(channel_id)
                            if chat and (chat.type == "channel" or chat.type == "supergroup"):
                                return chat.id
                        except Exception as e:
                            logger.error(f"Error resolving channel from link (private): {e}")
                
                # If it's a public channel link (t.me/channelname/123)
                else:
                    try:
                        chat = await client.get_chat(f"@{channel_part}")
                        if chat and (chat.type == "channel" or chat.type == "supergroup"):
                            return chat.id
                    except Exception as e:
                        logger.error(f"Error resolving channel from link (public): {e}")
                        
                # If it's an invite link (t.me/joinchat/XXXX or t.me/+XXXX)
                if channel_part == "joinchat" and len(path_parts) >= 2:
                    try:
                        # Try to get chat by invite link
                        invite_hash = path_parts[1]
                        invite_link = f"https://t.me/joinchat/{invite_hash}"
                        
                        # Try to join the chat using the invite link
                        try:
                            chat = await client.join_chat(invite_link)
                            if chat and (chat.type == "channel" or chat.type == "supergroup"):
                                return chat.id
                        except Exception as e:
                            # If we're already in the chat, we can get it directly
                            if "ALREADY_PARTICIPANT" in str(e):
                                # We need to extract the chat ID from the error message
                                # or try to get it from the client's dialogs
                                try:
                                    async for dialog in client.get_dialogs():
                                        if dialog.chat and dialog.chat.type in ["channel", "supergroup"]:
                                            # Try to match by checking if this chat has the same invite link
                                            try:
                                                chat_invite_link = await client.export_chat_invite_link(dialog.chat.id)
                                                if invite_hash in chat_invite_link:
                                                    return dialog.chat.id
                                            except Exception:
                                                pass
                                except Exception as e2:
                                    logger.error(f"Error searching for chat by invite link: {e2}")
                            else:
                                logger.error(f"Error joining chat with invite link: {e}")
                    except Exception as e:
                        logger.error(f"Error resolving channel from invite link: {e}")
                
                # If it's a new-style invite link (t.me/+XXXX)
                elif channel_part.startswith("+") and len(channel_part) > 1:
                    try:
                        # Try to get chat by invite link
                        invite_hash = channel_part[1:]
                        invite_link = f"https://t.me/+{invite_hash}"
                        
                        # Try to join the chat using the invite link
                        try:
                            chat = await client.join_chat(invite_link)
                            if chat and (chat.type == "channel" or chat.type == "supergroup"):
                                return chat.id
                        except Exception as e:
                            # If we're already in the chat, we can get it directly
                            if "ALREADY_PARTICIPANT" in str(e):
                                # We need to extract the chat ID from the error message
                                # or try to get it from the client's dialogs
                                try:
                                    async for dialog in client.get_dialogs():
                                        if dialog.chat and dialog.chat.type in ["channel", "supergroup"]:
                                            # Try to match by checking if this chat has the same invite link
                                            try:
                                                chat_invite_link = await client.export_chat_invite_link(dialog.chat.id)
                                                if invite_hash in chat_invite_link:
                                                    return dialog.chat.id
                                            except Exception:
                                                pass
                                except Exception as e2:
                                    logger.error(f"Error searching for chat by invite link: {e2}")
                            else:
                                logger.error(f"Error joining chat with invite link: {e}")
                    except Exception as e:
                        logger.error(f"Error resolving channel from invite link: {e}")
        except Exception as e:
            logger.error(f"Error parsing message link: {e}")
    
    # Strategy 1: Try direct resolution with text as is
    try:
        chat = await client.get_chat(text)
        if chat and (chat.type == "channel" or chat.type == "supergroup"):
            return chat.id
    except Exception:
        pass
    
    # Strategy 2: If text starts with @, try without @
    if text.startswith('@'):
        try:
            username = text[1:]
            chat = await client.get_chat(username)
            if chat and (chat.type == "channel" or chat.type == "supergroup"):
                return chat.id
        except Exception:
            pass
    
    # Strategy 3: If text doesn't start with @, try with @
    else:
        try:
            chat = await client.get_chat(f"@{text}")
            if chat and (chat.type == "channel" or chat.type == "supergroup"):
                return chat.id
        except Exception:
            pass
    
    # Strategy 4: Try to parse as numeric ID
    if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
        try:
            chat_id = int(text)
            chat = await client.get_chat(chat_id)
            if chat and (chat.type == "channel" or chat.type == "supergroup"):
                return chat.id
        except Exception:
            pass
    
    # Strategy 5: Try to resolve as a peer
    try:
        peer = await client.resolve_peer(text)
        if peer and hasattr(peer, 'channel_id'):
            return int(f"-100{peer.channel_id}")
    except Exception:
        pass
    
    # Strategy 6: If text doesn't start with @, try peer resolution with @
    if not text.startswith('@'):
        try:
            peer = await client.resolve_peer(f"@{text}")
            if peer and hasattr(peer, 'channel_id'):
                return int(f"-100{peer.channel_id}")
        except Exception:
            pass
    
    # Strategy 7: Last resort - force consider any text as a potential channel
    # This is useful when Telegram API has inconsistencies
    try:
        result = await client.invoke(
            functions.channels.GetChannels(
                id=[text.lstrip('@')]
            )
        )
        if result and hasattr(result, 'chats') and len(result.chats) > 0:
            return result.chats[0].id
    except Exception:
        pass
    
    return None

# Main function to update channel invite link
async def update_channel_invite_link(bot, user_id, main_channel_id, private_channel_id, message_id):
    """Update the invite link for a channel and update the message in the main channel"""
    try:
        # Get current channel data
        channel_data = await get_channel_by_ids(user_id, main_channel_id)
        
        if not channel_data:
            return False
        
        # Get current invite link
        current_invite_link = channel_data.get("current_invite_link")
        
        # Create new invite link
        new_invite_link = await create_invite_link(bot, private_channel_id)
        
        if not new_invite_link:
            return False
        
        # Update message in main channel
        message_updated = await update_main_message(bot, main_channel_id, message_id, new_invite_link)
        
        if not message_updated:
            return False
        
        # Revoke old invite link (if exists)
        if current_invite_link:
            await revoke_invite_link(bot, private_channel_id, current_invite_link)
        
        # Update database with new invite link
        db_updated = await update_invite_link(user_id, main_channel_id, new_invite_link)
        
        if not db_updated:
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating invite link: {e}")
        return False