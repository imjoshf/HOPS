# HOPS.py
import discord, time
from player_cards import PlayerCard, initialize_player_cards
from HOPS_game import handle_challenge, get_team_data, handle_wager, wait_for_reaction, wait_for_multiple_reactions, active_wagers, active_challenges
from HOPS_teams import create_user_team, view_team, update_team_position, change_team_name
from commands import (
    send_player_cards,
    view_collection,
    add_user,
    send_card_stats,
    initialize_cards_table,
    sync_player_cards_to_db,
    trade_card,
    giveaway,
)

initialize_player_cards()
initialize_cards_table()
sync_player_cards_to_db()

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = discord.Client(intents=intents)

# Cooldown dictionaries
drop_cooldowns = {}  # For !cards command
general_cooldowns = {}  # For all other commands

# Cooldown durations (in seconds)
DROP_COOLDOWN_DURATION = 0  # 30 minutes for !cards, but I set it to  0 for testing
GENERAL_COOLDOWN_DURATION = 0  # 5 seconds for other commands, but I set it to  0 for testing

def clean_mention(mention):
    # Clean up the mention to ensure it only contains the numeric discord_id.

    if mention.startswith("<@") and mention.endswith(">"):
        return mention[2:-1]  # Remove the <@ and > part
    return mention

async def get_user_from_guild(guild, discord_id):
    # Search for the user by discord_id in the specific guild.

    return await guild.fetch_member(discord_id)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    current_time = time.time()

    # Ensure the user exists in cooldown dictionaries
    user_id = message.author.id
    if user_id not in drop_cooldowns:
        drop_cooldowns[user_id] = 0
    if user_id not in general_cooldowns:
        general_cooldowns[user_id] = 0

    # Check general cooldown for all commands
    if current_time - general_cooldowns[user_id] < GENERAL_COOLDOWN_DURATION:
        await message.channel.send("Please wait 5 seconds before using another command.")
        return
    else:
        general_cooldowns[user_id] = current_time

    if message.guild:
        print(f"Message in server: {message.guild.name} - {message.channel.name} - {message.content}")
    else:
        print(f"Message in DM: {message.content}")

    # Processing the !cards command
    if message.content.startswith('!cards'):
        # Check the drop cooldown
        if current_time - drop_cooldowns[user_id] < DROP_COOLDOWN_DURATION:
            remaining_time = int(DROP_COOLDOWN_DURATION - (current_time - drop_cooldowns[user_id]))
            minutes, seconds = divmod(remaining_time, 60)
            await message.channel.send(f"Card drops are on cooldown. Please wait {minutes}m {seconds}s.")
        else:
            drop_cooldowns[user_id] = current_time  # Reset drop cooldown
            add_user(user_id)  # Ensure the user is added to the database
            await message.channel.send('Dropping three cards!')
            await send_player_cards(message.channel, user_id, bot)

    # Processing the !collection command
    elif message.content.startswith('!collection'):
        await view_collection(message.channel, user_id, bot)

    # Processing the !stats command
    elif message.content.startswith('!stats'):
        player_name = None
        parts = message.content.split(' ', 1)
        if len(parts) > 1:
            player_name = parts[1]  # The name of the player
        await send_card_stats(message.channel, user_id, player_name)

    # Processing the !team command
    elif message.content.startswith('!create_team'):
        parts = message.content.split()

        if len(parts) < 8:  # Command should have team_name + 6 instance IDs
            await message.channel.send(
                "Usage: `!create_team <team_name> <instance_id_1> <instance_id_2> <instance_id_3> <instance_id_4> <instance_id_5> <instance_id_6>`")
            return

        team_name = parts[1]  # First argument is the team name
        instance_ids = parts[2:8]  # Next six arguments are the instance IDs

        response = create_user_team(user_id, team_name, instance_ids)
        await message.channel.send(response)

    # Processing the !rename_team command
    elif message.content.startswith('!rename_team'):
        parts = message.content.split(' ', 1)
        if len(parts) > 1:
            new_team_name = parts[1]
            response = change_team_name(user_id, new_team_name)
            await message.channel.send(response)
        else:
            await message.channel.send("Please provide a new team name. Usage: `!update_team_name <new_team_name>`")

    # Processing the !team update command
    elif message.content.startswith('!update_team'):
        await update_team_position(message, user_id, bot)

    elif message.content.startswith('!view_team'):
        response = view_team(user_id)
        await message.channel.send(response)

    # Processing the !trade command
    elif message.content.startswith('!trade'):
        parts = message.content.split(' ')
        if len(parts) < 3:
            await message.channel.send("Usage: !trade <discord_id> <instance_id> <optional_cash>")
            return

        target_discord_id = parts[1]
        offer = parts[2:]  # Capturing both cards and cash as part of the offer

        # Clean the mention if it contains @ symbol
        target_discord_id = clean_mention(target_discord_id)

        # Ensure target_discord_id is numeric
        try:
            target_discord_id = int(target_discord_id)
        except ValueError:
            await message.channel.send(f"Invalid Discord ID: {parts[1]} is not a valid number.")
            return

        # Get the guild where the message was sent
        guild = message.guild

        # Fetch target user from the guild
        target_user = await get_user_from_guild(guild, target_discord_id)

        if target_user is None:
            await message.channel.send(
                f"Could not find a user with the ID {target_discord_id} in this server. Please check the discord ID and try again.")
            return

        # Now call the trade_card function with the cleaned data
        await trade_card(message, target_user, " ".join(offer), bot)  # Pass bot instance here

    # Processing the !give command
    elif message.content.startswith("!giveaway"):
        # Parse target user and giveaway details
        args = message.content.split(" ")
        if len(args) < 3:
            await message.channel.send("Usage: !giveaway @target_user <cards/cash>")
            return
        target_user = message.mentions[0]  # The user being mentioned
        giveaway_details = " ".join(args[2:])  # The rest of the message is the giveaway details
        # Call the giveaway function from commands.py
        await giveaway(message, target_user, giveaway_details, bot)

    elif message.content.startswith("!challenge"):
        args = message.content.split(" ")
        if len(args) < 2:
            await message.channel.send("Usage: `!challenge @User`")
            return

        # Get the target user (the person being challenged)
        target_user = message.mentions[0]

        # Get the Discord ID of the challenger (the user sending the challenge)
        challenger_discord_id = message.author.id

        # Get the team data for the challenger (team1)
        team1_name, team1_data = get_team_data(challenger_discord_id)

        if team1_data is None:
            await message.channel.send(f"Could not find your team, {message.author.name}.")
            return

        # Get the team data for the opponent (team2)
        target_discord_id = target_user.id
        team2_name, team2_data = get_team_data(target_discord_id)

        if team2_data is None:
            await message.channel.send(f"Could not find {target_user.name}'s team.")
            return

        # This was just for debugging challenges
        print(f"Challenger Team ({team1_name}):")

        for player in team1_data:
            print(f"  {player.player_name} - Off: {player.offensive_rating}, Def: {player.defensive_rating}")

        print(f"Opponent Team ({team2_name}):")

        for player in team2_data:
            print(f"  {player.player_name} - Off: {player.offensive_rating}, Def: {player.defensive_rating}")

        # Proceed with handling the challenge, passing team data
        await handle_challenge(bot, message, target_user, team1_name, team1_data, team2_name, team2_data)

bot.run('bot token replaced')

