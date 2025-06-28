from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChannelInvalid
from pyrogram.enums import ChatMemberStatus
from datetime import datetime
from loguru import logger
import os

from database import (
    add_linked_channels,
    remove_linked_channels,
    get_user_linked_channels,
    get_channel_by_ids
)
from utils import (
    is_user_admin,
    is_bot_admin_with_permissions,
    update_channel_invite_link
)
from callback_handlers import callback_query_handler

# User states for conversation handling
user_states = {}

# Initialize BOT_USERNAME here
BOT_USERNAME = None

# Register all handlers
def register_handlers(bot):
    # Define handlers directly with decorators
    
    # Start command handler
    @bot.on_message(filters.command("start") & filters.private)
    async def _start_command(client, message):
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        # Set BOT_USERNAME if needed
        global BOT_USERNAME
        if BOT_USERNAME is None:
            try:
                me = await client.get_me()
                BOT_USERNAME = me.username
                logger.info(f"Bot username set to @{BOT_USERNAME}")
            except Exception as e:
                logger.error(f"Failed to get bot username: {e}")
        
        # Welcome message
        welcome_text = f"👋 Hello, {user_name}!\n\n"
        welcome_text += "🔄 **Welcome to Link Guard Robot!**\n\n"
        welcome_text += "I can help you automatically refresh private channel invite links and update them in your public channel.\n\n"
        welcome_text += "**How it works:**\n"
        welcome_text += "1️⃣ Add me as an admin to both your public and private channels\n"
        welcome_text += "2️⃣ Use /add to link your channels\n"
        welcome_text += "3️⃣ I'll refresh the invite link every 6 hours\n\n"
        welcome_text += "Use /help to learn more about my commands."
        
        # Create keyboard with help button
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📚 Help", callback_data="help"),
                    InlineKeyboardButton("➕ Add Channels", callback_data="add")
                ],
                [
                    InlineKeyboardButton("Tutorial", url="https://t.me/HowtouseLinkguardbot/2")
                ]
            ]
        )
        
        await message.reply(welcome_text, reply_markup=keyboard)
    
    # Help command handler
    @bot.on_message(filters.command("help") & filters.private)
    async def _help_command(client, message):
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
                    InlineKeyboardButton("➕ Add Channels", callback_data="add"),
                    InlineKeyboardButton("Tutorial", url="https://t.me/HowtouseLinkguardbot/2")
                ]
            ]
        )
        
        await message.reply(help_text, reply_markup=keyboard)
    
    # Add command handler
    @bot.on_message(filters.command("add") & filters.private)
    async def _add_command(client, message):
        user_id = message.from_user.id
        
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
        
        await message.reply(instructions)
    
    # Remove command handler
    @bot.on_message(filters.command("remove") & filters.private)
    async def _remove_command(client, message):
        await remove_command(client, message)
    
    # Status command handler
    @bot.on_message(filters.command("status") & filters.private)
    async def _status_command(client, message):
        await status_command(client, message)
    
    # Handle conversation states
    @bot.on_message(filters.private & ~filters.command(["start", "help", "add", "remove", "status", "cancel"]))
    async def _conversation_handler(client, message):
        await handle_conversation(client, message)
    
    # Add cancel command handler
    @bot.on_message(filters.command("cancel") & filters.private)
    async def _cancel_command(client, message):
        user_id = message.from_user.id
        
        # Check if user has an active state
        if user_id in user_states:
            # Clear user state
            del user_states[user_id]
            await message.reply("❌ Operation cancelled. What would you like to do now?")
        else:
            await message.reply("There's no active operation to cancel.")
    
    # Add ping command to test bot responsiveness
    @bot.on_message(filters.command("ping") & filters.private)
    async def _ping_command(client, message):
        await message.reply("Pong! Bot is working correctly! 🤖")
    
    # Register callback handler from callback_handlers.py
    @bot.on_callback_query()
    async def _callback_handler(client, callback_query):
        await callback_query_handler(client, callback_query)

