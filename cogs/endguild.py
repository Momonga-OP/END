import discord
from discord.ext import commands
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from typing import Optional
import logging
from .config import GUILD_ID, PING_DEF_CHANNEL_ID, ALERTE_DEF_CHANNEL_ID
from .views import GuildPingView
from database import add_ping_record, get_ping_history

# Set up logging
logger = logging.getLogger(__name__)

class EndGuildCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns = {}
        self.ping_history = defaultdict(list)
        self.member_counts = {}
        self.total_online_members = 0
        self.panel_message: Optional[discord.Message] = None
        
        # Start the panel update task
        self.panel_update_task = self.bot.loop.create_task(self.panel_update_loop())
        
        # Register event listeners
        self.bot.add_listener(self.on_member_update, 'on_member_update')
        self.bot.add_listener(self.on_presence_update, 'on_presence_update')
        
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        if self.panel_update_task:
            self.panel_update_task.cancel()
            
    async def ensure_panel(self):
        """Ensure that we have a valid panel message."""
        try:
            # Get the alert channel
            channel = self.bot.get_channel(ALERTE_DEF_CHANNEL_ID)
            if not channel:
                logger.error(f"Could not find channel with ID: {ALERTE_DEF_CHANNEL_ID}")
                return
            
            # Find existing panel message if we don't have one
            if not self.panel_message:
                async for message in channel.history(limit=10):
                    if message.author == self.bot.user and message.embeds and len(message.embeds) > 0:
                        self.panel_message = message
                        logger.info("Found existing panel message")
                        break
        except Exception as e:
            logger.error(f"Error in ensure_panel: {e}")
    
    async def update_panel(self):
        """Update the panel with the latest information."""
        try:
            # Get the alert channel
            channel = self.bot.get_channel(ALERTE_DEF_CHANNEL_ID)
            if not channel:
                logger.error(f"Could not find channel with ID: {ALERTE_DEF_CHANNEL_ID}")
                return
            
            # Ensure we have a panel message
            await self.ensure_panel()
            
            # Create the panel embed and view
            embed = await self.create_panel_embed()
            view = GuildPingView(self)
            
            # Update or create the panel message
            if self.panel_message:
                try:
                    await self.panel_message.edit(embed=embed, view=view)
                    logger.debug("Updated existing panel message")
                except discord.NotFound:
                    logger.warning("Panel message not found, creating new one")
                    self.panel_message = None
                    await self.ensure_panel()
                    # Try again with a new message
                    self.panel_message = await channel.send(embed=embed, view=view)
                except Exception as e:
                    logger.error(f"Error updating panel: {e}")
            else:
                try:
                    self.panel_message = await channel.send(embed=embed, view=view)
                    logger.info("Created new panel message")
                except Exception as e:
                    logger.error(f"Error creating panel: {e}")
        except Exception as e:
            logger.error(f"Error in update_panel: {e}")
    
    async def panel_update_loop(self):
        """Background task that updates the panel periodically."""
        await self.bot.wait_until_ready()
        
        try:
            # Wait a bit for the bot to fully initialize
            await asyncio.sleep(5)
            
            while not self.bot.is_closed():
                try:
                    # Update member counts
                    await self.update_member_counts()
                    
                    # Update the panel
                    await self.update_panel()
                    
                except Exception as e:
                    logger.error(f"Error in panel update loop: {e}")
                
                # Update every 60 seconds
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except Exception as e:
            logger.error(f"Unexpected error in panel update loop: {e}")
            # Restart the task if it fails
            self.panel_update_task = self.bot.loop.create_task(self.panel_update_loop())

    @staticmethod
    def create_progress_bar(percentage: float, length: int = 10) -> str:
        """Create a visual progress bar."""
        filled = '▰' * int(round(percentage * length))
        empty = '▱' * (length - len(filled))
        return f"{filled}{empty} {int(percentage * 100)}%"

    async def update_member_counts(self):
        """Update the count of connected members for each guild."""
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            try:
                # Force fetch all members and their presences
                await guild.chunk(cache=True)
                
                # Initialize member counts dictionary if not exists
                if not hasattr(self, 'member_counts') or not self.member_counts:
                    self.member_counts = {}
                
                # Get guild data from config
                from .config import GUILD_EMOJIS_ROLES, load_guild_data_from_db
                load_guild_data_from_db()  # Refresh guild data
                
                # Track total online members
                self.total_online_members = 0
                
                # Track guild-specific counts based on roles from database
                for guild_name, guild_data in GUILD_EMOJIS_ROLES.items():
                    role_id = guild_data.get('role_id')
                    if role_id:
                        role = guild.get_role(role_id)
                        if role:
                            online_count = sum(1 for m in role.members 
                                             if not m.bot and hasattr(m, 'status') 
                                             and str(m.status) != 'offline')
                            
                            # Store the count for this guild
                            self.member_counts[guild_name] = online_count
                            
                            # Add to total online count
                            self.total_online_members += online_count
                        else:
                            logger.warning(f"Role with ID {role_id} for guild {guild_name} not found")
                            self.member_counts[guild_name] = 0
                
                logger.debug(f"Updated member counts: {self.member_counts}")
                logger.debug(f"Total online members: {self.total_online_members}")
            except Exception as e:
                logger.error(f"Error updating member counts: {e}")

    def add_ping_record_local(self, guild_name: str, author_id: int):
        """Add a ping record to local cache and database."""
        timestamp = datetime.now()
        
        # Add to local cache for immediate use
        self.ping_history[guild_name].append({
            'author_id': author_id,
            'timestamp': timestamp
        })
        
        # Trim local cache to last 100 entries
        self.ping_history[guild_name] = [
            ping for ping in self.ping_history[guild_name] 
            if ping['timestamp'] > datetime.now() - timedelta(days=7)
        ][-100:]
        
        # Add to database for persistence
        add_ping_record(guild_name, str(author_id))

    def get_ping_stats(self, guild_name: str) -> dict:
        """Get statistics about pings for a guild."""
        now = datetime.now()
        periods = {
            '24h': now - timedelta(hours=24),
            '7j': now - timedelta(days=7)
        }

        stats = {'member_count': self.member_counts.get(guild_name, 0)}
        
        # Get stats from local cache
        for period, cutoff in periods.items():
            pings = [p for p in self.ping_history[guild_name] if p['timestamp'] > cutoff]
            stats.update({
                f'total_{period}': len(pings),
                f'unique_{period}': len({p['author_id'] for p in pings}),
                f'activite_{period}': min(100, len(pings) * 2)
            })
        
        return stats

    async def create_panel_embed(self) -> discord.Embed:
        """Create the embed for the alert panel."""
        
        # Use a dark blue color for the END theme
        embed = discord.Embed(
            title="⚔️ Panneau d'Alerte END",
            color=discord.Color.from_rgb(21, 26, 35),  # Dark blue theme
            timestamp=datetime.now()
        )
        
        # Update the icon URL to a more modern icon
        embed.set_author(
            name="Système d'Alerte END",
            icon_url="https://i.imgur.com/6YToyEF.png"  # END logo
        )
        
        # Add a thumbnail for better visual appeal
        embed.set_thumbnail(url="https://i.imgur.com/JzDnCGU.png")  # Shield icon
        
        # Current date and time
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        # Compact description optimized for mobile
        embed.description = (
            "```ini\n[END v3.0.0]\n```\n"
            f"**📅 Date:** `{current_date}`\n"
            "**Instructions:**\n"
            "1️⃣ Sélectionnez votre guilde\n"
            "2️⃣ Alertes dans <#1264140175395655712>"
        )

        # Add a compact divider for better section separation on mobile
        embed.add_field(name="⎯⎯⎯⎯⎯⎯⎯⎯", value="", inline=False)
        
        # Get all guilds from config
        from .config import GUILD_EMOJIS_ROLES
        
        # Create a list of all guilds with their alert stats
        guild_list = []
        for guild_name in GUILD_EMOJIS_ROLES.keys():
            stats = self.get_ping_stats(guild_name)
            guild_data = GUILD_EMOJIS_ROLES.get(guild_name, {})
            guild_emoji = guild_data.get("emoji", "🛡️")  # Default to shield emoji if not found
            
            guild_list.append({
                "name": guild_name,
                "emoji": guild_emoji,
                "alerts_24h": stats['total_24h']
            })
        
        # Sort guilds by name (alphabetically) instead of by member count
        sorted_guilds = sorted(guild_list, key=lambda x: x["name"])
        
        # Limit to 10 guilds (which will create 20 fields with the spacers)
        displayed_guilds = 0
        max_guilds = 10
        
        for guild_data in sorted_guilds:
            # Stop if we've reached the maximum number of guilds to display
            if displayed_guilds >= max_guilds:
                break
                
            # Simplified, phone-friendly styling - removed member count
            valeur = (
                f"```yml\n"
                f"🔹 {guild_data['alerts_24h']} alertes aujourd'hui\n```"
            )
            
            # Make fields display in a more phone-friendly way (2 columns instead of 3)
            embed.add_field(
                name=f"{guild_data['emoji']} {guild_data['name']}",  # Show emoji and guild name
                value=valeur,
                inline=True
            )
            
            displayed_guilds += 1
            
            # Add a blank field after every 2 guilds to force 2-column layout on mobile
            if displayed_guilds % 2 == 0 and displayed_guilds < max_guilds:
                embed.add_field(name="​", value="​", inline=True)
        
        return embed

    async def ensure_panel(self):
        """Ensure that we have a valid panel message."""
        try:
            # Get the alert channel
            channel = self.bot.get_channel(ALERTE_DEF_CHANNEL_ID)
            if not channel:
                logger.error(f"Could not find channel with ID: {ALERTE_DEF_CHANNEL_ID}")
                return
            
            # Find existing panel message if we don't have one
            if not self.panel_message:
                try:
                    async for message in channel.history(limit=10):
                        if message.author == self.bot.user and message.embeds and len(message.embeds) > 0:
                            self.panel_message = message
                            logger.info("Found existing panel message")
                            break
                except Exception as e:
                    logger.error(f"Error searching for panel message: {e}")
        except Exception as e:
            logger.error(f"Error in ensure_panel: {e}")
            
    async def update_panel(self):
        """Update the panel with the latest information."""
        try:
            # Get the alert channel
            channel = self.bot.get_channel(ALERTE_DEF_CHANNEL_ID)
            if not channel:
                logger.error(f"Could not find channel with ID: {ALERTE_DEF_CHANNEL_ID}")
                return
            
            # Ensure we have a panel message
            await self.ensure_panel()
            
            # Create the panel embed and view
            embed = await self.create_panel_embed()
            view = GuildPingView(self)
            
            # Update or create the panel message
            if self.panel_message:
                try:
                    await self.panel_message.edit(embed=embed, view=view)
                    logger.debug("Updated existing panel message")
                except discord.NotFound:
                    logger.warning("Panel message not found, creating new one")
                    self.panel_message = None
                    # Try again with a new message
                    self.panel_message = await channel.send(embed=embed, view=view)
                    logger.info("Created new panel message")
                except Exception as e:
                    logger.error(f"Error updating panel: {e}")
            else:
                try:
                    self.panel_message = await channel.send(embed=embed, view=view)
                    logger.info("Created new panel message")
                except Exception as e:
                    logger.error(f"Error creating panel: {e}")
        except Exception as e:
            logger.error(f"Error in update_panel: {e}")

    async def on_member_update(self, before, after):
        """Handle member updates to refresh the panel."""
        # Only process if the update is in the main guild
        if after.guild.id == GUILD_ID:
            # Check if roles changed
            if before.roles != after.roles:
                logger.debug(f"Member {after.name} roles changed, updating panel")
                await self.update_member_counts()
                await self.update_panel()
    
    async def on_presence_update(self, before, after):
        """Handle presence updates to refresh the panel."""
        # Only process if the update is in the main guild
        if after.guild.id == GUILD_ID:
            # Check if status changed (online/offline/idle/dnd)
            if before.status != after.status:
                logger.debug(f"Member {after.name} status changed from {before.status} to {after.status}")
                await self.update_member_counts()
                await self.update_panel()
    
    async def panel_update_loop(self):
        """Loop to update the panel message periodically."""
        await self.bot.wait_until_ready()
        
        try:
            # Wait longer for the bot to fully initialize
            logger.info("Panel update loop starting - waiting 60 seconds before first update")
            await asyncio.sleep(60)  # Wait a full minute before first update
            
            # Track last successful update time
            last_update_time = datetime.now()
            update_interval = timedelta(hours=1)  # Update only once per hour
            
            while not self.bot.is_closed():
                try:
                    current_time = datetime.now()
                    
                    # Only update the panel if enough time has passed since last update
                    if current_time - last_update_time >= update_interval:
                        logger.info(f"Scheduled panel update at {current_time}")
                        
                        # Ensure we have the panel message
                        await self.ensure_panel()
                        
                        # Update the panel
                        await self.update_panel()
                        last_update_time = current_time
                        logger.info(f"Panel updated successfully at {current_time}")
                        
                        # Wait a bit after updating to avoid rate limits
                        await asyncio.sleep(30)
                    
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limit error
                        retry_after = e.retry_after if hasattr(e, 'retry_after') else 300
                        logger.warning(f"Rate limited. Waiting {retry_after} seconds before next update attempt")
                        # Increase the update interval temporarily
                        update_interval = max(update_interval, timedelta(hours=2))
                        await asyncio.sleep(retry_after)
                    else:
                        logger.error(f"HTTP error in panel update loop: {e}")
                        await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Error in panel update loop: {e}")
                    await asyncio.sleep(60)
                
                # Check every 5 minutes
                await asyncio.sleep(300)
                
        except asyncio.CancelledError:
            logger.info("Panel update loop was cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in panel update loop: {e}")
            # Restart the task if it fails
            self.panel_update_task = self.bot.loop.create_task(self.panel_update_loop())

    async def handle_ping(self, guild_name):
        """Handle cooldown for guild pings."""
        now = datetime.now().timestamp()
        if guild_name in self.cooldowns:
            if now < self.cooldowns[guild_name]:
                return self.cooldowns[guild_name] - now
            del self.cooldowns[guild_name]
        
        self.cooldowns[guild_name] = now + 15  # 15 seconds cooldown
        return True

    @commands.command(name="alerte_guild")
    async def ping_guild(self, ctx, guild_name: str):
        """Command to ping a guild for defense."""
        cooldown = await self.handle_ping(guild_name)
        if isinstance(cooldown, float):
            embed = discord.Embed(
                title="⏳ Temporisation Active",
                description=f"Veuillez patienter {cooldown:.1f}s avant une nouvelle alerte pour {guild_name}",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        self.add_ping_record_local(guild_name, ctx.author.id)
        await self.ensure_panel()

        stats = self.get_ping_stats(guild_name)
        reponse = discord.Embed(
            title=f"🚨 Alerte {guild_name} Activée",
            description=f"🔔 {self.member_counts.get(guild_name, 0)} membres disponibles",
            color=discord.Color.green()
        )
        reponse.add_field(
            name="Détails",
            value=f"**Initiateur:** {ctx.author.mention}\n"
                  f"**Canal:** {ctx.channel.mention}\n"
                  f"**Priorité:** `Urgente`",
            inline=False
        )
        reponse.add_field(
            name="Statistiques",
            value=f"```diff\n+ Pings 24h: {stats['total_24h']}\n"
                  f"+ Uniques: {stats['unique_24h']}\n"
                  f"- Prochaine alerte possible dans: 15s```",
            inline=False
        )
        
        await ctx.send(embed=reponse)
        await self.send_alert_log(guild_name, ctx.author)

    async def send_alert_log(self, guild_name: str, author: discord.Member):
        """Send an alert log to the alert channel."""
        guild = self.bot.get_guild(GUILD_ID)
        channel = guild.get_channel(ALERTE_DEF_CHANNEL_ID)
        
        if not channel:
            logger.warning("Alert channel not found")
            return
            
        embed = discord.Embed(
            title=f"🚨 Alerte {guild_name}",
            description=f"Une alerte a été déclenchée par {author.mention}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Détails",
            value=f"**Guilde:** {guild_name}\n"
                  f"**Initiateur:** {author.mention}\n"
                  f"**Membres disponibles:** {self.member_counts.get(guild_name, 0)}",
            inline=False
        )
        
        embed.set_footer(text=f"ID: {author.id}")
        
        try:
            await channel.send(embed=embed)
            logger.info(f"Sent alert log for {guild_name}")
        except Exception as e:
            logger.error(f"Error sending alert log: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Event triggered when the bot is ready."""
        logger.info("EndGuildCog is ready")
        # Load ping history from database
        try:
            # This would be implemented to load ping history from database
            # For now, we'll just initialize the panel
            await self.ensure_panel()
        except Exception as e:
            logger.error(f"Error in on_ready: {e}")

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(EndGuildCog(bot))
