import discord
from discord.ext import commands

class OnError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        if isinstance(error, discord.app_commands.errors.CommandNotFound):
            # Mengabaikan error CommandNotFound agar tidak muncul di log
            return
        elif isinstance(error, discord.app_commands.errors.MissingPermissions):
            await interaction.response.send_message(f"{interaction.user.mention} You do not have permission to use this command.", ephemeral=True)
        elif isinstance(error, discord.app_commands.errors.NotOwner):
            await interaction.response.send_message(f"{interaction.user.mention} Only the owner of the bot can use this command.", ephemeral=True)
        else:
            # Tampilkan error lainnya jika diperlukan
            print(f"An error occurred: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(OnError(bot))
