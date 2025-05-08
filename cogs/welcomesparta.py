import discord
from discord.ext import commands
import logging
from typing import Optional
from datetime import datetime
import asyncio

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class WelcomeConfig:
    """Configuration class to store all constants"""
    GUILD_ID = 1300093554064097400
    WELCOME_CHANNEL_ID = 1300093554399645707
    WELCOME_IMAGE_URL = "https://github.com/Momonga-OP/Start2000/blob/main/Alliance%20Start2000.png?raw=true"
    
    # Colors for embeds
    WELCOME_COLOR = discord.Color.blue()
    ERROR_COLOR = discord.Color.red()
    SUCCESS_COLOR = discord.Color.green()
    
    # Message templates
    WELCOME_MESSAGE = (
        "🎉 Bienvenue {member_mention} à Alliance Start ! 🎉\n"
        "Nous sommes ravis de vous accueillir ici ! N'oubliez pas de "
        "consulter nos salons et de profiter de votre séjour. 🎊"
    )

class WelcomeSparta(commands.Cog):
    """A cog for handling welcome messages and member joins"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = WelcomeConfig()
        self.last_error_time = {}  # Track error timestamps for rate limiting
        
    async def get_welcome_channel(self) -> Optional[discord.TextChannel]:
        """Get the welcome channel with error handling"""
        guild = self.bot.get_guild(self.config.GUILD_ID)
        if not guild:
            logger.error(f"Could not find guild with ID: {self.config.GUILD_ID}")
            return None
            
        channel = guild.get_channel(self.config.WELCOME_CHANNEL_ID)
        if not channel:
            logger.error(f"Could not find welcome channel with ID: {self.config.WELCOME_CHANNEL_ID}")
            return None
            
        return channel
        
    def create_welcome_embed(self, member: discord.Member) -> discord.Embed:
        """Create a welcome embed for new members"""
        embed = discord.Embed(
            description=self.config.WELCOME_MESSAGE.format(member_mention=member.mention),
            color=self.config.WELCOME_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_image(url=self.config.WELCOME_IMAGE_URL)
        embed.set_footer(text=f"Member #{len(member.guild.members)}")
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        return embed
        
    async def log_error(self, error_msg: str, error: Exception = None):
        """Rate-limited error logging to prevent spam"""
        current_time = datetime.utcnow()
        if error_msg in self.last_error_time:
            # Only log if more than 5 minutes have passed since the last similar error
            if (current_time - self.last_error_time[error_msg]).total_seconds() < 300:
                return
                
        self.last_error_time[error_msg] = current_time
        if error:
            logger.error(f"{error_msg}: {str(error)}")
        else:
            logger.error(error_msg)
            
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joins"""
        if member.guild.id != self.config.GUILD_ID:
            return
            
        logger.info(f"New member joined: {member.name} ({member.id}) in {member.guild.name}")
        
        welcome_channel = await self.get_welcome_channel()
        if not welcome_channel:
            return
            
        try:
            embed = self.create_welcome_embed(member)
            await welcome_channel.send(embed=embed)
            logger.info(f"Welcome message sent for {member.name}")
            
            # Optional: Send a private message to the new member
            try:
                await member.send(
                    f"Bienvenue sur {member.guild.name}! 🎉\n"
                    "N'hésitez pas à lire nos règles et à vous présenter!"
                )
            except discord.Forbidden:
                logger.info(f"Could not send DM to {member.name} - they might have DMs disabled")
                
        except discord.Forbidden:
            await self.log_error("Missing permissions to send welcome message")
        except discord.HTTPException as e:
            await self.log_error("Failed to send welcome message", e)
        except Exception as e:
            await self.log_error("Unexpected error in on_member_join", e)
            
    @commands.Cog.listener()
    async def on_ready(self):
        """Handle bot ready event"""
        logger.info("Welcome cog is ready!")
        await self.validate_configuration()
        
    async def validate_configuration(self):
        """Validate bot permissions and channel access on startup"""
        channel = await self.get_welcome_channel()
        if not channel:
            return
            
        # Check bot permissions
        permissions = channel.permissions_for(channel.guild.me)
        missing_perms = []
        
        required_perms = {
            'send_messages': 'Send Messages',
            'embed_links': 'Embed Links',
            'attach_files': 'Attach Files',
            'view_channel': 'View Channel'
        }
        
        for perm, name in required_perms.items():
            if not getattr(permissions, perm):
                missing_perms.append(name)
                
        if missing_perms:
            await self.log_error(
                f"Missing required permissions in {channel.name}: {', '.join(missing_perms)}"
            )
        else:
            logger.info(f"All required permissions verified in {channel.name}")
            
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx):
        """Test the welcome message (Admin only)"""
        try:
            embed = self.create_welcome_embed(ctx.author)
            await ctx.send("Testing welcome message:", embed=embed)
            logger.info(f"Welcome test performed by {ctx.author.name}")
        except Exception as e:
            await self.log_error("Error in test_welcome command", e)
            await ctx.send("An error occurred while testing the welcome message.")

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeSparta(bot))
    logger.info("WelcomeSparta cog loaded successfully.")
