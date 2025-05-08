import discord
from discord.ext import commands
from discord import app_commands
from io import BytesIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WriteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="write", description="Send an anonymous message with an optional image. Only admins can use this command.")
    @app_commands.describe(message="The message to send", image="Optional image to include with the message")
    @app_commands.checks.has_permissions(administrator=True)
    async def write(self, interaction: discord.Interaction, message: str, image: discord.Attachment = None):
        try:
            # Prepare the message content
            content = message
            files = []

            # Check if an image is provided
            if image:
                # Create a discord.File object directly from the attachment
                img_file = discord.File(fp=BytesIO(await image.read()), filename=image.filename)
                files.append(img_file)

            # Send the anonymized message with the optional image
            await interaction.channel.send(content=content, files=files)
            
            # Defer the interaction response and delete it
            await interaction.response.defer(ephemeral=True)
            await interaction.delete_original_response()

        except Exception as e:
            logger.error(f"Error in write command: {e}", exc_info=True)
            await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)

    @write.error
    async def write_error(self, interaction: discord.Interaction, error):
        try:
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message("You do not have the necessary permissions to use this command.", ephemeral=True)
            else:
                await interaction.response.send_message("An unexpected error occurred while processing the command.", ephemeral=True)
        except discord.errors.InteractionResponded:
            pass

async def setup(bot):
    await bot.add_cog(WriteCog(bot))
