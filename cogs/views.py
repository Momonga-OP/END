import discord
from discord.ui import View, Button, Modal, TextInput
import random
from .config import ALERTE_DEF_CHANNEL_ID, ALERT_MESSAGES, GUILD_ID, GUILD_EMOJIS_ROLES


class NoteModal(Modal):
    def __init__(self, message: discord.Message):
        super().__init__(title="Ajouter une note")
        self.message = message

        self.note_input = TextInput(
            label="Votre note",
            placeholder="Ajoutez des détails sur l'alerte (nom de la guilde attaquante, heure, etc.)",
            max_length=100,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.note_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message.embeds[0] if self.message.embeds else None
        if not embed:
            await interaction.response.send_message("Impossible de récupérer l'embed à modifier.", ephemeral=True)
            return

        existing_notes = embed.fields[0].value if embed.fields else "Aucune note."
        updated_notes = f"{existing_notes}\n- **{interaction.user.display_name}**: {self.note_input.value.strip()}"
        embed.clear_fields()
        embed.add_field(name="📝 Notes", value=updated_notes, inline=False)

        await self.message.edit(embed=embed)
        await interaction.response.send_message("Votre note a été ajoutée avec succès !", ephemeral=True)


class AlertActionView(View):
    def __init__(self, bot, message: discord.Message):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message
        self.is_locked = False

        self.add_note_button = Button(
            label="Ajouter une note",
            style=discord.ButtonStyle.secondary,
            emoji="📝"
        )
        self.add_note_button.callback = self.add_note_callback
        self.add_item(self.add_note_button)

        self.won_button = Button(
            label="Won",
            style=discord.ButtonStyle.success,
        )
        self.won_button.callback = self.mark_as_won
        self.add_item(self.won_button)

        self.lost_button = Button(
            label="Lost",
            style=discord.ButtonStyle.danger,
        )
        self.lost_button.callback = self.mark_as_lost
        self.add_item(self.lost_button)

        self.screens_def_button = Button(
            label="Screens-Def",
            style=discord.ButtonStyle.primary,
            emoji="🖼️"
        )
        self.screens_def_button.callback = self.upload_screenshot
        self.add_item(self.screens_def_button)

        # Adding the custom triangle emoji button for second defense
        self.second_defense_button = Button(
            style=discord.ButtonStyle.primary,  # Purple/violet color
            emoji="<:triangle_emoji:1223045245428568106>"  # Custom emoji with ID
        )
        self.second_defense_button.callback = self.call_second_defense
        self.add_item(self.second_defense_button)

    async def add_note_callback(self, interaction: discord.Interaction):
        if interaction.channel_id != ALERTE_DEF_CHANNEL_ID:
            await interaction.response.send_message("Vous ne pouvez pas ajouter de note ici.", ephemeral=True)
            return

        modal = NoteModal(self.message)
        await interaction.response.send_modal(modal)

    async def mark_as_won(self, interaction: discord.Interaction):
        await self.mark_alert(interaction, "Gagnée", discord.Color.green())

    async def mark_as_lost(self, interaction: discord.Interaction):
        await self.mark_alert(interaction, "Perdue", discord.Color.red())

    async def mark_alert(self, interaction: discord.Interaction, status: str, color: discord.Color):
        if self.is_locked:
            await interaction.response.send_message("Cette alerte a déjà été marquée.", ephemeral=True)
            return

        self.is_locked = True
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        embed = self.message.embeds[0]
        embed.color = color
        embed.add_field(name="Statut", value=f"L'alerte a été marquée comme **{status}** par {interaction.user.mention}.", inline=False)

        await self.message.edit(embed=embed)
        await interaction.response.send_message(f"Alerte marquée comme **{status}** avec succès.", ephemeral=True)

    async def upload_screenshot(self, interaction: discord.Interaction):
        await interaction.response.send_message("Veuillez uploader votre screenshot (formats supportés: jpg, png).", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.attachments

        try:
            message = await self.bot.wait_for('message', check=check, timeout=60.0)
            attachment = message.attachments[0]
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                embed = self.message.embeds[0]
                embed.set_image(url=attachment.url)
                await self.message.edit(embed=embed)
                await interaction.followup.send("Screenshot ajouté avec succès !", ephemeral=True)
            else:
                await interaction.followup.send("Format de fichier non supporté. Veuillez uploader un fichier jpg ou png.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Une erreur est survenue: {e}", ephemeral=True)

    async def call_second_defense(self, interaction: discord.Interaction):
        # Get the role to tag
        role = interaction.guild.get_role(1300093554064097401)
        if not role:
            await interaction.response.send_message("Le rôle pour la deuxième défense est introuvable.", ephemeral=True)
            return

        # Update the embed
        embed = self.message.embeds[0]
        embed.add_field(
            name="⚠️ Deuxième Défense",
            value=f"Une équipe défend déjà un percepteur, besoin de monde pour une deuxième défense. {role.mention}",
            inline=False
        )
        await self.message.edit(embed=embed)

        # Send a confirmation message
        await interaction.response.send_message(f"Demande de deuxième défense envoyée. {role.mention}", ephemeral=True)


class GuildPingView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        for guild_name, data in GUILD_EMOJIS_ROLES.items():
            button = Button(
                label=f"  {guild_name.upper()}  ",
                emoji=data["emoji"],
                style=discord.ButtonStyle.primary
            )
            button.callback = self.create_ping_callback(guild_name, data["role_id"])
            self.add_item(button)

    def create_ping_callback(self, guild_name, role_id):
        async def callback(interaction: discord.Interaction):
            try:
                if interaction.guild_id != GUILD_ID:
                    await interaction.response.send_message(
                        "Cette fonction n'est pas disponible sur ce serveur.", ephemeral=True
                    )
                    return

                alert_channel = interaction.guild.get_channel(ALERTE_DEF_CHANNEL_ID)
                if not alert_channel:
                    await interaction.response.send_message("Canal d'alerte introuvable !", ephemeral=True)
                    return

                role = interaction.guild.get_role(role_id)
                if not role:
                    await interaction.response.send_message(f"Rôle pour {guild_name} introuvable !", ephemeral=True)
                    return

                alert_message = random.choice(ALERT_MESSAGES).format(role=role.mention)
                embed = discord.Embed(
                    title="🔔 Alerte envoyée !",
                    description=f"**{interaction.user.mention}** a déclenché une alerte pour **{guild_name}**.",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.add_field(name="📝 Notes", value="Aucune note.", inline=False)

                sent_message = await alert_channel.send(content=alert_message, embed=embed)
                view = AlertActionView(self.bot, sent_message)
                await sent_message.edit(view=view)

                await interaction.response.send_message(
                    f"Alerte envoyée à {guild_name} dans le canal d'alerte !", ephemeral=True
                )

            except Exception as e:
                print(f"Error in ping callback for {guild_name}: {e}")
                await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)

        return callback
