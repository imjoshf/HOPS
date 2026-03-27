#commands.py
import discord, random, io, asyncio, time, string
from player_cards import PlayerCard
try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None

DATABASE_NAME = 'HOPS_prototype1.db'
CARDS_PER_PAGE = 10

from storage.database import connect_db as storage_connect_db
from storage.repositories import (
    add_user as repo_add_user,
    initialize_cards_table as repo_initialize_cards_table,
    sync_player_cards_to_db as repo_sync_player_cards_to_db,
    get_user_id as repo_get_user_id,
    add_card_to_user as repo_add_card_to_user,
    user_owns_card as repo_user_owns_card,
    get_user_cards_rows as repo_get_user_cards_rows,
    get_last_claimed_card_player as repo_get_last_claimed_card_player,
    get_user_row as repo_get_user_row,
    get_card_display_for_instance as repo_get_card_display_for_instance,
    execute_trade_swap as repo_execute_trade_swap,
    execute_giveaway_transfer as repo_execute_giveaway_transfer,
)

from utils.offer_parser import parse_offer_items, format_instance_ids_for_owner
from utils.discord_interactions import (
    wait_for_message_from_user_with_prefix,
    wait_for_reaction_from_user,
    wait_for_reaction_from_users,
)


def connect_db():  # Connect to SQL database
    # Delegate connection logic to storage layer to reduce redundancy.
    return storage_connect_db()


def add_user(discord_id):  # Adds user to database
    repo_add_user(discord_id)


def user_owns_card(discord_id, player_name):
    return repo_user_owns_card(discord_id, player_name)


def initialize_cards_table():
    repo_initialize_cards_table()


def sync_player_cards_to_db():
    repo_sync_player_cards_to_db(PlayerCard)

def get_user_id(discord_id):
    return repo_get_user_id(discord_id)

def get_random_condition():
    # Returns a random condition based on predefined probabilities. This will affect gameplay later on
    conditions = ['Healthy', 'Injury Watch', 'Injured', 'Peak Condition']
    probabilities = [0.7, 0.15, 0.1, 0.05]
    return random.choices(conditions, probabilities)[0]

def generate_card_id():
    # Generate a unique six-character alphanumeric ID for the card.
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def generate_card_instance_id():
    # Generates a random 6-character alphanumeric string for the instance ID.
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


def add_card_to_user(discord_id, player_name, season_year):
    return repo_add_card_to_user(discord_id, player_name, season_year)

def pick_random_cards(num_cards=3):
    all_cards = PlayerCard.get_cards()
    if len(all_cards) < num_cards:
        return []

    return random.sample(all_cards, num_cards)

def compile_images(cards): # Creates image of three cards
    if Image is None:
        return None
    images = [card.image for card in cards if card.image is not None]

    if not images:
        print("No images found for the selected cards.")
        return None

    total_width = sum(image.width for image in images)
    max_height = max(image.height for image in images)

    # Create a transparent background for the compiled image
    compiled_image = Image.new("RGBA", (total_width, max_height), (0, 0, 0, 0))

    x_offset = 0
    for img in images:
        compiled_image.paste(img, (x_offset, 0), img if img.mode == 'RGBA' else None)
        x_offset += img.width

    # Save to a BytesIO object instead of a file
    img_byte_arr = io.BytesIO()
    compiled_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)  # Move to the beginning of the BytesIO object

    return img_byte_arr

# To store cooldown information and expiration timestamps for card drops
user_cooldowns = {}
card_drop_expiration_times = {}

