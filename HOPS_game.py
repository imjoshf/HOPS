# HOPS_game.py
import random, asyncio

# Dictionary to track active challenges and wagers
active_challenges = {}
active_wagers = {}

from services.team_service import calculate_off_def_totals, get_team_game_team_data

async def wait_for_reaction(bot, message, user, valid_reactions):
    # Waits for a valid reaction from a specific user on a given message.
    try:
        def check(reaction, reactor):
            return reactor == user and str(reaction.emoji) in valid_reactions and reaction.message.id == message.id

        reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=60)
        return str(reaction.emoji) == "✅"
    except asyncio.TimeoutError:
        await message.channel.send(f"{user.mention} did not respond in time!")
        return False

async def wait_for_multiple_reactions(bot, message, users, valid_reactions):
    # Waits for valid reactions from multiple users on a given message.

    reactions = {}

    def check(reaction, reactor):
        return reactor in users and str(reaction.emoji) in valid_reactions and reaction.message.id == message.id

    try:
        while len(reactions) < len(users):
            reaction, reactor = await bot.wait_for("reaction_add", check=check, timeout=60)
            reactions[reactor] = str(reaction.emoji)

        return reactions
    except asyncio.TimeoutError:
        return {}

quarter_prompts = [
    ("You're on a fast break, defender closing in!", "1️⃣ Go for a dunk", "2️⃣ Pull up for a jumper",
     "You soar through the air and slam it home!", "Your jumper clangs off the rim."),
    ("Clock winding down, last shot of the quarter!", "1️⃣ Take a step-back three", "2️⃣ Drive to the hoop",
     "Nothing but net! The crowd goes wild!", "You get blocked at the rim!"),
    ("Opponent traps your ball handler!", "1️⃣ Pass to the open man", "2️⃣ Try to dribble out of it",
     "Great vision! Your teammate scores!", "The defender strips the ball away!"),
    ("Your team is down by 3, 10 seconds left!", "1️⃣ Shoot a contested three", "2️⃣ Pass to a teammate",
     "It's in! The game is tied!", "Your pass gets intercepted!"),
]
# These prompts are just for testing for now, I plan on refining them

async def handle_challenge(bot, message, target_user, team1_name, team1_data, team2_name, team2_data):
    # Handles the entire challenge process, including wager initiation.

    # Send the challenge message
    challenge_msg = await message.channel.send(
        f"{target_user.mention}, {message.author.mention} has challenged you to a game! "
        f"({team1_name} vs {team2_name}) Do you accept? ✅/❌"
    )

    await challenge_msg.add_reaction("✅")
    await challenge_msg.add_reaction("❌")

    if not await wait_for_reaction(bot, challenge_msg, target_user, ["✅", "❌"]):
        await message.channel.send(f"{target_user.mention} has declined the challenge.")
        return

    await message.channel.send(f"{target_user.mention} has accepted the challenge!")

    # Pass teams along with players to the wager handler
    await handle_wager(bot, message, target_user, team1_name, team1_data, team2_name, team2_data)

async def handle_wager(bot, message, target_user, team1_name, team1_data, team2_name, team2_data):
    # Handles wager decision between two players.

    wager_msg = await message.channel.send(
        f"{message.author.mention} and {target_user.mention}, would you like to make a wager? ✅/❌"
    )

    await wager_msg.add_reaction("✅")
    await wager_msg.add_reaction("❌")

    reactions = await wait_for_multiple_reactions(bot, wager_msg, [message.author, target_user], ["✅", "❌"])

    if all(reaction == "✅" for reaction in reactions.values()):
        await message.channel.send("Both players have agreed to the wager!")
        await message.channel.send(
            "To make an offer, each player must send their wager using `!wager $court_cash amount, instance_id(s)`."
        )

        await process_wager_offers(bot, message.author, target_user, message.channel, team1_name, team1_data, team2_name, team2_data, message)
    else:
        await message.channel.send("One or both players declined the wager. The challenge is canceled.")

