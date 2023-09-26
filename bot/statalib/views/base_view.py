from typing import Any
import discord

from ..handlers import handle_interaction_errors


class CustomBaseView(discord.ui.View):
    async def on_error(
        self,
        interaction: discord.Interaction[discord.Client],
        error: Exception,
        item: discord.ui.Item[Any]
    ) -> None:
        await handle_interaction_errors(interaction, error)
