import discord
from discord import app_commands
from discord.ext import commands

from helper.functions import update_command_stats, get_embed_color


class SubmitSuggestion(discord.ui.Modal, title='Submit Suggestion'):
    def __init__(self, channel, **kwargs):
        self.channel = channel
        super().__init__(**kwargs)

    suggestion = discord.ui.TextInput(label='Suggestion:', placeholder='You should add...', style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed_color = get_embed_color('primary')
        submit_embed = discord.Embed(
            title=f'Suggestion by {interaction.user} ({interaction.user.id})',
            description=f'**Suggestion:**\n{self.suggestion}', color=embed_color
        )

        await self.channel.send(embed=submit_embed)
        await interaction.followup.send('Successfully submitted suggestion!', ephemeral=True)


class Suggest(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client


    @app_commands.command(name='suggest', description='Suggest a feature you would like to see added!')
    async def suggest(self, interaction: discord.Interaction):
        channel = self.client.get_channel(1065918528236040232)
        await interaction.response.send_modal(SubmitSuggestion(channel))

        update_command_stats(interaction.user.id, 'suggest')


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Suggest(client))