async def process_wager_offers(bot, player1, player2, channel, team1_name, team1_data, team2_name, team2_data, message):
    # Waits for both players to send their wager offers, then asks for final confirmation.

    wagers = {}

    def check_wager(msg):
        return msg.author in [player1, player2] and msg.content.startswith("!wager ")

    try:
        while len(wagers) < 2:
            msg = await bot.wait_for("message", check=check_wager, timeout=120)
            wagers[msg.author] = msg.content[len("!wager "):]  # Extract wager details

        wager_msg = await channel.send(
            f"{player1.mention} is wagering **{wagers[player1]}**.\n"
            f"{player2.mention} is wagering **{wagers[player2]}**.\n"
            "Do both players accept these terms? ✅/❌"
        )

        await wager_msg.add_reaction("✅")
        await wager_msg.add_reaction("❌")

        reactions = await wait_for_multiple_reactions(bot, wager_msg, [player1, player2], ["✅", "❌"])

        if all(reaction == "✅" for reaction in reactions.values()):
            # Both players accepted the wager, now proceed to start the game directly
            await run_game(bot, channel, player1, player2, team1_name, team1_data, team2_name, team2_data)
        else:
            await channel.send("One or both players declined the wager. The challenge is canceled.")

    except asyncio.TimeoutError:
        await channel.send("Wager process timed out. Challenge is canceled.")

async def run_game(bot, channel, user1, user2, team1_name, team1_data, team2_name, team2_data):
    # Runs a full game simulation.
    quarter_scores = {user1: 0, user2: 0}
    users = [user1, user2]
    teams = {user1: team1_data, user2: team2_data}

    # Now the game can proceed
    for quarter in range(4):
        active_user = users[quarter % 2]
        passive_user = users[(quarter + 1) % 2]

        # Prepare the prompt and options for the active user
        prompt, option1, option2, success_msg, fail_msg = random.choice(quarter_prompts)
        prompt_msg = await channel.send(
            f"Middle of Q{quarter + 1}. {active_user.mention}, {prompt}\n\n{option1}\n{option2}"
        )

        await prompt_msg.add_reaction("1️⃣")
        await prompt_msg.add_reaction("2️⃣")

        # Wait for the active user to respond
        reaction = await wait_for_reaction(bot, prompt_msg, active_user, ["1️⃣", "2️⃣"])
        correct_choice = random.choice([True, False])

        # Calculate offensive and defensive ratings for each team
        team1_off, team1_def = calculate_team_ratings(team1_data, team2_data)
        team2_off, team2_def = calculate_team_ratings(team2_data, team1_data)

        # Update the scores for each quarter based on the choices
        quarter_scores[user1] += calculate_quarter_score(team1_off, team2_def, quarter, correct_choice)
        quarter_scores[user2] += calculate_quarter_score(team2_off, team1_def, quarter, not correct_choice)

        # Determine the result of the quarter
        result_message = success_msg if correct_choice else fail_msg
        await channel.send(f"Q{quarter + 1} Result: {result_message}")
        await channel.send(
            f"End of Q{quarter + 1}: Score is {int(quarter_scores[user1])} - {int(quarter_scores[user2])}"
        )

    # Determine the winner
    winner = user1 if quarter_scores[user1] > quarter_scores[user2] else user2
    await channel.send(f"Game Over! {winner.mention} wins!")

    # Handle the wager transfer if a wager exists
    if winner in active_wagers:
        await transfer_wager(winner, active_wagers[winner])

def calculate_team_ratings(team_data, opponent_data):
    # Calculates the offensive and defensive ratings of a team.
    # `opponent_data` is unused but kept for backward-compatible signature.
    return calculate_off_def_totals(team_data)


def calculate_quarter_score(team_off, opponent_def, quarter, correct_choice):
    # Calculates the score for a given quarter based on team ratings, quarter formula, and correctness of player choice.

    print(team_off) # Just to see make sure team offense is being properly calculated

    # Initialize base multiplier and score adjustment based on the quarter
    if quarter == 1:
        base_multiplier = 1 / 3
    elif quarter == 2:
        base_multiplier = 1.05 / 2
    elif quarter == 3:
        base_multiplier = 9.5 / 12
    else:  # Quarter 4
        base_multiplier = 1

    # Calculate the base score
    base_score = ((team_off / 12) * base_multiplier) - (opponent_def / 200)

    # Adjust score based on whether the player made a correct choice
    score_variation = 3 if correct_choice else 0

    # Calculate final quarter score
    final_score = base_score + score_variation

    # Ensure the score never decreases
    return max(final_score, 0)  # Prevent negative scores

def get_team_data(discord_id):
    return get_team_game_team_data(discord_id)


async def transfer_wager(winner, wager):
    # Transfers wagered items to the winner. Not currently functional
    await winner.send(f"You've received your wagered items: {wager}!")
