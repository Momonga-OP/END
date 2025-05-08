import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import utcnow
from datetime import datetime, timedelta
import os
import re
import logging
import aiofiles
import json
from discord.ext.commands import CooldownMapping, BucketType
from .config import GUILD_ID, ALERTE_DEF_CHANNEL_ID
from database import get_ping_history, get_setting, set_setting

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_channel_id = int(get_setting('ALERTS_CHANNEL_ID', '1247728738326679583'))
        self._cd = CooldownMapping.from_cooldown(1, 60, BucketType.user)  # 1 use per 60 seconds per user

    def filter_relevant_messages(self, messages):
        """Filter messages that are sent by bots and mention everyone or roles."""
        return [
            message for message in messages
            if message.author.bot and (message.mention_everyone or message.role_mentions)
        ]

    def parse_notification_data(self, message):
        """Parse notification data from a message."""
        attacker_match = re.search(r"Attacker:\s*(\w+)", message.content, re.IGNORECASE)
        outcome_match = re.search(r"Outcome:\s*(Win|Loss)", message.content, re.IGNORECASE)
        guild_match = re.search(r"Guild:\s*(\w+)", message.content, re.IGNORECASE)
        
        return {
            "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "roles_tagged": [role.name for role in message.role_mentions],
            "guild": guild_match.group(1) if guild_match else "Unknown",
            "attacker": attacker_match.group(1) if attacker_match else "Unknown",
            "outcome": outcome_match.group(1) if outcome_match else "Not Specified"
        }

    async def generate_report(self, notification_data, now):
        """Generate a report file with notification data."""
        report_filename = f"notification_report_{now.strftime('%Y%m%d_%H%M%S')}.txt"
        async with aiofiles.open(report_filename, "w", encoding='utf-8') as report_file:
            if not notification_data:
                await report_file.write("No notifications were sent in the last 7 days.\n")
            else:
                for user_id, data in notification_data.items():
                    await report_file.write(f"User: {data['username']}\n")
                    await report_file.write(f"Total Notifications Sent: {len(data['notifications'])}\n\n")
                    for notification in data["notifications"]:
                        await report_file.write(f"  - Timestamp: {notification['timestamp']}\n")
                        await report_file.write(f"    Guild: {notification['guild']}\n")
                        await report_file.write(f"    Roles Tagged: {', '.join(notification['roles_tagged']) if notification['roles_tagged'] else 'None'}\n")
                        await report_file.write(f"    Attacker: {notification['attacker']}\n")
                        await report_file.write(f"    Outcome: {notification['outcome']}\n\n")
        return report_filename

    async def generate_json_report(self, notification_data):
        """Generate a JSON report with notification data."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "notifications": []
        }
        
        for user_id, data in notification_data.items():
            for notification in data["notifications"]:
                report["notifications"].append({
                    "user": data['username'],
                    "user_id": user_id,
                    "timestamp": notification['timestamp'],
                    "guild": notification['guild'],
                    "roles_tagged": notification['roles_tagged'],
                    "attacker": notification['attacker'],
                    "outcome": notification['outcome']
                })
                
        return report

    @app_commands.command(name="alert", description="Generate a report of notifications sent in this channel for the last 7 days.")
    async def alert(self, interaction: discord.Interaction):
        """Generate a report of notifications sent in the last 7 days."""
        # Check cooldown
        bucket = self._cd.get_bucket(interaction.user.id)  # Use the user's ID for cooldown tracking
        retry_after = bucket.update_rate_limit()
        if retry_after:
            await interaction.response.send_message(f"Please wait {retry_after:.2f} seconds before using this command again.", ephemeral=True)
            return

        # Ensure the command is only used in the specified channel
        if interaction.channel_id != self.allowed_channel_id and interaction.channel_id != ALERTE_DEF_CHANNEL_ID:
            await interaction.response.send_message("This command can only be used in the designated channels.", ephemeral=True)
            return

        # Get the message history for the last 7 days
        channel = interaction.channel
        now = utcnow()
        seven_days_ago = now - timedelta(days=7)

        # Defer the response since this might take a while
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # Collect relevant messages asynchronously
            messages = []
            async for message in channel.history(after=seven_days_ago, limit=500):
                messages.append(message)

            # Filter relevant messages
            relevant_messages = self.filter_relevant_messages(messages)

            # Collect notification data
            notification_data = {}
            for message in relevant_messages:
                author = message.author
                parsed_data = self.parse_notification_data(message)

                # Initialize data for the author if not already done
                if author.id not in notification_data:
                    notification_data[author.id] = {
                        "username": author.name,
                        "notifications": []
                    }

                # Append notification details
                notification_data[author.id]["notifications"].append(parsed_data)

            # Generate the reports
            report_filename = await self.generate_report(notification_data, now)
            json_report = await self.generate_json_report(notification_data)
            json_filename = f"notification_report_{now.strftime('%Y%m%d_%H%M%S')}.json"
            
            # Save JSON report
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_report, f, ensure_ascii=False, indent=2)

            # Create an embed with summary information
            embed = discord.Embed(
                title="📊 Rapport d'Alertes",
                description=f"Rapport généré pour les 7 derniers jours",
                color=discord.Color.blue(),
                timestamp=now
            )
            
            total_notifications = sum(len(data['notifications']) for data in notification_data.values())
            total_users = len(notification_data)
            
            embed.add_field(
                name="Résumé",
                value=f"**Total des alertes:** {total_notifications}\n**Utilisateurs uniques:** {total_users}",
                inline=False
            )
            
            # Add top 3 users by notification count
            if notification_data:
                sorted_users = sorted(
                    notification_data.items(), 
                    key=lambda x: len(x[1]['notifications']), 
                    reverse=True
                )[:3]
                
                top_users = "\n".join([f"**{i+1}.** {data['username']}: {len(data['notifications'])} alertes" 
                                    for i, (_, data) in enumerate(sorted_users)])
                
                embed.add_field(
                    name="Top Utilisateurs",
                    value=top_users or "Aucune donnée",
                    inline=False
                )

            # Notify the user and attach the files
            await interaction.followup.send(
                embed=embed,
                files=[discord.File(report_filename), discord.File(json_filename)],
                ephemeral=True
            )

            # Clean up the files after sending
            os.remove(report_filename)
            os.remove(json_filename)

        except discord.Forbidden:
            await interaction.followup.send("Je n'ai pas la permission de lire les messages dans ce canal.", ephemeral=True)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            await interaction.followup.send(f"Une erreur est survenue: {e}", ephemeral=True)

    @app_commands.command(name="stats", description="Show statistics about guild alerts.")
    async def stats(self, interaction: discord.Interaction, guild_name: str = None):
        """Show statistics about guild alerts."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            # Get all guild names if none specified
            guild_names = [guild_name] if guild_name else [
                role.name for role in interaction.guild.roles 
                if role.name.startswith("DEF")
            ]
            
            if not guild_names:
                await interaction.followup.send("Aucune guilde trouvée.", ephemeral=True)
                return
                
            embed = discord.Embed(
                title="📊 Statistiques d'Alertes par Guilde",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for name in guild_names:
                # Get ping history from database
                ping_records = get_ping_history(name, days=7)
                
                if not ping_records:
                    embed.add_field(
                        name=f"{name}",
                        value="Aucune alerte dans les 7 derniers jours.",
                        inline=False
                    )
                    continue
                    
                # Calculate statistics
                total_pings = len(ping_records)
                unique_users = len(set(record[2] for record in ping_records))  # author_id is at index 2
                
                # Count pings by day
                days = {}
                for record in ping_records:
                    # timestamp is at index 3
                    day = record[3].split()[0] if isinstance(record[3], str) else record[3].strftime("%Y-%m-%d")
                    days[day] = days.get(day, 0) + 1
                
                # Format the statistics
                stats = f"**Total des alertes:** {total_pings}\n"
                stats += f"**Utilisateurs uniques:** {unique_users}\n\n"
                
                if days:
                    stats += "**Alertes par jour:**\n"
                    for day, count in sorted(days.items(), reverse=True)[:5]:  # Show last 5 days
                        stats += f"- {day}: {count}\n"
                
                embed.add_field(
                    name=f"{name}",
                    value=stats,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await interaction.followup.send(f"Une erreur est survenue: {e}", ephemeral=True)

    @app_commands.command(name="set_alerts_channel", description="Set the channel where alerts can be generated.")
    @app_commands.default_permissions(administrator=True)
    async def set_alerts_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel where alerts can be generated."""
        try:
            # Save to database
            set_setting('ALERTS_CHANNEL_ID', str(channel.id))
            self.allowed_channel_id = channel.id
            
            await interaction.response.send_message(
                f"Le canal pour les alertes a été défini sur {channel.mention}.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting alerts channel: {e}")
            await interaction.response.send_message(
                f"Une erreur est survenue: {e}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Alerts(bot))
