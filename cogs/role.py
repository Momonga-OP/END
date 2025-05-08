import discord
from discord.ext import commands
from typing import Dict, Optional
import logging
import asyncio
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Role configuration
ROLE_DATA: Dict[str, Dict[str, any]] = {

    "GTO": {
        "emoji": "<:GTO:1307418692992237668>",
        "role_id": 1300093554080612363,
        "role_name": "GTO",
        "color": discord.Color.blue()
    },

    "LMDF": {
        "emoji": "<:lmdf:1307418765142786179>",
        "role_id": 1300093554080612364,
        "role_name": "LMDF",
        "color": discord.Color.green()
    },
    "Notorious": {
        "emoji": "<:notorious:1307418766266728500>",
        "role_id": 1300093554064097406,
        "role_name": "Notorious",
        "color": discord.Color.red()
    },
    "Percophile": {
        "emoji": "<:percophile:1307418769764651228>",
        "role_id": 1300093554080612362,
        "role_name": "Percophile",
        "color": discord.Color.orange()
    },
    "Nightmare": {
        "emoji": "<:Nightmare:1342131008987730064>",
        "role_id": 1300093554080612367,
        "role_name": "Nightmare",
        "color": discord.Color.gold()
    },
    "Crescent": {
        "emoji": "<:Crescent:1328374098262495232>",
        "role_id": 1300093554064097404,
        "role_name": "Crescent",
        "color": discord.Color.blue()
    },
    "Academie": {
        "emoji": "<:Academie:1333147586986774739>",
        "role_id": 1300093554080612365,
        "role_name": "Academie",
        "color": discord.Color.dark_red()
    },
}

DEF_ROLE_ID: int = 1300093554064097401
NICKNAME_TIMEOUT: int = 300  # 5 minutes
MAX_RETRIES: int = 3

