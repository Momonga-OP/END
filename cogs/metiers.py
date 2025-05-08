import discord
from discord.ext import commands
from discord import app_commands
import pandas as pd

class Metiers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = './metiers.xlsx'
        self.professions = pd.ExcelFile(self.file_path).sheet_names
        self.suggestion_box_message_id = None  # To track the suggestion box message

    @app_commands.command(name="metiers", description="Afficher les professions disponibles")
    async def metiers(self, interaction: discord.Interaction):
        if interaction.guild.id != 1248345019333611561 or interaction.channel.id != 1248345019333611561:
            await interaction.response.send_message(
                "Cette commande n'est disponible que dans le canal **#║╟➢👷metiers**.",
                ephemeral=True
            )
            return

        # Create dropdown options from Excel sheet names
        profession_options = [
            discord.SelectOption(label=profession, value=profession) for profession in self.professions
        ]
        view = MetiersView(profession_options, self.file_path, self)

        if self.suggestion_box_message_id:
            try:
                channel = interaction.channel
                message = await channel.fetch_message(self.suggestion_box_message_id)
                await message.edit(content="Choisissez une profession :", view=view)
            except discord.NotFound:
                self.suggestion_box_message_id = None

        if not self.suggestion_box_message_id:
            suggestion_message = await interaction.response.send_message(
                "Choisissez une profession :", view=view, fetch_response=True
            )
            self.suggestion_box_message_id = suggestion_message.id
            await suggestion_message.pin()

    async def move_suggestion_box_to_bottom(self, channel):
        if self.suggestion_box_message_id:
            try:
                message = await channel.fetch_message(self.suggestion_box_message_id)
                await message.delete()
                suggestion_message = await channel.send(content="Choisissez une profession :", view=message.components[0])
                self.suggestion_box_message_id = suggestion_message.id
                await suggestion_message.pin()
            except discord.NotFound:
                self.suggestion_box_message_id = None


class MetiersView(discord.ui.View):
    def __init__(self, profession_options, file_path, cog):
        super().__init__()
        self.add_item(MetiersSelect(profession_options, file_path, cog))


class MetiersSelect(discord.ui.Select):
    def __init__(self, profession_options, file_path, cog):
        super().__init__(placeholder="Sélectionnez une profession", min_values=1, max_values=1, options=profession_options)
        self.file_path = file_path
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        selected_profession = self.values[0]
        try:
            df = pd.read_excel(self.file_path, sheet_name=selected_profession)
            formatted_data = "\n".join(
                f"**Nom**: {row['Nom']} | **Serveur**: {row['Serveur']} | **Niveau métier**: {row['Niveau métier']} | **Classe**: {row['Classe']}"
                for _, row in df.iterrows()
            )

            embed = discord.Embed(
                title=f"Joueurs avec la profession {selected_profession}",
                description=formatted_data,
                color=discord.Color.blue()
            )
            embed.set_footer(
                text="Astuce : Si un joueur n'est pas en ligne, ajoutez-le comme ami et vérifiez son statut en ligne."
            )
            await interaction.response.send_message(embed=embed)
            await self.cog.move_suggestion_box_to_bottom(interaction.channel)
        except Exception as e:
            await interaction.response.send_message(
                f"Erreur lors du chargement des données pour {selected_profession}: {e}"
            )


async def setup(bot):
    await bot.add_cog(Metiers(bot))
