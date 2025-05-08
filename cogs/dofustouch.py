import discord
from discord import app_commands
from discord.ext import commands
import requests
from requests.exceptions import RequestException

class DofusTouch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Function to fetch data from DOFAPI
    def fetch_dofus_data(self, category, item_id):
        url = f"https://fr.dofus.dofapi.fr/{category}/{item_id}"
        try:
            response = requests.get(url, timeout=10)  # Add a timeout
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()
            return data
        except RequestException as e:
            print(f"Error fetching data from DOFAPI: {e}")
            return None

    # Function to format the API response
    def format_response(self, data):
        name = data.get("name", "Unknown")
        description = data.get("description", "No description available.")
        image_url = data.get("imgUrl", "")
        item_type = data.get("type", "Unknown type")
        response = f"**{name}**\n*Type: {item_type}*\n{description}"
        if image_url:
            response += f"\n{image_url}"
        return response

    # Slash command: /item <category> <item_id>
    @app_commands.command(name="item", description="Fetch item data from DOFAPI by ID")
    @app_commands.describe(category="The category of the item (e.g., weapons, equipment)", item_id="The ID of the item")
    async def item(self, interaction: discord.Interaction, category: str, item_id: int):
        data = self.fetch_dofus_data(category, item_id)
        if data:
            await interaction.response.send_message(self.format_response(data))
        else:
            await interaction.response.send_message(f"Item with ID '{item_id}' not found in category '{category}'.")

# Cog setup function
async def setup(bot):
    await bot.add_cog(DofusTouch(bot))