class RoleSelectionView(discord.ui.View):
    def __init__(self, bot: commands.Bot, member: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.member = member
        self._add_role_buttons()

    def _add_role_buttons(self) -> None:
        """Add role buttons to the view"""
        for role_name, role_info in ROLE_DATA.items():
            self.add_item(
                RoleButton(
                    self.bot,
                    self.member,
                    role_name,
                    role_info["emoji"],
                    role_info["role_name"],
                    role_info["role_id"],
                    role_info["color"]
                )
            )

class RoleButton(discord.ui.Button):
    def __init__(
        self, 
        bot: commands.Bot,
        member: discord.Member,
        role_name: str,
        emoji: str,
        role_display_name: str,
        role_id: int,
        color: discord.Color
    ):
        super().__init__(
            label=role_name,
            emoji=emoji,
            style=discord.ButtonStyle.primary,
            custom_id=f"role_{role_name.lower()}"
        )
        self.bot = bot
        self.member = member
        self.role_display_name = role_display_name
        self.role_id = role_id
        self.color = color

    async def callback(self, interaction: discord.Interaction) -> None:
        """Handle button click interaction"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            server = interaction.guild or self.member.guild
            if not server:
                await interaction.followup.send("Server not found. Please try again.", ephemeral=True)
                return

            # Handle role assignment
            success = await self._handle_role_assignment(server, interaction)
            if success:
                # Handle nickname setup
                await self._handle_nickname_setup(interaction)
                
        except Exception as e:
            logger.error(f"Error in button callback: {str(e)}")
            await interaction.followup.send("An error occurred. Please try again or contact an admin.", ephemeral=True)

    async def _handle_role_assignment(self, server: discord.Guild, interaction: discord.Interaction) -> bool:
        """Handle the role assignment process"""
        try:
            # Get or create guild role
            role = server.get_role(self.role_id) or await self._create_role(server)
            if not role:
                await interaction.followup.send("Could not create or find the role. Please contact an admin.", ephemeral=True)
                return False

            # Get DEF role
            def_role = server.get_role(DEF_ROLE_ID)
            if not def_role:
                await interaction.followup.send("The DEF role does not exist. Please contact an admin.", ephemeral=True)
                return False

            # Assign roles
            await self.member.add_roles(role, def_role, reason=f"Roles assigned via selection panel at {datetime.now()}")
            await interaction.followup.send(
                f"✅ You've been assigned the **{self.role_display_name}** and **DEF** roles successfully!",
                ephemeral=True
            )
            return True

        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to assign roles.", ephemeral=True)
            return False
        except Exception as e:
            logger.error(f"Error assigning roles: {str(e)}")
            await interaction.followup.send("An error occurred while assigning roles.", ephemeral=True)
            return False

    async def _create_role(self, server: discord.Guild) -> Optional[discord.Role]:
        """Create a new role with the specified parameters"""
        try:
            return await server.create_role(
                name=self.role_display_name,
                color=self.color,
                reason="Auto-created role via selection panel",
                hoist=True,  # Shows role members separately in member list
                mentionable=True
            )
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            return None

    async def _handle_nickname_setup(self, interaction: discord.Interaction) -> None:
        """Handle the nickname setup process"""
        for attempt in range(MAX_RETRIES):
            try:
                # Ask for IGN
                await self.member.send("Please enter your in-game name:")
                
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == self.member and isinstance(m.channel, discord.DMChannel),
                    timeout=NICKNAME_TIMEOUT
                )

                new_nickname = f"[{self.role_display_name}] {response.content}"
                await self.member.edit(nick=new_nickname)
                await self.member.send(f"✅ Your nickname has been set to **{new_nickname}**")
                return

            except asyncio.TimeoutError:
                remaining_attempts = MAX_RETRIES - attempt - 1
                if remaining_attempts > 0:
                    await self.member.send(f"Time out! You have {remaining_attempts} more attempts.")
                else:
                    await self.member.send("Nickname setup timed out. Please contact an admin to set your nickname.")
            except discord.Forbidden:
                await interaction.followup.send(
                    "I couldn't send you a DM or change your nickname. Please check your privacy settings and contact an admin.",
                    ephemeral=True
                )
                return
            except Exception as e:
                logger.error(f"Error in nickname setup: {str(e)}")
                await self.member.send("An error occurred. Please contact an admin to set your nickname.")
                return

class RoleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recent_welcomes = set()  # Prevent duplicate welcomes

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle new messages for role assignment"""
        if message.author.bot or not message.guild:
            return

        user = message.author
        if len(user.roles) <= 1 and user.id not in self.recent_welcomes:
            self.recent_welcomes.add(user.id)
            await self.send_welcome_message(user)
            await asyncio.sleep(300)  # Clear from recent welcomes after 5 minutes
            self.recent_welcomes.discard(user.id)

    async def send_welcome_message(self, member: discord.Member) -> None:
        """Send welcome message with role selection panel"""
        try:
            embed = discord.Embed(
                title="🎮 Welcome to the Alliance!",
                description=(
                    "Welcome to the server! Please select your role by clicking a button below.\n\n"
                    "Your role determines your place in the alliance. Choose wisely!\n\n"
                    "**Note:** You'll be asked to provide your in-game name after selecting a role."
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Role Selection Panel • Choose your destiny")
            if member.guild.icon:
                embed.set_thumbnail(url=member.guild.icon.url)

            await member.send(
                embed=embed,
                view=RoleSelectionView(self.bot, member)
            )
            logger.info(f"Welcome message sent to {member.name}#{member.discriminator}")
            
        except discord.Forbidden:
            logger.warning(f"Could not send DM to {member.name}#{member.discriminator}")
            # Could implement a fallback here, like sending to a specific channel

async def setup(bot: commands.Bot) -> None:
    """Setup function to add the RoleCog to the bot"""
    await bot.add_cog(RoleCog(bot))
    logger.info("RoleCog has been loaded")
