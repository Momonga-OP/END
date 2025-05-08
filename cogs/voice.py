import discord
from discord.ext import commands
from gtts import gTTS
import os
import asyncio
import logging
from typing import Optional, Set, Dict
import random
import tempfile
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceConfig:
    """Configuration settings for voice features"""
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 5
    COOLDOWN_DURATION: int = 300  # 5 minutes cooldown
    DEFAULT_LANGUAGE: str = 'fr'
    VOLUME: float = 1.0
    DISCONNECT_DELAY: int = 3

    WELCOME_MESSAGES = [
        "Bonjour {name}! Ravi de vous avoir parmi nous.",
        "Bienvenue, {name}! Nous espérons que vous passerez un bon moment.",
        "Salut {name}! Content de vous voir parmi nous.",
        "Hey {name}! Bienvenue dans notre communauté.",
        "Bienvenus {name}! Nous sommes ravis de vous accueillir.",
    ]

    # Server-specific welcome messages
    SERVER_SPECIFIC_MESSAGES = {
        1296795292703784960: "Bonjour {name}, bienvenue sur {server}. Nous sommes ravis de vous accueillir!"
    }

class VoiceManager:
    """Manages voice-related functionality"""
    def __init__(self):
        self.active_connections: Dict[int, discord.VoiceClient] = {}
        self.user_cooldowns: Dict[int, datetime] = {}

    def is_user_on_cooldown(self, user_id: int) -> bool:
        """Check if a user is on cooldown"""
        if user_id not in self.user_cooldowns:
            return False
        return datetime.now() - self.user_cooldowns[user_id] < timedelta(seconds=VoiceConfig.COOLDOWN_DURATION)

    def set_user_cooldown(self, user_id: int) -> None:
        """Set cooldown for a user"""
        self.user_cooldowns[user_id] = datetime.now()

    def get_connection(self, guild_id: int) -> Optional[discord.VoiceClient]:
        """Get voice connection for a guild"""
        return self.active_connections.get(guild_id)

    def set_connection(self, guild_id: int, connection: discord.VoiceClient) -> None:
        """Set voice connection for a guild"""
        self.active_connections[guild_id] = connection

    def remove_connection(self, guild_id: int) -> None:
        """Remove voice connection for a guild"""
        self.active_connections.pop(guild_id, None)

class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_manager = VoiceManager()
        self.blocked_users: Dict[int, Set[int]] = {}

    async def text_to_speech(self, text: str, lang: str = VoiceConfig.DEFAULT_LANGUAGE) -> Optional[str]:
        """Converts text to speech and returns the file path"""
        try:
            tts = gTTS(text, lang=lang)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tts.save(tmp_file.name)
                return tmp_file.name
        except Exception as e:
            logger.error(f"Error in text_to_speech: {e}")
            return None

    async def connect_to_channel(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
        """Connects to a voice channel with retry logic"""
        for attempt in range(VoiceConfig.RETRY_ATTEMPTS):
            try:
                return await channel.connect()
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < VoiceConfig.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(VoiceConfig.RETRY_DELAY)
        return None

    async def play_audio(self, vc: discord.VoiceClient, file_path: str) -> None:
        """Plays audio file in voice channel"""
        if not vc or not vc.is_connected():
            return

        try:
            vc.play(
                discord.FFmpegPCMAudio(file_path),
                after=lambda e: logger.error(f"Player error: {e}") if e else None
            )
            
            # Wait for audio to finish
            while vc.is_playing():
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error playing audio: {e}")

    def get_welcome_message(self, member: discord.Member) -> str:
        """Gets appropriate welcome message for member"""
        guild_id = member.guild.id
        
        # Check for server-specific message
        if guild_id in VoiceConfig.SERVER_SPECIFIC_MESSAGES:
            return VoiceConfig.SERVER_SPECIFIC_MESSAGES[guild_id].format(
                name=member.name,
                server=member.guild.name
            )
        
        # Use random general message
        return random.choice(VoiceConfig.WELCOME_MESSAGES).format(name=member.name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handles member joining voice channels"""
        if member.bot or before.channel == after.channel:
            return

        if before.channel is None and after.channel is not None:
            # Initialize blocked users for guild if needed
            guild_id = member.guild.id
            if guild_id not in self.blocked_users:
                self.blocked_users[guild_id] = set()

            # Check if user is blocked or on cooldown
            if (member.id in self.blocked_users[guild_id] or 
                self.voice_manager.is_user_on_cooldown(member.id)):
                return

            try:
                # Connect to voice channel
                vc = await self.connect_to_channel(after.channel)
                if not vc:
                    return

                self.voice_manager.set_connection(guild_id, vc)
                
                # Generate and play welcome message
                welcome_text = self.get_welcome_message(member)
                audio_file = await self.text_to_speech(welcome_text)
                
                if audio_file:
                    await self.play_audio(vc, audio_file)
                    os.remove(audio_file)  # Clean up file
                
                # Set cooldown and disconnect
                self.voice_manager.set_user_cooldown(member.id)
                await asyncio.sleep(VoiceConfig.DISCONNECT_DELAY)
                await vc.disconnect()
                self.voice_manager.remove_connection(guild_id)

            except Exception as e:
                logger.exception(f"Error handling voice state update: {e}")

    @commands.command(name="block_welcome")
    @commands.has_permissions(administrator=True)
    async def block_welcome(self, ctx: commands.Context, member: discord.Member):
        """Blocks a user from receiving welcome messages"""
        guild_id = ctx.guild.id
        if guild_id not in self.blocked_users:
            self.blocked_users[guild_id] = set()
        
        self.blocked_users[guild_id].add(member.id)
        await ctx.send(f"✅ {member.mention} ne recevra plus de messages de bienvenue.")

    @commands.command(name="unblock_welcome")
    @commands.has_permissions(administrator=True)
    async def unblock_welcome(self, ctx: commands.Context, member: discord.Member):
        """Unblocks a user from welcome messages"""
        guild_id = ctx.guild.id
        if guild_id in self.blocked_users:
            self.blocked_users[guild_id].discard(member.id)
            await ctx.send(f"✅ {member.mention} recevra à nouveau des messages de bienvenue.")

    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        for vc in self.bot.voice_clients:
            try:
                await vc.disconnect()
            except:
                pass

async def setup(bot: commands.Bot):
    """Setup the Voice cog"""
    await bot.add_cog(Voice(bot))
    logger.info("Voice cog loaded successfully")
