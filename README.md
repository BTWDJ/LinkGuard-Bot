# Link Guard Robot

A Telegram bot that automatically refreshes private channel invite links and updates them in a public channel message.

## Features

- 🔄 **Automatic Link Refresh**: Updates private channel invite links every 12 hours
- 🔐 **Security**: Revokes old links after creating new ones
- 📢 **Public Usage**: Any channel admin can use this bot for their channels
- 🛡️ **Permission Checks**: Ensures proper admin rights for both user and bot
- 📊 **Status Tracking**: View linked channels and next update times
- 🚀 **Performance**: Optimized for reliability and fast response time

## Commands

- `/start` - Welcome message and info
- `/help` - Instructions on how to use the bot
- `/add` - Start channel linking process
- `/remove` - Unlink previously linked channels
- `/status` - View currently linked channels and next update time

## Requirements

- Python 3.11+
- Pyrogram v2
- MongoDB Atlas account
- Telegram API credentials (API ID, API Hash, Bot Token)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/invitelinkguard-bot.git
cd invitelinkguard-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root directory with the following content:

```
# Pyrogram API credentials
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# MongoDB Atlas connection string
MONGODB_URI=your_mongodb_connection_string

# Optional: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO
```

Replace the placeholder values with your actual credentials:

- **API_ID** and **API_HASH**: Get these from [my.telegram.org](https://my.telegram.org)
- **BOT_TOKEN**: Get this from [@BotFather](https://t.me/BotFather) on Telegram
- **MONGODB_URI**: Your MongoDB Atlas connection string

### 4. Create Logs Directory

```bash
mkdir logs
```

### 5. Run the Bot

```bash
python bot.py
```

## Deploying on Replit

1. Create a new Replit project
2. Upload all the project files or clone from GitHub
3. Add the environment variables in the Replit Secrets tab:
   - Add each variable from the `.env` file as a separate secret
4. Install the dependencies by running `pip install -r requirements.txt` in the Shell
5. Click the Run button to start the bot

### Keeping the Bot Running on Replit

To keep your bot running 24/7 on Replit, you can use UptimeRobot to ping your Replit project URL every few minutes.

1. Create a simple HTTP endpoint in your bot (already included in the code)
2. Get your Replit project URL (should look like `https://your-project-name.your-username.repl.co`)
3. Sign up for [UptimeRobot](https://uptimerobot.com/) and add a new monitor to ping your Replit URL

## Bot Permissions

The bot requires the following permissions:

- In the public channel: `Edit Messages`
- In the private channel: `Invite Users`

## Usage

1. Add the bot as an admin to both your public and private channels with the required permissions
2. Start a private chat with the bot and use the `/add` command
3. Follow the instructions to link your channels
4. The bot will automatically update the invite link every 12 hours

## License

MIT