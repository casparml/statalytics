from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from render.historical import render_historical
from statalib import (
    HistoricalManager,
    fetch_player_info,
    uuid_to_discord_id,
    username_autocompletion,
    generic_command_cooldown,
    fetch_hypixel_data,
    update_command_stats,
    fetch_skin_model,
    ordinal, loading_message,
    handle_modes_renders,
    fname,
    pluralize
)


class Daily(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client
        self.LOADING_MSG = loading_message()


    @app_commands.command(
        name="daily",
        description="View the daily stats of a player")
    @app_commands.describe(player='The player you want to view')
    @app_commands.autocomplete(player=username_autocompletion)
    @app_commands.checks.dynamic_cooldown(generic_command_cooldown)
    async def daily(self, interaction: discord.Interaction, player: str=None):
        await interaction.response.defer()

        name, uuid = await fetch_player_info(player, interaction)

        historic = HistoricalManager(interaction.user.id, uuid)
        gmt_offset, hour = historic.get_reset_time()

        historical_data = historic.get_historical(identifier='daily')

        if not historical_data:
            await historic.start_historical()
            await interaction.followup.send(
                f'Historical stats for {fname(name)} will now be tracked.')
            return

        await interaction.followup.send(self.LOADING_MSG)
        skin_res = await fetch_skin_model(uuid, 144)
        hypixel_data = await fetch_hypixel_data(uuid)

        now = datetime.now(timezone(timedelta(hours=gmt_offset)))
        formatted_date = now.strftime(f"%b {now.day}{ordinal(now.day)}, %Y")

        next_occurrence = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if now >= next_occurrence:
            next_occurrence += timedelta(days=1)
        utc_next_occurrence = next_occurrence.astimezone(timezone.utc)
        timestamp = int(utc_next_occurrence.timestamp())

        kwargs = {
            "name": name,
            "uuid": uuid,
            "identifier": "daily",
            "relative_date": formatted_date,
            "title": "Daily Stats",
            "hypixel_data": hypixel_data,
            "skin_res": skin_res,
            "save_dir": interaction.id
        }

        await handle_modes_renders(
            interaction=interaction,
            func=render_historical,
            kwargs=kwargs,
            message=f':alarm_clock: Resets <t:{timestamp}:R>'
        )
        update_command_stats(interaction.user.id, 'daily')


    @app_commands.command(
        name="lastday",
        description="View yesterdays stats of a player")
    @app_commands.describe(
        player='The player you want to view',
        days='The lookback amount in days')
    @app_commands.autocomplete(player=username_autocompletion)
    @app_commands.checks.dynamic_cooldown(generic_command_cooldown)
    async def lastday(self, interaction: discord.Interaction,
                      player: str=None, days: int=1):
        await interaction.response.defer()

        name, uuid = await fetch_player_info(player, interaction)

        historic = HistoricalManager(interaction.user.id, uuid)
        discord_id = uuid_to_discord_id(uuid=uuid)

        max_lookback = historic.get_max_lookback(discord_id, interaction.user.id)

        if -1 != max_lookback < days:
            embeds = historic.build_invalid_lookback_embeds(max_lookback)
            await interaction.followup.send(embeds=embeds)
            return

        days = max(days, 1)
        gmt_offset = historic.get_reset_time()[0]
        now = datetime.now(timezone(timedelta(hours=gmt_offset)))

        try:
            relative_date = now - timedelta(days=days)

            formatted_date = relative_date.strftime(
                f"%b {relative_date.day}{ordinal(relative_date.day)}, %Y")

            period = relative_date.strftime("daily_%Y_%m_%d")
        except OverflowError:
            await interaction.followup.send('Big, big number... too big number...')
            return

        historical_data = historic.get_historical(identifier=period)

        if not historical_data:
            await interaction.followup.send(
                f'{fname(name)} has no tracked data for {days} day(s) ago!')
            return

        await interaction.followup.send(self.LOADING_MSG)
        skin_res = await fetch_skin_model(uuid, 144)
        hypixel_data = await fetch_hypixel_data(uuid)

        kwargs = {
            "name": name,
            "uuid": uuid,
            "identifier": "lastday",
            "relative_date": formatted_date,
            "title": f"{days} {pluralize(days, 'Day')} Ago",
            "period": period,
            "hypixel_data": hypixel_data,
            "skin_res": skin_res,
            "save_dir": interaction.id
        }

        await handle_modes_renders(interaction, render_historical, kwargs)
        update_command_stats(interaction.user.id, 'lastday')


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Daily(client))
