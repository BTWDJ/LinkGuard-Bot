from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from database import get_user_linked_channels, get_channel_by_ids
from utils import update_channel_invite_link

# Main callback query handler
async def callback_query_handler(client: Client, callback_query: CallbackQuery):
    """Handle callback queries from inline keyboard buttons"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Handle different callback data
    if data == "help":
        await help_callback(client, callback_query)
    
    elif data == "add":
        await add_callback(client, callback_query)
    
    elif data == "refresh_all":
        await refresh_all_callback(client, callback_query)
    
    elif data.startswith("update_"):
        # Extract channel ID from callback data
        try:
            main_channel_id = int(data.split("_")[1])
            await update_single_callback(client, callback_query, main_channel_id)
        except (ValueError, IndexError):
            await callback_query.answer("Invalid callback data")

# Help callback
async def help_callback(client: Client, callback_query: CallbackQuery):
    """Handle help button callback"""
    await callback_query.answer("Showing help information")
    
    # Create help message directly in callback handler
    help_text = "📚 **Link Guard Robot Help**\n\n"
    help_text += "**Available Commands:**\n\n"
    help_text += "🔹 /start - Start the bot and see welcome message\n"
    help_text += "🔹 /help - Show this help message\n"
    help_text += "🔹 /add - Link your public and private channels\n"
    help_text += "🔹 /remove - Unlink previously linked channels\n"
    help_text += "🔹 /status - Check your linked channels and next update time\n\n"
    
    help_text += "**Required Permissions:**\n"
    help_text += "For this bot to work properly, it needs to be an admin with these permissions:\n"
    help_text += "• In public channel: 'Edit Messages'\n"
    help_text += "• In private channel: 'Invite Users'\n\n"
    
    help_text += "**How to Use:**\n"
    help_text += "1. Add the bot as admin to both channels\n"
    help_text += "2. Create a message in your public channel where the invite link will be placed\n"
    help_text += "3. Use /add and follow the instructions\n"
    help_text += "4. The bot will automatically update the invite link every 6 hours\n\n"
    
    help_text += "If you have any questions or issues, feel free to contact the developer."
    
    # Create keyboard with add button
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Add Channels", callback_data="add")
            ]
        ]
    )
    
    await callback_query.message.reply(help_text, reply_markup=keyboard)

# Add callback
async def add_callback(client: Client, callback_query: CallbackQuery):
    """Handle add button callback"""
    await callback_query.answer("Starting channel linking process")
    
    user_id = callback_query.from_user.id
    
    # We need to import this at runtime to avoid circular imports
    from handlers import user_states
    
    # Set user state to waiting for main channel
    user_states[user_id] = {
        "state": "waiting_main_channel",
        "data": {}
    }
    
    instructions = "🔄 **Channel Linking Process**\n\n"
    instructions += "Please follow these steps:\n\n"
    instructions += "1️⃣ **First, send me your public (main) channel username or ID**\n"
    instructions += "This is the channel where the invite link message will be updated.\n\n"
    instructions += "You can forward a message from the channel or send the channel username (e.g., @mychannel) or ID.\n\n"
    instructions += "Make sure I'm an admin in this channel with 'Edit Messages' permission."
    
    await callback_query.message.reply(instructions)

# Refresh all callback
async def refresh_all_callback(client: Client, callback_query: CallbackQuery):
    """Handle refresh all button callback"""
    user_id = callback_query.from_user.id
    
    # Get user's linked channels
    channels = await get_user_linked_channels(user_id)
    
    if not channels:
        await callback_query.answer("You don't have any linked channels")
        await callback_query.message.reply("❌ You don't have any linked channels to refresh.")
        return
    
    await callback_query.answer("Refreshing all your linked channels...")
    
    # Update message to show progress
    await callback_query.message.reply(
        f"🔄 **Refreshing invite links...**\n\n"
        f"Please wait while I update {len(channels)} channel(s)."
    )
    
    # Process each channel
    success_count = 0
    error_count = 0
    
    for channel in channels:
        try:
            # Extract channel data
            main_channel_id = channel["main_channel_id"]
            private_channel_id = channel["private_channel_id"]
            message_id = channel["message_id"]
            
            # Update invite link
            success = await update_channel_invite_link(
                client,
                user_id,
                main_channel_id,
                private_channel_id,
                message_id
            )
            
            if success:
                success_count += 1
            else:
                error_count += 1
        
        except Exception as e:
            logger.error(f"Error refreshing channel: {e}")
            error_count += 1
    
    # Update message with results
    result_text = f"✅ **Refresh Complete**\n\n"
    result_text += f"Successfully updated: {success_count} channel(s)\n"
    
    if error_count > 0:
        result_text += f"Failed to update: {error_count} channel(s)\n"
    
    result_text += "\nUse /status to see the updated information."
    
    await callback_query.message.reply(result_text)

# Update single callback
async def update_single_callback(client: Client, callback_query: CallbackQuery, main_channel_id):
    """Handle update single channel button callback"""
    user_id = callback_query.from_user.id
    
    # Get channel data
    channel = await get_channel_by_ids(user_id, main_channel_id)
    
    if not channel:
        await callback_query.answer("Channel not found or you don't have permission")
        await callback_query.message.reply("❌ Channel not found.")
        return
    
    await callback_query.answer("Refreshing invite link...")
    
    # Update message to show progress
    await callback_query.message.reply(
        f"🔄 **Refreshing invite link...**\n\n"
        f"Please wait while I update the channel."
    )
    
    try:
        # Extract channel data
        private_channel_id = channel["private_channel_id"]
        message_id = channel["message_id"]
        
        # Update invite link
        success = await update_channel_invite_link(
            client,
            user_id,
            main_channel_id,
            private_channel_id,
            message_id
        )
        
        if success:
            # Try to get channel names
            try:
                main_chat = await client.get_chat(main_channel_id)
                private_chat = await client.get_chat(private_channel_id)
                
                main_name = main_chat.title or f"Channel {main_channel_id}"
                private_name = private_chat.title or f"Channel {private_channel_id}"
            except Exception:
                main_name = f"Channel {main_channel_id}"
                private_name = f"Channel {private_channel_id}"
            
            # Update message with results
            result_text = f"✅ **Invite Link Updated Successfully**\n\n"
            result_text += f"📢 **Public Channel:** {main_name}\n"
            result_text += f"🔒 **Private Channel:** {private_name}\n\n"
            result_text += f"The message in your public channel has been updated with the new invite link.\n\n"
            result_text += f"Use /status to see the updated information."
            
            await callback_query.message.reply(result_text)
        else:
            await callback_query.message.reply(
                f"❌ **Failed to Update Invite Link**\n\n"
                f"There was an error updating the invite link. Please check that:\n\n"
                f"1. The bot is still an admin in both channels\n"
                f"2. The bot has the required permissions\n"
                f"3. The message still exists in the public channel\n\n"
                f"Use /status to check your linked channels."
            )
    
    except Exception as e:
        logger.error(f"Error in update_single_callback: {e}")
        await callback_query.message.reply(
            f"❌ **An Error Occurred**\n\n"
            f"There was an error updating the invite link. Please try again later.\n\n"
            f"Use /status to check your linked channels."
        )