import asyncio
from itertools import cycle
import discord
from discord.ext import commands

from bot_utilities.config_loader import config
from ..common import presences_disabled, current_language, presences

class OnReady(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} aka {self.bot.user.name} has connected to Discord!")
        
        # Menghapus semua slash commands yang terdaftar pada bot
        # await self.bot.tree.sync()
        # await self.bot.tree.clear_commands(guild=None, commands=None)

        # Bagian untuk mengubah status (presence) bot
        presences_cycle = cycle(presences + [current_language['help_footer']])
        if presences_disabled:
            return
        while True:
            presence = next(presences_cycle)
            presence_with_count = presence.replace("{guild_count}", str(len(self.bot.guilds)))
            delay = config['PRESENCES_CHANGE_DELAY']
            await self.bot.change_presence(activity=discord.Game(name=presence_with_count))
            await asyncio.sleep(delay)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        # Cek jika error adalah CommandNotFound
        if isinstance(error, discord.app_commands.errors.CommandNotFound):
            # Abaikan error atau log minimal jika perlu
            return  # Tidak melakukan apa-apa, dengan demikian menghindari debug muncul
        else:
            # Tampilkan error lainnya
            print(f"An error occurred: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(OnReady(bot))