# Start command handler
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Welcome message
    welcome_text = f"👋 Hello, {user_name}!\n\n"
    welcome_text += "🔄 **Welcome to Link Guard Robot!**\n\n"
    welcome_text += "I can help you automatically refresh private channel invite links and update them in your public channel.\n\n"
    welcome_text += "**How it works:**\n"
    welcome_text += "1️⃣ Add me as an admin to both your public and private channels\n"
    welcome_text += "2️⃣ Use /add to link your channels\n"
    welcome_text += "3️⃣ I'll refresh the invite link every 6 hours\n\n"
    welcome_text += "Use /help to learn more about my commands."
    
    # Create keyboard with help button
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📚 Help", callback_data="help"),
                InlineKeyboardButton("➕ Add Channels", callback_data="add")
            ],
            [
                InlineKeyboardButton("Tutorial", url="https://t.me/HowtouseLinkguardbot/2")
            ]
        ]
    )
    
    await message.reply(welcome_text, reply_markup=keyboard)

# Help command handler
async def help_command(client: Client, message: Message):
    """Handle /help command"""
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
                InlineKeyboardButton("➕ Add Channels", callback_data="add"),
                InlineKeyboardButton("Tutorial", url="https://t.me/HowtouseLinkguardbot/2")
            ]
        ]
    )
    
    await message.reply(help_text, reply_markup=keyboard)

# Add command handler
async def add_command(client: Client, message: Message):
    """Handle /add command"""
    user_id = message.from_user.id
    
    # Set user state to waiting for main channel
    user_states[user_id] = {
        "state": "waiting_main_channel",
        "data": {}
    }
    
    instructions = "🔄 **Channel Linking Process**\n\n"
    instructions += "Please follow these steps:\n\n"
    instructions += "1️⃣ **First, send me your public (main) channel username or ID**\n"
    instructions += "This is the channel where the invite link message will be updated.\n\n"
    instructions += "You can:\n"
    instructions += "• Forward a message from the channel\n"
    instructions += "• Send the channel username (e.g., @mychannel)\n"
    instructions += "• Send the channel ID (e.g., -1001234567890)\n"
    instructions += "• Send a message link (e.g., https://t.me/channelname/123)\n\n"
    instructions += "Make sure I'm an admin in this channel with 'Edit Messages' permission."
    
    await message.reply(instructions)

# Remove command handler
async def remove_command(client: Client, message: Message):
    """Handle /remove command"""
    user_id = message.from_user.id
    
    # Get user's linked channels
    channels = await get_user_linked_channels(user_id)
    
    if not channels:
        await message.reply("❌ You don't have any linked channels yet. Use /add to link channels.")
        return
    
    # Set user state to waiting for channel selection
    user_states[user_id] = {
        "state": "waiting_remove_selection",
        "data": {"channels": channels}
    }
    
    # Create message with channel list
    response = "🗑 **Remove Linked Channels**\n\n"
    response += "Please send the number of the channel pair you want to remove:\n\n"
    
    for i, channel in enumerate(channels, 1):
        main_channel_id = channel["main_channel_id"]
        private_channel_id = channel["private_channel_id"]
        
        # Try to get channel names
        try:
            main_channel = await client.get_chat(main_channel_id)
            private_channel = await client.get_chat(private_channel_id)
            
            main_name = main_channel.title or f"Channel {main_channel_id}"
            private_name = private_channel.title or f"Channel {private_channel_id}"
            
            response += f"**{i}.** Public: {main_name} | Private: {private_name}\n"
        except Exception:
            # Fallback to IDs if names can't be retrieved
            response += f"**{i}.** Public: {main_channel_id} | Private: {private_channel_id}\n"
    
    response += "\nOr send /cancel to abort."
    
    await message.reply(response)

