import logging
from typing import Callable

from aiohttp import ContentTypeError, ClientConnectionError
from discord import Interaction, Embed

from .responses import interaction_send_object
from ..account_manager import Account
from ..aliases import PlayerName, PlayerUUID, PlayerDynamic
from ..functions import fname, load_embeds
from ..views.info import SessionInfoButton
from ..network import fetch_hypixel_data, mojang_session
from ..mcfetch import AsyncFetchPlayer2
from ..sessions import SessionManager, BedwarsSession
from ..errors import (
    PlayerNotFoundError,
    SessionNotFoundError,
    MojangInvalidResponseError,
    UserBlacklistedError,
    MissingPermissionsError
)
from ..linking import (
    link_account,
    get_linked_player,
    update_autofill
)


logger = logging.getLogger('statalytics')


async def fetch_player_info(
    player: PlayerDynamic,
    interaction: Interaction,
    eph=False
) -> tuple[PlayerName, PlayerUUID]:
    """
    Get formatted username & uuid of a user from their minecraft ign / uuid
    :param player: Username, uuid, or linked discord id of the player
    :param interaction: The discord interaction object used
    :param eph: whether or not to respond with an ephemeral message (default false)
    """
    if player is None:
        uuid = get_linked_player(interaction.user.id)

        if uuid:
            try:
                name = await AsyncFetchPlayer2(uuid, cache_backend=mojang_session).name
            except (ContentTypeError, ClientConnectionError) as exc:
                raise MojangInvalidResponseError from exc

            update_autofill(interaction.user.id, uuid, name)
        else:
            msg = ("You are not linked! Either specify "
                   "a player or link your account using `/link`!")

            if interaction.response.is_done():
                await interaction.followup.send(msg)
            else:
                await interaction.response.send_message(msg, ephemeral=eph)
            raise PlayerNotFoundError
    else:
        # allow for linked discord ids
        if player.isnumeric() and len(player) >= 16:
            player = get_linked_player(int(player)) or ''

        player_data = AsyncFetchPlayer2(player, cache_backend=mojang_session)

        try:
            name = await player_data.name
            uuid = await player_data.uuid
        except (ContentTypeError, ClientConnectionError) as exc:
            raise MojangInvalidResponseError from exc

        if name is None:
            await interaction_send_object(interaction)(
                "That player does not exist!", ephemeral=eph)
            raise PlayerNotFoundError
    return name, uuid


async def linking_interaction(
    interaction: Interaction,
    username: PlayerName
):
    """
    discord.py interaction for account linking
    :param interaction: the discord interaction to be used
    :param username: the username of the respective player
    """
    await interaction.response.defer()
    await run_interaction_checks(interaction)

    name, uuid = await fetch_player_info(username, interaction)

    hypixel_data = await fetch_hypixel_data(uuid, cache=False)

    # Linking Logic
    discord_tag = str(interaction.user)
    response = await link_account(
        discord_tag, interaction.user.id, hypixel_data, uuid, name)

    if response == 1:
        await interaction.followup.send(f"Successfully linked to **{fname(name)}**")
        return

    if response == 2:
        await interaction.followup.send(
            f"Successfully linked to **{fname(name)}**\n"
            "No sessions where found for this player so one was created.",
            view=SessionInfoButton())
        return

    # Player not linked embed
    embeds = load_embeds('linking', color='primary')
    await interaction.followup.send(embeds=embeds)


async def find_dynamic_session_interaction(
    interaction_callback: Callable[[str], None],
    username: PlayerName,
    uuid: PlayerUUID,
    hypixel_data: dict,
    session: int | None=None
) -> BedwarsSession:
    """
    Dynamically gets a session of a user\n
    If session is None, the first session to exist will be returned
    :param interaction_callback: The discord interaction response object
    to reply with.
    :param username: The username of the session owner
    :param uuid: The uuid of the session owner
    :param hypixel_data: the current hypixel data of the session owner
    :param session: The session to attempt to be retrieved
    :param eph: whether or not to respond ephemerally
    """
    session_manager = SessionManager(uuid)
    session_info = session_manager.get_session(session)

    # no sessions exist because... i forgot to finish this comment now idk
    if not session_info:
        session_count = session_manager.session_count()

        if session_count == 0:
            session_manager.create_session(session_id=1, hypixel_data=hypixel_data)

            await interaction_callback(
                content=f"**{fname(username)}** has no active sessions so one was created!"
            )
            raise SessionNotFoundError

        await interaction_callback(
            content=
                f"**{fname(username)}** doesn't have an active session with ID: `{session}`!"
        )
        raise SessionNotFoundError

    return session_info


async def _send_interaction_check_response(
    interaction: Interaction,
    embeds: list[Embed]
):
    if interaction.response.is_done():
        await interaction.edit_original_response(
            embeds=embeds, content=None, attachments=[])
    else:
        await interaction.response.send_message(
            embeds=embeds, content=None, files=[])


async def run_interaction_checks(
    interaction: Interaction,
    check_blacklisted: bool=True,
    permissions: list | str=None,
    allow_star: bool=True
):
    """
    Runs any checks to see if the interaction is allowed to proceed.
    Checks things such as if the user is blacklisted, or requires\
        certain permissions
    :param interaction: the `discord.Interaction` object for the interaction
    :param check_blacklisted: whether or not to check if the user is blacklisted
    :param permissions: A required list of permissions that the user must have\
        in order for the interaction to proceed. It will check if the user has\
        at least one of the permissions in the provided list.
    :param allow_star: whether or not to allow star permissions if certain\
        permissions are required
    """
    account = Account(interaction.user.id)

    if account.exists:
        if check_blacklisted and account.blacklisted:
            embeds = load_embeds('blacklisted', color='danger')
            await _send_interaction_check_response(interaction, embeds)

            logger.debug(
                f'`Blacklisted User`: Denied {interaction.user} '
                f'({interaction.user.id}) access to an interaction')
            raise UserBlacklistedError

    if permissions:
        # User doesn't have at least one of the required permissions
        if not (allow_star and '*' in account.permissions):
            if not set(permissions) & set(account.permissions):
                embeds = load_embeds('missing_permissions', color='danger')
                await _send_interaction_check_response(interaction, embeds)

                logger.debug(
                    f'`Missing permissions`: Denied {interaction.user} '
                    f'({interaction.user.id}) access to an interaction.')
                raise MissingPermissionsError
