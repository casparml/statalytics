import discord
from discord import app_commands
from discord.ext import commands

from render.mostplayed import render_mostplayed
from statalib import (
    fetch_player_info,
    username_autocompletion,
    generic_command_cooldown,
    fetch_hypixel_data,
    update_command_stats,
    loading_message,
    run_interaction_checks
)


class MostPlayed(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client
        self.LOADING_MSG = loading_message()


    @app_commands.command(
        name="mostplayed",
        description="Most played mode of a player")
    @app_commands.describe(player='The player you want to view')
    @app_commands.autocomplete(player=username_autocompletion)
    @app_commands.checks.dynamic_cooldown(generic_command_cooldown)
    async def most_played(self, interaction: discord.Interaction ,player: str=None):
        await interaction.response.defer()
        await run_interaction_checks(interaction)

        name, uuid = await fetch_player_info(player, interaction)

        await interaction.followup.send(self.LOADING_MSG)

        hypixel_data = await fetch_hypixel_data(uuid)

        rendered = await render_mostplayed(name, uuid, hypixel_data)
        await interaction.edit_original_response(
            content=None,
            attachments=[discord.File(rendered, filename='mostplayed.png')]
        )

        update_command_stats(interaction.user.id, 'mostplayed')


async def setup(client: commands.Bot) -> None:
    await client.add_cog(MostPlayed(client))