# Status command handler
async def status_command(client: Client, message: Message):
    """Handle /status command"""
    user_id = message.from_user.id
    
    # Get user's linked channels
    channels = await get_user_linked_channels(user_id)
    
    if not channels:
        await message.reply("❌ You don't have any linked channels yet. Use /add to link channels.")
        return
    
    # Create message with channel status
    response = "📊 **Your Linked Channels Status**\n\n"
    
    for i, channel in enumerate(channels, 1):
        main_channel_id = channel["main_channel_id"]
        private_channel_id = channel["private_channel_id"]
        message_id = channel["message_id"]
        last_update = channel.get("last_update_time")
        next_update = channel.get("next_update_time")
        
        # Try to get channel names
        try:
            main_channel = await client.get_chat(main_channel_id)
            private_channel = await client.get_chat(private_channel_id)
            
            main_name = main_channel.title or f"Channel {main_channel_id}"
            private_name = private_channel.title or f"Channel {private_channel_id}"
            
            response += f"**{i}. Channel Pair:**\n"
            response += f"📢 **Public:** {main_name}\n"
            response += f"🔒 **Private:** {private_name}\n"
            response += f"📝 **Message ID:** {message_id}\n"
            
            if last_update:
                response += f"🕒 **Last Update:** {last_update.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            
            if next_update:
                response += f"⏰ **Next Update:** {next_update.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            
            response += "\n"
        except Exception as e:
            # Fallback to IDs if names can't be retrieved
            response += f"**{i}. Channel Pair:**\n"
            response += f"📢 **Public:** {main_channel_id}\n"
            response += f"🔒 **Private:** {private_channel_id}\n"
            response += f"📝 **Message ID:** {message_id}\n"
            
            if last_update:
                response += f"🕒 **Last Update:** {last_update.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            
            if next_update:
                response += f"⏰ **Next Update:** {next_update.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            
            response += "\n"
    
    # Add refresh button
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Refresh Now", callback_data="refresh_all")
            ]
        ]
    )
    
    await message.reply(response, reply_markup=keyboard)

# Handle conversation states
async def handle_conversation(client: Client, message: Message):
    """Handle conversation states for multi-step commands"""
    user_id = message.from_user.id
    
    # Check if user has an active state
    if user_id not in user_states:
        # No active state, ignore message
        return
    
    state = user_states[user_id]["state"]
    data = user_states[user_id]["data"]
    
    logger.debug(f"Handling conversation for user {user_id} in state {state}")
    
    # Handle cancel command
    if message.text and message.text.lower() == "/cancel":
        del user_states[user_id]
        await message.reply("❌ Operation cancelled.")
        return
    
    try:
        # Handle different states
        if state == "waiting_main_channel":
            await handle_main_channel_input(client, message, user_id, data)
        
        elif state == "waiting_private_channel":
            await handle_private_channel_input(client, message, user_id, data)
        
        elif state == "waiting_message_id":
            await handle_message_id_input(client, message, user_id, data)
        
        elif state == "waiting_remove_selection":
            await handle_remove_selection(client, message, user_id, data)
        else:
            logger.warning(f"Unknown state {state} for user {user_id}")
            del user_states[user_id]
            await message.reply("❌ An error occurred with your current operation. Please try again.")
    except Exception as e:
        logger.error(f"Error in conversation handler for user {user_id}: {e}")
        await message.reply(
            "❌ An error occurred while processing your request. Please try again.\n\n"
            "If the error persists, try using the /cancel command and start over."
        )

