import discord
from discord.ext import commands
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from typing import Optional
from .config import GUILD_ID, PING_DEF_CHANNEL_ID, ALERTE_DEF_CHANNEL_ID
from .views import GuildPingView

class StartGuildCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns = {}
        self.ping_history = defaultdict(list)
        self.member_counts = {}
        self.panel_message: Optional[discord.Message] = None

    @staticmethod
    def create_progress_bar(percentage: float, length: int = 10) -> str:
        filled = '▰' * int(round(percentage * length))
        empty = '▱' * (length - len(filled))
        return f"{filled}{empty} {int(percentage * 100)}%"

    async def update_member_counts(self):
        """Mise à jour précise des membres connectés"""
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            await guild.chunk()  # Charge tous les membres
            for role in guild.roles:
                if role.name.startswith("DEF"):
                    self.member_counts[role.name] = sum(
                        1 for m in role.members 
                        if not m.bot and m.raw_status != 'offline'
                    )

    def add_ping_record(self, guild_name: str, author_id: int):
        timestamp = datetime.now()
        self.ping_history[guild_name].append({
            'author_id': author_id,
            'timestamp': timestamp
        })
        self.ping_history[guild_name] = [
            ping for ping in self.ping_history[guild_name] 
            if ping['timestamp'] > datetime.now() - timedelta(days=7)
        ][-100:]

    def get_ping_stats(self, guild_name: str) -> dict:
        now = datetime.now()
        periodes = {
            '24h': now - timedelta(hours=24),
            '7j': now - timedelta(days=7)
        }

        stats = {'member_count': self.member_counts.get(guild_name, 0)}
        
        for periode, cutoff in periodes.items():
            pings = [p for p in self.ping_history[guild_name] if p['timestamp'] > cutoff]
            stats.update({
                f'total_{periode}': len(pings),
                f'unique_{periode}': len({p['author_id'] for p in pings}),
                f'activite_{periode}': min(100, len(pings) * 2)
            })
        
        return stats

    async def create_panel_embed(self) -> discord.Embed:
        await self.update_member_counts()
        
        embed = discord.Embed(
            title="🛡️ Panneau d'Alerte Défense",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        total_connectes = sum(self.member_counts.values())
        
        embed.set_author(
            name="Système d'Alerte START",
            icon_url="https://github.com/Momonga-OP/Start2000/blob/main/35_35-0%20(2).png?raw=true"
        )
        
        embed.description = (
            "```diff\n+ SYSTÈME D'ALERTE GUILDE [v2.7.0]\n```\n"
            "**📋 Instructions :**\n"
            "1️⃣ Cliquez sur le bouton de votre guilde\n"
            "2️⃣ Suivez les mises à jour dans #║╟➢📯alertes-def \n"
            "3️⃣ Ajoutez des notes si nécessaire\n\n"
            f"👥 Membres connectés: {total_connectes}\n"
            "```ansi\n[2;34m[!] Statut système: [0m[2;32mOPÉRATIONNEL[0m```"
        )

        for guild_name, count in self.member_counts.items():
            stats = self.get_ping_stats(guild_name)
            activite = self.create_progress_bar(stats['activite_24h'] / 100)
            
            valeur = (
                f"```prolog\n"
                f"[🟢 Connectés] {count}\n"
                f"[📨 Pings 24h] {stats['total_24h']}\n"
                f"[⏱ Cooldown] {'🟠 Actif' if self.cooldowns.get(guild_name) else '🟢 Inactif'}\n"
                f"[📊 Activité] {activite}```"
            )
            
            embed.add_field(
                name=f"📌 {guild_name}",
                value=valeur,
                inline=True
            )

        embed.set_footer(
            text=f"Dernière actualisation: {datetime.now().strftime('%H:%M:%S')}",
            icon_url="https://github.com/Momonga-OP/Start2000/blob/main/hourglass.png?raw=true"
        )
        
        return embed

    async def ensure_panel(self):
        await self.update_member_counts()
        
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        channel = guild.get_channel(PING_DEF_CHANNEL_ID)
        if not channel:
            return

        if not self.panel_message:
            async for msg in channel.history(limit=20):
                if msg.author == self.bot.user and msg.pinned:
                    self.panel_message = msg
                    break

        view = GuildPingView(self.bot)
        embed = await self.create_panel_embed()

        if self.panel_message:
            try:
                await self.panel_message.edit(embed=embed, view=view)
            except discord.NotFound:
                self.panel_message = None
                await self.ensure_panel()
        else:
            self.panel_message = await channel.send(embed=embed, view=view)
            await self.panel_message.pin(reason="Mise à jour du panneau")

    async def handle_ping(self, guild_name):
        """Gestion améliorée du cooldown"""
        now = datetime.now().timestamp()
        if guild_name in self.cooldowns:
            if now < self.cooldowns[guild_name]:
                return self.cooldowns[guild_name] - now
            del self.cooldowns[guild_name]
        
        self.cooldowns[guild_name] = now + 15  # 15 secondes de cooldown
        return True

    @commands.command(name="alerte_guild")
    async def ping_guild(self, ctx, guild_name: str):
        cooldown = await self.handle_ping(guild_name)
        if isinstance(cooldown, float):
            embed = discord.Embed(
                title="⏳ Temporisation Active",
                description=f"Veuillez patienter {cooldown:.1f}s avant une nouvelle alerte pour {guild_name}",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        self.add_ping_record(guild_name, ctx.author.id)
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
        guild = self.bot.get_guild(GUILD_ID)
        channel = guild.get_channel(ALERTE_DEF_CHANNEL_ID)
        
        if not channel:
            return

        log_embed = discord.Embed(
            title=f"🚩 Alerte {guild_name}",
            description=f"@here · Défenseurs requis · {self.member_counts.get(guild_name, 0)} disponibles",
            color=discord.Color.red()
        )
        log_embed.add_field(
            name="Informations",
            value=f"**Initiateur:** {author.mention}\n"
                  f"**Heure:** {discord.utils.format_dt(datetime.now(), 'F')}\n"
                  f"**Statut serveur:** `Stable`",
            inline=False
        )
        log_embed.add_field(
            name="Actions Requises",
            value="```fix\n1. Confirmer disponibilité\n2. Rejoindre le canal vocal\n3. Suivre les instructions```",
            inline=False
        )
        
        await channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_panel()
        guild = self.bot.get_guild(GUILD_ID)
        
        if guild:
            alert_channel = guild.get_channel(ALERTE_DEF_CHANNEL_ID)
            if alert_channel:
                await alert_channel.set_permissions(
                    guild.default_role,
                    send_messages=False,
                    add_reactions=False,
                    create_public_threads=False
                )
                
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{sum(self.member_counts.values())} défenseurs"
            )
        )
        print(f"✅ Système opérationnel • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

async def setup(bot: commands.Bot):
    await bot.add_cog(StartGuildCog(bot))