async def send_player_cards(channel, user_id, bot):
    # Pick 3 random cards
    selected_cards = pick_random_cards(3)
    if not selected_cards:
        await channel.send("Not enough cards to choose from.")
        return

    # Compile images for the selected cards
    compiled_image = compile_images(selected_cards)
    if compiled_image is None:
        await channel.send("Card images are unavailable (PIL not installed). Try again later.")
        return

    message = await channel.send(file=discord.File(compiled_image, filename='compiled_player_cards.png'))

    # Set expiration time for the card drop
    card_drop_expiration_times[message.id] = time.time() + 60  # Expires after 1 minute

    # Add reactions to the message for card selection
    emoji_list = ['1️⃣', '2️⃣', '3️⃣']
    for emoji in emoji_list:
        await message.add_reaction(emoji)


    # Wait for a reaction from the user
    def check(reaction, user):
        # Check expiration before allowing claim
        if time.time() > card_drop_expiration_times.get(message.id, 0):
            return False
        if not getattr(user, "id", None):
            return False
        if user.id != user_id:
            return False
        return str(reaction.emoji) in emoji_list and reaction.message.id == message.id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await channel.send("The card drop has expired!")
    else:
        if time.time() > card_drop_expiration_times[message.id]:  # Re-check expiration
            await channel.send("The card drop has expired!")
        else:
            chosen_card_index = emoji_list.index(str(reaction.emoji))
            chosen_card = selected_cards[chosen_card_index]
            try:
                response = add_card_to_user(user.id, chosen_card.player_name, chosen_card.season_year)
            except Exception as e:
                await channel.send(f"Failed to add card (DB error): {type(e).__name__}: {e}")
            else:
                await channel.send(response)

    # Clean up expired card drop data
    card_drop_expiration_times.pop(message.id, None)

