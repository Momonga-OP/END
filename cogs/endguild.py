import discord
from discord.ext import commands
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from typing import Optional
import logging
from .config import GUILD_ID
from .views import GuildPingView
from database import add_ping_record, get_ping_history

# Channel IDs
PING_DEF_CHANNEL_ID = 1369382571363930174
ALERTE_DEF_CHANNEL_ID = 1264140175395655712

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
        self.last_presence_update = datetime.now()
        self.presence_update_cooldown = 600  # 10 minutes in seconds
        self.last_member_update = datetime.now()
        self.member_update_cooldown = 600  # 10 minutes in seconds
        
        # Start the panel update task after bot is ready
        self.panel_update_task = None
        
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
            channel = self.bot.get_channel(PING_DEF_CHANNEL_ID)
            if not channel:
                logger.error(f"Could not find channel with ID: {PING_DEF_CHANNEL_ID}")
                return
            
            # Find existing panel message if we don't have one
            if not self.panel_message:
                async for message in channel.history(limit=10):
                    if message.author == self.bot.user and message.embeds and len(message.embeds) > 0:
                        # Check if it looks like our panel message
                        embed = message.embeds[0]
                        if "Panneau d'Alerte END" in str(embed.title):
                            self.panel_message = message
                            logger.info("Found existing panel message")
                            break
        except Exception as e:
            logger.error(f"Error in ensure_panel: {e}")
    
    async def update_panel(self):
        """Update the panel with the latest information."""
        try:
            # Get the alert channel
            channel = self.bot.get_channel(PING_DEF_CHANNEL_ID)
            if not channel:
                logger.error(f"Could not find channel with ID: {PING_DEF_CHANNEL_ID}")
                return
            
            # Ensure we have a panel message
            await self.ensure_panel()
            
            # Create the panel embed and view
            embed = await self.create_panel_embed()
            
            # Create view with error handling for emoji issues
            try:
                view = GuildPingView(self)
            except Exception as view_error:
                logger.error(f"Error creating view: {view_error}")
                # Create embed without view if view creation fails
                view = None
            
            # Update or create the panel message
            if self.panel_message:
                try:
                    if view:
                        await self.panel_message.edit(embed=embed, view=view)
                    else:
                        await self.panel_message.edit(embed=embed)
                    logger.debug("Updated existing panel message")
                except discord.NotFound:
                    logger.warning("Panel message not found, creating new one")
                    self.panel_message = None
                    # Try again with a new message
                    if view:
                        self.panel_message = await channel.send(embed=embed, view=view)
                    else:
                        self.panel_message = await channel.send(embed=embed)
                except discord.HTTPException as e:
                    logger.error(f"Discord HTTP error updating panel: {e}")
                    # Try without view if it's an emoji/component error
                    if "emoji" in str(e).lower() or "component" in str(e).lower():
                        try:
                            await self.panel_message.edit(embed=embed)
                            logger.info("Updated panel without view due to component error")
                        except Exception as fallback_error:
                            logger.error(f"Fallback update failed: {fallback_error}")
                except Exception as e:
                    logger.error(f"Error updating panel: {e}")
            else:
                try:
                    if view:
                        self.panel_message = await channel.send(embed=embed, view=view)
                    else:
                        self.panel_message = await channel.send(embed=embed)
                    logger.info("Created new panel message")
                except discord.HTTPException as e:
                    logger.error(f"Discord HTTP error creating panel: {e}")
                    # Try without view if it's an emoji/component error
                    if "emoji" in str(e).lower() or "component" in str(e).lower():
                        try:
                            self.panel_message = await channel.send(embed=embed)
                            logger.info("Created panel without view due to component error")
                        except Exception as fallback_error:
                            logger.error(f"Fallback creation failed: {fallback_error}")
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
            logger.info("Panel update task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in panel update loop: {e}")
            # Restart the task if it fails
            await asyncio.sleep(10)  # Wait before restarting
            if not self.bot.is_closed():
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
        if not guild:
            logger.warning(f"Guild with ID {GUILD_ID} not found")
            return
            
        try:
            # Force fetch all members and their presences
            await guild.chunk(cache=True)
            
            # Initialize member counts dictionary if not exists
            if not hasattr(self, 'member_counts') or not self.member_counts:
                self.member_counts = {}
            
            # Get guild data from config with error handling
            try:
                from .config import GUILD_EMOJIS_ROLES, load_guild_data_from_db
                load_guild_data_from_db()  # Refresh guild data
            except ImportError as e:
                logger.error(f"Import error: {e}")
                # Fallback: create empty guild data if import fails
                GUILD_EMOJIS_ROLES = {}
            except AttributeError as e:
                logger.error(f"Function not found: {e}")
                # Try alternative function name or use empty dict
                try:
                    from .config import GUILD_EMOJIS_ROLES
                except ImportError:
                    GUILD_EMOJIS_ROLES = {}
            
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
                else:
                    logger.warning(f"No role_id found for guild {guild_name}")
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
        
        # Add to database for persistence with error handling
        try:
            add_ping_record(guild_name, str(author_id))
        except Exception as e:
            logger.error(f"Error adding ping record to database: {e}")

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
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Compact description optimized for mobile
        embed.description = (
            "```ini\n[END v3.0.0]\n```\n"
            f"**👥 En ligne:** `{self.total_online_members}`  •  "
            f"**📅 Date:** `{current_date}`\n"
            f"**⚡ Statut:** {'`OPÉRATIONNEL`' if self.total_online_members > 0 else '`EN ATTENTE`'}\n\n"
            "**Instructions:**\n"
            "1️⃣ Sélectionnez votre guilde\n"
            f"2️⃣ Alertes dans <#{ALERTE_DEF_CHANNEL_ID}>"
        )

        # Add a compact divider for better section separation on mobile
        embed.add_field(name="⎯⎯⎯⎯⎯⎯⎯⎯", value="", inline=False)
        
        # Set compact footer with last update time
        embed.set_footer(text=f"END • Mise à jour: {current_time}")
        
        # Guild status fields with simplified styling - limit to 20 fields max (Discord limit is 25)
        # Sort guilds by online member count (descending)
        sorted_guilds = sorted(self.member_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Limit to 10 guilds (which will create 20 fields with the spacers)
        displayed_guilds = 0
        max_guilds = 10
        
        for guild_name, count in sorted_guilds:
            # Stop if we've reached the maximum number of guilds to display
            if displayed_guilds >= max_guilds:
                break
                
            stats = self.get_ping_stats(guild_name)
            
            # Simplified, phone-friendly styling
            valeur = (
                f"```yml\n"
                f"🔹 {count} membres en ligne\n"
                f"🔹 {stats['total_24h']} alertes aujourd'hui\n```"
            )
            
            # Get the guild's emoji from config with fallback
            try:
                from .config import GUILD_EMOJIS_ROLES
                guild_data = GUILD_EMOJIS_ROLES.get(guild_name, {})
                guild_emoji = guild_data.get("emoji", "🛡️")  # Default to shield emoji if not found
            except ImportError:
                guild_emoji = "🛡️"  # Fallback emoji
            
            # Make fields display in a more phone-friendly way (2 columns instead of 3)
            embed.add_field(
                name=f"{guild_emoji} {guild_name}",  # Show emoji and guild name
                value=valeur,
                inline=True
            )
            
            displayed_guilds += 1
            
            # Add a blank field after every 2 guilds to force 2-column layout on mobile
            if displayed_guilds % 2 == 0 and displayed_guilds < max_guilds:
                embed.add_field(name="​", value="​", inline=True)

        return embed

    async def handle_ping(self, guild_name):
        """Handle cooldown for guild pings."""
        now = datetime.now().timestamp()
        if guild_name in self.cooldowns:
            if now < self.cooldowns[guild_name]:
                return self.cooldowns[guild_name] - now
            del self.cooldowns[guild_name]
        
        self.cooldowns[guild_name] = now + 30  # 30 seconds cooldown
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
        await self.update_panel()  # Update panel after ping

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
                  f"- Prochaine alerte possible dans: 30s```",
            inline=False
        )
        
        await ctx.send(embed=reponse)
        await self.send_alert_log(guild_name, ctx.author)

    async def send_alert_log(self, guild_name: str, author: discord.Member):
        """Send an alert log to the alert channel."""
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning("Guild not found for alert log")
            return
            
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

    async def on_member_update(self, before, after):
        """Handle member updates to refresh the panel."""
        # Only process if the update is in the main guild
        if after.guild.id == GUILD_ID:
            # Check if roles changed
            if before.roles != after.roles:
                logger.debug(f"Member {after.name} roles changed, updating panel")
                
                # Only update if cooldown has passed
                now = datetime.now()
                if (now - self.last_member_update).total_seconds() >= self.member_update_cooldown:
                    logger.info(f"Updating panel due to role changes (cooldown passed)")
                    await self.update_member_counts()
                    await self.update_panel()
                    self.last_member_update = now
    
    async def on_presence_update(self, before, after):
        """Handle presence updates to refresh the panel."""
        # Only process if the update is in the main guild
        if after.guild.id == GUILD_ID:
            # Check if status changed (online/offline/idle/dnd)
            if before.status != after.status:
                logger.debug(f"Member {after.name} status changed from {before.status} to {after.status}")
                
                # Only update if cooldown has passed
                now = datetime.now()
                if (now - self.last_presence_update).total_seconds() >= self.presence_update_cooldown:
                    logger.info(f"Updating panel due to presence changes (cooldown passed)")
                    await self.update_member_counts()
                    await self.update_panel()
                    self.last_presence_update = now

    @commands.Cog.listener()
    async def on_ready(self):
        """Event triggered when the bot is ready."""
        logger.info("EndGuildCog is ready")
        
        # Start the panel update task now that bot is ready
        if not self.panel_update_task:
            self.panel_update_task = self.bot.loop.create_task(self.panel_update_loop())
            logger.info("Started panel update task")
        
        # Load ping history from database and initialize panel
        try:
            # Load ping history if function exists
            try:
                history = get_ping_history()
                if history:
                    for record in history:
                        guild_name = record.get('guild_name')
                        author_id = record.get('author_id')
                        timestamp = record.get('timestamp')
                        if guild_name and author_id and timestamp:
                            self.ping_history[guild_name].append({
                                'author_id': int(author_id),
                                'timestamp': timestamp
                            })
                    logger.info(f"Loaded {len(history)} ping records from database")
            except Exception as e:
                logger.warning(f"Could not load ping history: {e}")
            
            # Initialize the panel
            await self.update_member_counts()
            await self.ensure_panel()
            
        except Exception as e:
            logger.error(f"Error in on_ready: {e}")

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(EndGuildCog(bot))
