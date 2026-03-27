from __future__ import annotations

import asyncio
from typing import Iterable, Optional, Sequence


async def wait_for_reaction_from_user(
    bot,
    message,
    *,
    user,
    valid_emojis: Sequence[str],
    timeout: float = 60.0,
) -> str:
    """
    Waits for a reaction from a single `user` on `message` for one of `valid_emojis`.
    Returns the emoji string, or raises asyncio.TimeoutError.
    """

    def check(reaction, reactor):
        return (
            reactor == user
            and reaction.message.id == message.id
            and str(reaction.emoji) in valid_emojis
        )

    reaction, _reactor = await bot.wait_for("reaction_add", timeout=timeout, check=check)
    return str(reaction.emoji)


async def wait_for_reaction_from_users(
    bot,
    message,
    *,
    users: Iterable,
    valid_emojis: Sequence[str],
    timeout: float = 60.0,
) -> tuple[str, object]:
    """
    Waits for a reaction from one of `users` on `message`.
    Returns (emoji, reactor), or raises asyncio.TimeoutError.
    """
    users_set = set(users)

    def check(reaction, reactor):
        return (
            reactor in users_set
            and reaction.message.id == message.id
            and str(reaction.emoji) in valid_emojis
        )

    reaction, reactor = await bot.wait_for("reaction_add", timeout=timeout, check=check)
    return str(reaction.emoji), reactor


async def wait_for_message_from_user_with_prefix(
    bot,
    *,
    channel,
    user,
    prefix: str,
    timeout: float = 60.0,
):
    """
    Waits for a message from `user` in `channel` whose content starts with `prefix`.
    Returns the message object, or raises asyncio.TimeoutError.
    """

    def check(m):
        return m.author == user and m.channel == channel and m.content.startswith(prefix)

    return await bot.wait_for("message", timeout=timeout, check=check)