async def view_collection(channel, discord_id, bot):
    # Fetch the user's cards along with instance numbers, instance ids, and condition
    user_cards = repo_get_user_cards_rows(discord_id)

    if not user_cards:
        await channel.send("You don't have any cards in your collection.")
        return

    # Define pagination variables
    total_cards = len(user_cards)
    total_pages = (total_cards + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
    current_page = 0

    def generate_page_content(page_index):
        start = page_index * CARDS_PER_PAGE
        end = start + CARDS_PER_PAGE
        cards_on_page = user_cards[start:end]

        content = f"**Your Collection - Page {page_index + 1}/{total_pages}:**\n"
        for idx, (player_name, season_year, instance_number, instance_id, condition) in enumerate(cards_on_page, start=start + 1):
            content += f"{idx}. {player_name}, {season_year} #{instance_number} (ID: {instance_id}) - Condition: {condition}\n"

        return content

    # Send the first page of the collection
    message = await channel.send(generate_page_content(current_page))

    # Add reaction buttons for pagination if more than one page exists
    if total_pages > 1:
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        # Reaction check function
        def check(reaction, user):
            return (user != bot.user and
                    str(reaction.emoji) in ["◀️", "▶️"] and
                    reaction.message.id == message.id)

        while True:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                await message.remove_reaction(reaction.emoji, user)

                # Update current_page based on the reaction
                if reaction.emoji == "▶️" and current_page < total_pages - 1:
                    current_page += 1
                elif reaction.emoji == "◀️" and current_page > 0:
                    current_page -= 1

                # Edit the message to show the new page
                await message.edit(content=generate_page_content(current_page))

            except asyncio.TimeoutError:
                await message.clear_reactions()
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")


async def send_card_stats(channel, discord_id, player_name):
    # Send a message containing the stats of a player/card
    try:
        # If player_name is provided, search for it
        if player_name:
            print(f"Searching for player name: {player_name}")

            # Log contents of PlayerCard.cards for debugging
            print("Contents of PlayerCard.cards:", [card.player_name for card in PlayerCard.cards])

            # Retrieve specific card by player_name from PlayerCard.cards
            card = next(
                (card for card in PlayerCard.cards if card.player_name.lower().strip() == player_name.lower().strip()),
                None
            )

            if not card:
                print(f"No matching card found for player: {player_name}")
        else:
            # If no player_name, get the most recently claimed card using discord_id
            card = get_last_claimed_card(discord_id)

        if isinstance(card, PlayerCard):
            # Prepare the message with stats, including offensive and defensive ratings, attributes, condition, and positions
            stats_message = (
                f"Stats for {card.player_name} ({card.stats})\n"
                f"Position: {card.position}\n"
                f"Offensive Rating: {card.offensive_rating}\n"
                f"Defensive Rating: {card.defensive_rating}\n"
                f"Attributes: {', '.join(card.attributes) if card.attributes else 'No attributes'}"
            )

            await channel.send(stats_message)

            # Send the image if available
            if card.image:
                img_byte_arr = io.BytesIO()
                card.image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                await channel.send(file=discord.File(img_byte_arr, filename='card_image.png'))
            else:
                await channel.send("No image available for this card.")
        else:
            await channel.send("Player card not found.")
    except Exception as e:
        print(f"Error sending stats: {e}")
        await channel.send("An error occurred while retrieving stats.")



def get_last_claimed_card(discord_id):
    # This is so !stats automatically prints the stats of the last player collected, if no other player is specified.
    return repo_get_last_claimed_card_player(discord_id)

async def trade_card(message, target_user: discord.Member, offer: str, bot: discord.Client):
    # Two players make a trade
    sender = message.author
    sender_id = sender.id
    target_user_id = target_user.id
    # Retrieve user IDs & balances from the database
    sender_row = repo_get_user_row(sender_id)
    receiver_row = repo_get_user_row(target_user_id)

    if not sender_row or not receiver_row:
        await message.channel.send("One of the users is not found in the database.")
        return

    sender_user_id, sender_cash = sender_row
    receiver_user_id, receiver_cash = receiver_row

    # Parse sender's offer
    try:
        offer_items = parse_offer_items(offer)
    except ValueError:
        await message.channel.send("Invalid cash amount. Please enter a valid number.")
        return

    sender_cash_offer = offer_items.cash
    try:
        sender_cards_display, sender_instance_ids = format_instance_ids_for_owner(
            user_id=sender_user_id,
            instance_ids=offer_items.instance_ids,
            get_card_display_for_instance=repo_get_card_display_for_instance,
        )
    except ValueError as e:
        invalid_instance_id = e.args[0] if e.args else str(e)
        await message.channel.send(f"You do not own the card with Instance ID `{invalid_instance_id}`.")
        return

    # Check if sender has enough Court Cash
    if sender_cash < sender_cash_offer:
        await message.channel.send("You do not have enough Court Cash to make this offer.")
        return

    sender_offer_str = ", ".join(sender_cards_display) + (
        f" and ${sender_cash_offer}" if sender_cash_offer else ""
    )
    trade_msg = await message.channel.send(
        f"{target_user.mention}, {sender.mention} is offering `{sender_offer_str}`. Do you accept or decline?"
    )
    await trade_msg.add_reaction("✅")
    await trade_msg.add_reaction("❌")

    try:
        reaction_emoji = await wait_for_reaction_from_user(
            bot,
            trade_msg,
            user=target_user,
            valid_emojis=["✅", "❌"],
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        await message.channel.send("Trade request timed out.")
        return

    if reaction_emoji == "❌":
        await message.channel.send("Trade Offer Declined.")
        return

    await message.channel.send(f"{target_user.mention}, input your return offer using `!return <Cards/Cash>`.")

    try:
        return_msg = await wait_for_message_from_user_with_prefix(
            bot,
            channel=message.channel,
            user=target_user,
            prefix="!return",
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        await message.channel.send("Return trade offer timed out.")
        return

    # Process return offer (target_user)
    return_offer_text = return_msg.content.replace("!return ", "").strip()
    try:
        return_offer_items = parse_offer_items(return_offer_text)
    except ValueError:
        await message.channel.send("Invalid cash amount in return offer.")
        return

    receiver_cash_offer = return_offer_items.cash
    try:
        receiver_cards_display, receiver_instance_ids = format_instance_ids_for_owner(
            user_id=receiver_user_id,
            instance_ids=return_offer_items.instance_ids,
            get_card_display_for_instance=repo_get_card_display_for_instance,
        )
    except ValueError as e:
        invalid_instance_id = e.args[0] if e.args else str(e)
        await message.channel.send(f"You do not own the card with Instance ID `{invalid_instance_id}`.")
        return

    if receiver_cash < receiver_cash_offer:
        await message.channel.send("You do not have enough Court Cash to make this return offer.")
        return

    receiver_offer_str = ", ".join(receiver_cards_display) + (
        f" and ${receiver_cash_offer}" if receiver_cash_offer else ""
    )

    # Final Confirmation
    confirm_msg = await message.channel.send(
        f"{sender.mention} is offering `{sender_offer_str}`.\n"
        f"{target_user.mention} is offering `{receiver_offer_str}`.\n"
        f"Do both players accept?"
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    accepted_users = set()
    try:
        while len(accepted_users) < 2:
            reaction_emoji, user = await wait_for_reaction_from_users(
                bot,
                confirm_msg,
                users=[sender, target_user],
                valid_emojis=["✅", "❌"],
                timeout=60.0,
            )
            if reaction_emoji == "❌":
                await message.channel.send("Trade Offer Declined.")
                return
            accepted_users.add(user)
    except asyncio.TimeoutError:
        await message.channel.send("Final trade confirmation timed out.")
        return

    repo_execute_trade_swap(
        sender_user_id=sender_user_id,
        receiver_user_id=receiver_user_id,
        sender_instance_ids=sender_instance_ids,
        receiver_instance_ids=receiver_instance_ids,
        sender_cash_offer=sender_cash_offer,
        receiver_cash_offer=receiver_cash_offer,
    )

    await message.channel.send(
        f"Trade Completed! `{sender_offer_str}` exchanged for `{receiver_offer_str}`."
    )

async def giveaway(message, target_user: discord.Member, giveaway: str, bot: discord.Client):
    # Giveaway a card
    sender = message.author
    sender_id = sender.id
    target_user_id = target_user.id
    # Retrieve user IDs & balances from the database
    sender_row = repo_get_user_row(sender_id)
    receiver_row = repo_get_user_row(target_user_id)

    if not sender_row or not receiver_row:
        await message.channel.send("One of the users is not found in the database.")
        return

    sender_user_id, sender_cash = sender_row
    receiver_user_id, _ = receiver_row

    # Parse giveaway details
    try:
        offer_items = parse_offer_items(giveaway)
    except ValueError:
        await message.channel.send("Invalid cash amount. Please enter a valid number.")
        return

    sender_cash_giveaway = offer_items.cash
    try:
        sender_cards_display, sender_instance_ids = format_instance_ids_for_owner(
            user_id=sender_user_id,
            instance_ids=offer_items.instance_ids,
            get_card_display_for_instance=repo_get_card_display_for_instance,
        )
    except ValueError as e:
        invalid_instance_id = e.args[0] if e.args else str(e)
        await message.channel.send(f"You do not own the card with Instance ID `{invalid_instance_id}`.")
        return

    if sender_cash < sender_cash_giveaway:
        await message.channel.send("You do not have enough Court Cash to give away.")
        return

    sender_offer_str = ", ".join(sender_cards_display) + (
        f" and ${sender_cash_giveaway}" if sender_cash_giveaway else ""
    )
    confirm_msg = await message.channel.send(
        f"{target_user.mention}, {sender.mention} is giving away `{sender_offer_str}`. Do you accept?"
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    try:
        reaction_emoji = await wait_for_reaction_from_user(
            bot,
            confirm_msg,
            user=target_user,
            valid_emojis=["✅", "❌"],
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        await message.channel.send("Giveaway request timed out.")
        return

    if reaction_emoji == "❌":
        await message.channel.send("Giveaway Declined.")
        return

    repo_execute_giveaway_transfer(
        sender_user_id=sender_user_id,
        receiver_user_id=receiver_user_id,
        sender_instance_ids=sender_instance_ids,
        sender_cash_giveaway=sender_cash_giveaway,
    )

    await message.channel.send(
        f"Giveaway Completed! `{sender_offer_str}` has been given to {target_user.mention}."
    )
