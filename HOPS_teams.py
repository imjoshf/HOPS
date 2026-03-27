# HOPS_teams.py
import asyncio

from storage.repositories import (
    change_team_name as repo_change_team_name,
    create_user_team as repo_create_user_team,
    update_team_position as repo_update_team_position,
    get_user_id,
    user_has_team,
)
from services.team_service import get_team_from_db, render_team_view

def create_user_team(discord_id, team_name, instance_ids):
    return repo_create_user_team(discord_id, team_name, instance_ids)

def change_team_name(discord_id, new_team_name):
    return repo_change_team_name(discord_id, new_team_name)


async def update_team_position(message, user_id, bot):
    # Updates individual position on user's team
    sender = message.author
    sender_id = sender.id
    if get_user_id(sender_id) is None:
        await message.channel.send("You need to be registered first. Use `!cards` to register.")
        return
    if not user_has_team(sender_id):
        await message.channel.send("You don't have a team yet! Use `!team <team_name>` first.")
        return

    # Ask which position they want to update
    position_msg = await message.channel.send(
        "Which position would you like to update on your team? React with 1️⃣-6️⃣.\n\n1️⃣ Point Guard\n2️⃣ Shooting Guard\n3️⃣ Small Forward\n4️⃣ Power Forward\n5️⃣ Center\n6️⃣ Sixth Man")
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    for emoji in reactions:
        await position_msg.add_reaction(emoji)

    def check_reaction(reaction, user):
        return user == sender and reaction.message.id == position_msg.id and str(reaction.emoji) in reactions

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check_reaction)
    except asyncio.TimeoutError:
        await message.channel.send("Team update timed out.")
        return

    position_map = {
        "1️⃣": "point_guard",
        "2️⃣": "shooting_guard",
        "3️⃣": "small_forward",
        "4️⃣": "power_forward",
        "5️⃣": "center",
        "6️⃣": "sixth_man"
    }
    selected_position = position_map[str(reaction.emoji)]

    await message.channel.send(
        f"Send the instance ID of the player you want to assign as your {selected_position.replace('_', ' ').title()}.")

    def check_message(m):
        return m.author == sender and m.channel == message.channel

    try:
        instance_msg = await bot.wait_for("message", timeout=60.0, check=check_message)
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond.")
        return

    instance_id = instance_msg.content.strip()
    response = repo_update_team_position(sender_id, selected_position, instance_id)
    await message.channel.send(response)

def view_team(discord_id):
    # Sends message with users' team
    team = get_team_from_db(discord_id)
    if team is None:
        if get_user_id(discord_id) is None:
            return "User not found. Use `!cards` first to add yourself to the database."
        return "You do not have a team yet. Use `!team create <team_name>` to create one."
    return render_team_view(team)
