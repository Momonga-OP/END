# END Bot - Discord Defense Alert System

END Bot (formerly Start2000) is a Discord bot designed to manage guild defense alerts for gaming communities. It provides a robust alert system with cooldowns, statistics tracking, and a user-friendly interface.

## Features

- **Alert Panel**: Interactive panel for triggering guild defense alerts
- **Cooldown System**: Prevents spam by implementing cooldowns between alerts
- **Statistics Tracking**: Tracks alert usage and member activity
- **Database Integration**: Stores guild information and alert history
- **Customizable**: Easy configuration through environment variables
- **Multi-environment Support**: Works with both PostgreSQL (production) and SQLite (development)

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- PostgreSQL database (for production) or SQLite (for development)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/END-bot.git
   cd END-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your Discord bot token and other configuration values

4. Run the bot:
   ```bash
   python main.py
   ```

## Deployment on Vercel

1. Create a Vercel account if you don't have one
2. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

3. Initialize Vercel project:
   ```bash
   vercel
   ```

4. Set up environment variables in Vercel:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `DEV_MODE`: Set to "False"
   - Other configuration variables as needed

5. Deploy to Vercel:
   ```bash
   vercel --prod
   ```

## Commands

### User Commands

- `!help` - Display help information
- `!alerte_guild <guild_name>` - Send an alert for a specific guild
- `/alert` - Generate an alert report
- `/stats [guild_name]` - Show alert statistics

### Admin Commands

- `/set_alerts_channel` - Set the channel for alerts

## Database Structure

- **guilds**: Stores guild information (name, emoji, role ID)
- **ping_history**: Records alert history
- **settings**: Stores bot configuration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Original development by Momonga-OP
- Discord.py library and community