# Handle main channel input
async def handle_main_channel_input(client: Client, message: Message, user_id, data):
    """Handle main channel input from user"""
    # Try to extract channel ID from message
    channel_id = None
    
    # Check if message is forwarded from a channel
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        channel_id = message.forward_from_chat.id
        logger.info(f"Extracted channel ID {channel_id} from forwarded message")
    
    # Check if message contains a channel username or ID
    elif message.text:
        # Use the new helper function to resolve channel ID
        from utils import resolve_channel_id
        channel_id = await resolve_channel_id(client, message.text.strip())

    
    # If channel ID couldn't be extracted
    if not channel_id:
        await message.reply(
            "❌ I couldn't identify a channel from your message.\n\n"
            "Please try one of these methods:\n"
            "1. Forward a message from the channel\n"
            "2. Send the channel username (e.g., @mychannel)\n"
            "3. Send the channel ID (e.g., -1001234567890)\n\n"
            "Make sure the bot is already added to the channel.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Check if user is admin in the channel
    is_admin = await is_user_admin(client, user_id, channel_id)
    
    if not is_admin:
        await message.reply(
            "❌ You are not an admin in this channel.\n\n"
            "Please make sure you are an admin in the channel and try again.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Check if bot is admin in the channel with required permissions
    is_bot_admin = await is_bot_admin_with_permissions(client, channel_id)
    
    if not is_bot_admin:
        await message.reply(
            "❌ I am not an admin in this channel or don't have the required permissions.\n\n"
            "Please add me as an admin with 'Edit Messages' permission and try again.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Store main channel ID and move to next state
    data["main_channel_id"] = channel_id
    user_states[user_id]["state"] = "waiting_private_channel"
    
    # Try to get channel name
    try:
        chat = await client.get_chat(channel_id)
        channel_name = chat.title or f"Channel {channel_id}"
    except Exception:
        channel_name = f"Channel {channel_id}"
    
    await message.reply(
        f"✅ Public channel set: **{channel_name}**\n\n"
        f"2️⃣ Now, send me your private channel username or ID.\n\n"
        f"This is the channel whose invite link will be refreshed.\n\n"
        f"**For private channels without username:**\n"
        f"1. Add @missrose_bot as an admin to your private channel\n"
        f"2. Forward any message from the private channel to @missrose_bot\n"
        f"3. Reply to that forwarded message with /id\n"
        f"4. Copy the ID (starts with -100) and send it to me\n\n"
        f"Make sure I'm an admin in this channel with 'Invite Users' permission.\n\n"
        f"Send /cancel to abort."
    )

# Handle private channel input
async def handle_private_channel_input(client: Client, message: Message, user_id, data):
    """Handle private channel input from user"""
    # Try to extract channel ID from message
    channel_id = None
    
    # Check if message is forwarded from a channel
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        channel_id = message.forward_from_chat.id
        logger.info(f"Extracted private channel ID {channel_id} from forwarded message")
    
    # Check if message contains a channel username, ID, or link
    elif message.text:
        # Use the new helper function to resolve channel ID
        from utils import resolve_channel_id
        channel_id = await resolve_channel_id(client, message.text.strip())
        if channel_id:
            logger.info(f"Successfully resolved private channel ID: {channel_id}")
    
    # If channel ID couldn't be extracted
    if not channel_id:
        await message.reply(
            "❌ I couldn't identify a channel from your message.\n\n"
            "**For private channels without username:**\n"
            "1. Add @missrose_bot as an admin to your private channel\n"
            "2. Forward any message from the private channel to @missrose_bot\n"
            "3. Reply to that forwarded message with /id\n"
            "4. Copy the ID (starts with -100) and send it to me\n\n"
            "Make sure the bot is already added to the channel.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Check if user is admin in the channel
    is_admin = await is_user_admin(client, user_id, channel_id)
    
    if not is_admin:
        await message.reply(
            "❌ You are not an admin in this channel.\n\n"
            "Please make sure you are an admin in the channel and try again.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Check if bot is admin in the channel with required permissions
    is_bot_admin = await is_bot_admin_with_permissions(client, channel_id)
    
    if not is_bot_admin:
        await message.reply(
            "❌ I am not an admin in this channel or don't have the required permissions.\n\n"
            "Please add me as an admin with 'Invite Users' permission and try again.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Store private channel ID and move to next state
    data["private_channel_id"] = channel_id
    user_states[user_id]["state"] = "waiting_message_id"
    
    # Try to get channel name
    try:
        chat = await client.get_chat(channel_id)
        channel_name = chat.title or f"Channel {channel_id}"
    except Exception:
        channel_name = f"Channel {channel_id}"
    
    await message.reply(
        f"✅ Private channel set: **{channel_name}**\n\n"
        f"3️⃣ Finally, send me the message ID in your public channel where the invite link should be updated.\n\n"
        f"This should be a number like '123'. You can get this by forwarding the message to @getidsbot.\n\n"
        f"Send /cancel to abort."
    )

# Handle message ID input
async def handle_message_id_input(client: Client, message: Message, user_id, data):
    """Handle message ID input from user"""
    # Try to extract message ID from text
    message_id = None
    main_channel_id = data["main_channel_id"]
    private_channel_id = data["private_channel_id"]
    
    # Check if it's a message link
    if message.text and "t.me/" in message.text:
        try:
            # Handle message links like https://t.me/channelname/123
            parts = message.text.split("t.me/")
            if len(parts) > 1:
                path_parts = parts[1].split("/")
                
                # Make sure there's a message ID at the end
                if len(path_parts) >= 2 and path_parts[-1].isdigit():
                    message_id = int(path_parts[-1])
                    
                    # Verify the channel in the link matches the main channel
                    channel_part = path_parts[0]
                    
                    # If it's a private channel link (t.me/c/123456789/123)
                    if channel_part == "c" and len(path_parts) >= 3:
                        # Skip verification for private channels as IDs might be formatted differently
                        pass
                    # For public channels, verify username matches
                    else:
                        try:
                            link_channel_id = await resolve_channel_id(client, f"@{channel_part}")
                            if link_channel_id and link_channel_id != main_channel_id:
                                await message.reply(
                                    "⚠️ The channel in the message link doesn't match your selected public channel.\n\n"
                                    "Please make sure you're sending a message link from the correct channel.\n\n"
                                    "Send /cancel to abort."
                                )
                                return
                        except Exception:
                            # If verification fails, continue with the message ID
                            pass
        except Exception as e:
            logger.error(f"Error parsing message link: {e}")
    
    # If not a valid message link, check if it's a direct message ID
    if message_id is None and message.text and message.text.strip().isdigit():
        message_id = int(message.text.strip())
    
    # If we still don't have a message ID
    if message_id is None:
        await message.reply(
            "❌ Please send a valid message ID or message link.\n\n"
            "You can either:\n"
            "1. Send just the message ID number\n"
            "2. Send the full message link (e.g., https://t.me/channelname/123)\n\n"
            "You can get the message ID by forwarding the message to @getidsbot.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Try to get the message to verify it exists
    try:
        await client.get_messages(main_channel_id, message_id)
    except Exception:
        await message.reply(
            "❌ I couldn't find that message in the public channel.\n\n"
            "Please make sure the message ID is correct and try again.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Add linked channels to database
    success = await add_linked_channels(user_id, main_channel_id, private_channel_id, message_id)
    
    if not success:
        await message.reply(
            "❌ There was an error linking your channels. Please try again later."
        )
        del user_states[user_id]
        return
    
    # Clear user state
    del user_states[user_id]
    
    # Try to get channel names
    try:
        main_chat = await client.get_chat(main_channel_id)
        private_chat = await client.get_chat(private_channel_id)
        
        main_name = main_chat.title or f"Channel {main_channel_id}"
        private_name = private_chat.title or f"Channel {private_channel_id}"
    except Exception:
        main_name = f"Channel {main_channel_id}"
        private_name = f"Channel {private_channel_id}"
    
    # Send success message
    success_message = f"✅ **Channels successfully linked!**\n\n"
    success_message += f"📢 **Public Channel:** {main_name}\n"
    success_message += f"🔒 **Private Channel:** {private_name}\n"
    success_message += f"📝 **Message ID:** {message_id}\n\n"
    success_message += f"The invite link will be updated every 6 hours automatically.\n\n"
    success_message += f"Use /status to check the status of your linked channels."
    
    # Create keyboard with update now button
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Update Now", callback_data=f"update_{main_channel_id}")
            ]
        ]
    )
    
    await message.reply(success_message, reply_markup=keyboard)
    
    # Trigger first update
    await update_channel_invite_link(client, user_id, main_channel_id, private_channel_id, message_id)

# Handle remove selection
async def handle_remove_selection(client: Client, message: Message, user_id, data):
    """Handle channel removal selection"""
    # Check if input is a valid number
    if not message.text or not message.text.strip().isdigit():
        await message.reply(
            "❌ Please send a valid number from the list.\n\n"
            "Send /cancel to abort."
        )
        return
    
    selection = int(message.text.strip())
    channels = data["channels"]
    
    # Check if selection is valid
    if selection < 1 or selection > len(channels):
        await message.reply(
            f"❌ Please send a number between 1 and {len(channels)}.\n\n"
            "Send /cancel to abort."
        )
        return
    
    # Get selected channel
    selected_channel = channels[selection - 1]
    main_channel_id = selected_channel["main_channel_id"]
    private_channel_id = selected_channel["private_channel_id"]
    
    # Remove linked channels from database
    success = await remove_linked_channels(user_id, main_channel_id)
    
    # Clear user state
    del user_states[user_id]
    
    if not success:
        await message.reply(
            "❌ There was an error removing your linked channels. Please try again later."
        )
        return
    
    # Try to get channel names
    try:
        main_chat = await client.get_chat(main_channel_id)
        private_chat = await client.get_chat(private_channel_id)
        
        main_name = main_chat.title or f"Channel {main_channel_id}"
        private_name = private_chat.title or f"Channel {private_channel_id}"
    except Exception:
        main_name = f"Channel {main_channel_id}"
        private_name = f"Channel {private_channel_id}"
    
    # Send success message
    success_message = f"✅ **Channels successfully unlinked!**\n\n"
    success_message += f"📢 **Public Channel:** {main_name}\n"
    success_message += f"🔒 **Private Channel:** {private_name}\n\n"
    success_message += f"The invite link will no longer be updated.\n\n"
    success_message += f"Use /add to link new channels."
    
    await message.reply(success_message)