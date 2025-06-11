import discord
from discord.ext import commands
import os
import asyncio
import logging
import sys
from dotenv import load_dotenv
from database import initialize_db
from cogs.config import load_guild_data_from_db

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('end_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('end_bot')

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True  # Required to see online/offline status

# Create the bot
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Constants
OWNER_ID = int(os.getenv('OWNER_ID', '486652069831376943'))
TOKEN = os.getenv('DISCORD_TOKEN')
VERSION = '3.0.0'

# Initialize the database
try:
    initialize_db()
    # Load guild data from database
    load_guild_data_from_db()
    load_guild_data_from_db_server2()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    logger.info(f'Logged in as {bot.user}')
    logger.info(f'END Bot v{VERSION} is online')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="les défenses de guilde | !help"
        ),
        status=discord.Status.online
    )
    
    # Sync slash commands
    await sync_commands()

async def sync_commands():
    """Sync slash commands with Discord."""
    if not hasattr(bot, 'synced'):
        try:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} commands")
            bot.synced = True
        except Exception as e:
            logger.exception("Failed to sync commands")

@bot.command(name='help')
async def help_command(ctx):
    """Display help information about the bot."""
    embed = discord.Embed(
        title="END Bot - Système d'Alerte Défense",
        description="Un bot pour gérer les alertes de défense de guilde",
        color=discord.Color.blue()
    )
    
    embed.set_author(
        name="END Bot",
        icon_url=bot.user.display_avatar.url
    )
    
    embed.add_field(
        name="Commandes Principales",
        value=(
            "`!alerte_guild <nom_guilde>` - Envoyer une alerte pour une guilde\n"
            "`/alert` - Générer un rapport d'alertes\n"
            "`/stats [guild_name]` - Afficher les statistiques d'alertes\n"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Commandes Admin",
        value=(
            "`/set_alerts_channel` - Définir le canal pour les alertes\n"
        ),
        inline=False
    )
    
    embed.set_footer(text=f"END Bot v{VERSION} | Développé par Momonga-OP")
    
    await ctx.send(embed=embed)

@bot.event
async def on_message(message: discord.Message):
    """Event triggered when a message is sent."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
        
    # Log messages (except in DMs for privacy)
    if not isinstance(message.channel, discord.DMChannel):
        logger.debug(f"Message from {message.author} in {message.channel}: {message.content[:50]}...")

    # Forward DMs to the bot owner
    if isinstance(message.channel, discord.DMChannel):
        await forward_dm(message)

    # Process commands
    await bot.process_commands(message)

async def forward_dm(message: discord.Message):
    """Forward DMs to the bot owner."""
    try:
        owner = await bot.fetch_user(OWNER_ID)
        if owner:
            embed = discord.Embed(
                title="Message Privé Reçu",
                description=message.content or "[Pas de contenu textuel]",
                color=discord.Color.blue(),
                timestamp=message.created_at
            )
            
            embed.set_author(
                name=f"{message.author.name} ({message.author.id})",
                icon_url=message.author.display_avatar.url
            )
            
            # Handle attachments
            if message.attachments:
                embed.add_field(
                    name="Pièces jointes",
                    value="\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
                )
                
                # Set the first image as the embed image if it's an image
                if message.attachments[0].content_type and 'image' in message.attachments[0].content_type:
                    embed.set_image(url=message.attachments[0].url)
            
            await owner.send(embed=embed)
    except Exception as e:
        logger.error(f"Error forwarding DM: {e}")

@bot.event
async def on_disconnect():
    """Event triggered when the bot disconnects."""
    logger.warning("Bot disconnected")

@bot.event
async def on_error(event: str, *args, **kwargs):
    """Event triggered when an error occurs."""
    logger.exception(f"An error occurred in event {event}")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Argument manquant: {error.param.name}. Utilisez `!help` pour plus d'informations.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Argument invalide. Utilisez `!help` pour plus d'informations.")
    else:
        logger.error(f"Command error in {ctx.command}: {error}")
        await ctx.send(f"Une erreur est survenue lors de l'exécution de la commande.")

@bot.event
async def on_close():
    """Event triggered when the bot is closing."""
    logger.info("Bot is closing")
    await close_sessions()

async def close_sessions():
    """Perform cleanup before closing the bot."""
    logger.info("Performing cleanup before closing...")

# List of extensions (cogs) to load
EXTENSIONS = [
    'cogs.admin',
    'cogs.relocate', 'cogs.watermark', 'cogs.talk',
    'cogs.watermark_user',
    'cogs.image_converter', 'cogs.endguild', 'cogs.clear',  # Updated to endguild
    'cogs.alerts',
    'cogs.super', 'cogs.translator', 'cogs.rules', 'cogs.write', 'cogs.dofustouch',
    'cogs.endguild_server2',  # Added for the second server
    # 'cogs.voice',  # Removed due to FFmpeg dependency exceeding Vercel size limits
]

async def load_extensions():
    """Load all extensions (cogs) listed in EXTENSIONS."""
    for extension in EXTENSIONS:
        try:
            await bot.load_extension(extension)
            logger.info(f"Loaded extension: {extension}")
        except Exception as e:
            logger.error(f"Failed to load extension {extension}: {e}")

async def main():
    """Main function to start the bot."""
    async with bot:
        # Load extensions
        await load_extensions()

        # Check if the bot token is available
        if not TOKEN:
            logger.error("Bot token not found. Please set the DISCORD_TOKEN environment variable.")
            return

        # Start the bot
        try:
            logger.info("Starting END Bot...")
            await bot.start(TOKEN)
        except discord.LoginFailure:
            logger.error("Invalid token. Please check your DISCORD_TOKEN environment variable.")
        except Exception as e:
            logger.exception("Failed to start the bot")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Bot encountered an error and stopped")
