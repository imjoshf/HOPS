import ast
import random
import sqlite3
import time
from typing import Any, Iterable, Optional

from player_cards import PlayerCard

from .database import connect_db, DATABASE_NAME


# -----------------------------
# User / registration
# -----------------------------
def add_user(discord_id: str) -> None:
    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                discord_id TEXT UNIQUE
            )
            """
        )
        # Backfill/migrate expected column for court cash.
        c.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in c.fetchall()}
        if "court_cash" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN court_cash INTEGER DEFAULT 0")
        c.execute("INSERT OR IGNORE INTO users (discord_id) VALUES (?)", (discord_id,))
        conn.commit()


def get_user_id(discord_id: str) -> Optional[int]:
    conn = connect_db()
    try:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE discord_id = ?", (discord_id,))
        row = c.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_user_cash(discord_id: str) -> Optional[int]:
    conn = connect_db()
    try:
        c = conn.cursor()
        c.execute("SELECT court_cash FROM users WHERE discord_id = ?", (discord_id,))
        row = c.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_user_row(discord_id: str) -> Optional[tuple[int, int]]:
    conn = connect_db()
    try:
        c = conn.cursor()
        c.execute("SELECT user_id, court_cash FROM users WHERE discord_id = ?", (discord_id,))
        return c.fetchone()
    finally:
        conn.close()


# -----------------------------
# Cards / master catalog
# -----------------------------
def initialize_cards_table() -> None:
    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS cards (
                card_id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                position INTEGER NOT NULL,
                season_year INTEGER NOT NULL,
                stats TEXT NOT NULL,
                offensive_rating REAL NOT NULL,
                defensive_rating REAL NOT NULL,
                attributes TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS user_cards (
                instance_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                instance_number INTEGER NOT NULL,
                condition TEXT NOT NULL,
                offensive_rating REAL NOT NULL,
                defensive_rating REAL NOT NULL,
                attributes TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (card_id) REFERENCES cards (card_id)
            )
            """
        )
        conn.commit()


def sync_player_cards_to_db(player_cards: type[PlayerCard]) -> None:
    with connect_db() as conn:
        c = conn.cursor()
        for card in player_cards.cards:
            data = (
                card.card_id,
                card.player_name,
                card.position,
                card.season_year,
                str(card.stats),
                card.offensive_rating,
                card.defensive_rating,
                str(card.attributes),
            )
            c.execute(
                """
                INSERT INTO cards (card_id, player_name, position, season_year, stats, offensive_rating, defensive_rating, attributes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(card_id) DO UPDATE SET
                    player_name = excluded.player_name,
                    position = excluded.position,
                    season_year = excluded.season_year,
                    stats = excluded.stats,
                    offensive_rating = excluded.offensive_rating,
                    defensive_rating = excluded.defensive_rating,
                    attributes = excluded.attributes
                """,
                data,
            )
        conn.commit()


# -----------------------------
# Card instances (ownership)
# -----------------------------
def generate_card_instance_id() -> str:
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))


def get_random_condition() -> str:
    conditions = ["Healthy", "Injury Watch", "Injured", "Peak Condition"]
    probabilities = [0.7, 0.15, 0.1, 0.05]
    return random.choices(conditions, probabilities)[0]


def add_card_to_user(discord_id: str, player_name: str, season_year: str) -> str:
    """
    Adds a new card instance (user_cards row) and credits $100 court cash.
    Returns the human-facing condition message (matching previous behavior).
    """
    with connect_db() as conn:
        c = conn.cursor()

        c.execute("SELECT user_id, court_cash FROM users WHERE discord_id = ?", (discord_id,))
        user_row = c.fetchone()
        if not user_row:
            return "User not found in the database."

        user_id, current_cash = user_row

        c.execute(
            """
            SELECT card_id, offensive_rating, defensive_rating, attributes
            FROM cards
            WHERE LOWER(player_name) = ? AND season_year = ?
            """,
            (player_name.lower(), season_year),
        )
        card_row = c.fetchone()
        if not card_row:
            return f"Card for {player_name} ({season_year}) not found."

        card_id, offensive_rating, defensive_rating, attributes = card_row

        c.execute("SELECT MAX(instance_number) FROM user_cards WHERE card_id = ?", (card_id,))
        max_instance_number = c.fetchone()[0]
        next_instance_number = 1 if max_instance_number is None else max_instance_number + 1

        instance_id = generate_card_instance_id()
        condition = get_random_condition()

        try:
            c.execute(
                """
                INSERT INTO user_cards (instance_id, user_id, card_id, instance_number, condition, offensive_rating, defensive_rating, attributes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance_id,
                    user_id,
                    card_id,
                    next_instance_number,
                    condition,
                    offensive_rating,
                    defensive_rating,
                    attributes,
                ),
            )

            if current_cash is None:
                current_cash = 0
            new_cash_balance = current_cash + 100
            c.execute("UPDATE users SET court_cash = ? WHERE user_id = ?", (new_cash_balance, user_id))

            conn.commit()
        except sqlite3.IntegrityError as e:
            return f"An error occurred while adding the card: {str(e)}"

        condition_messages = {
            "Injured": f"You claimed {player_name}, {season_year} #{next_instance_number}, but unfortunately, he's **Injured**! You also received **$100 Court Cash**.",
            "Injury Watch": f"You claimed {player_name}, {season_year} #{next_instance_number}, but he's on **Injury Watch**. Be cautious! You also received **$100 Court Cash**.",
            "Healthy": f"You claimed {player_name}, {season_year} #{next_instance_number}, and he's **Healthy**. Good luck! You also received **$100 Court Cash**.",
            "Peak Condition": f"You claimed {player_name}, {season_year} #{next_instance_number}, and he's in **Peak Condition**! Amazing find! You also received **$100 Court Cash**.",
        }
        return condition_messages[condition]


def get_user_cards_rows(discord_id: str) -> list[tuple[Any, ...]]:
    """
    Returns rows: (player_name, season_year, instance_number, instance_id, condition)
    """
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        c = conn.cursor()
        c.execute(
            """
            SELECT cards.player_name, cards.season_year, user_cards.instance_number,
                   user_cards.instance_id AS instance_id, user_cards.condition
            FROM user_cards
            JOIN cards ON user_cards.card_id = cards.card_id
            WHERE user_cards.user_id = (SELECT user_id FROM users WHERE discord_id = ?)
            """
            ,
            (discord_id,),
        )
        return c.fetchall()
    finally:
        conn.close()


def user_owns_card(discord_id: str, player_name: str) -> tuple[bool, str]:
    conn = connect_db()
    try:
        c = conn.cursor()
        c.execute("SELECT card_id FROM cards WHERE LOWER(player_name) = LOWER(?)", (player_name,))
        card_row = c.fetchone()
        if not card_row:
            return False, "This card does not exist."
        card_id = card_row[0]

        c.execute("SELECT user_id FROM users WHERE discord_id = ?", (discord_id,))
        user_row = c.fetchone()
        if not user_row:
            return False, "User not found. Please register first."
        user_id = user_row[0]

        c.execute("SELECT 1 FROM user_cards WHERE user_id = ? AND card_id = ?", (user_id, card_id))
        if not c.fetchone():
            return False, "You don't own this card."
        return True, "Card found in your collection."
    finally:
        conn.close()


def get_card_display_for_instance(user_id: int, instance_id: str) -> Optional[tuple[str, int, str]]:
    """
    Returns (player_name, instance_number, instance_id) if the user owns the instance.
    """
    conn = connect_db()
    try:
        c = conn.cursor()
        c.execute(
            """
            SELECT cards.player_name, user_cards.instance_number, user_cards.instance_id
            FROM user_cards
            INNER JOIN cards ON user_cards.card_id = cards.card_id
            WHERE user_cards.instance_id = ? AND user_cards.user_id = ?
            """,
            (instance_id, user_id),
        )
        row = c.fetchone()
        return (row[0], row[1], row[2]) if row else None
    finally:
        conn.close()


def get_last_claimed_card_player(discord_id: str) -> Optional[PlayerCard]:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM users WHERE discord_id = ?", (discord_id,))
        user_record = cursor.fetchone()
        if user_record is None:
            return None
        hops_user_id = user_record[0]

        cursor.execute(
            """
            SELECT card_id
            FROM user_cards
            WHERE user_id = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (hops_user_id,),
        )
        card_record = cursor.fetchone()
        if card_record is None:
            return None

        last_card_id = card_record[0]
        cursor.execute("SELECT player_name FROM cards WHERE card_id = ?", (last_card_id,))
        card_info = cursor.fetchone()
        if card_info is None:
            return None

        player_name = card_info[0]
        return next(
            (card for card in PlayerCard.cards if card.player_name.lower() == player_name.lower()),
            None,
        )
    finally:
        conn.close()


def transfer_card_instances(from_user_id: int, to_user_id: int, instance_ids: Iterable[str]) -> None:
    with connect_db() as conn:
        c = conn.cursor()
        for instance_id in instance_ids:
            c.execute("UPDATE user_cards SET user_id = ? WHERE instance_id = ?", (to_user_id, instance_id))
        conn.commit()


def update_court_cash(discord_id: str, delta: int) -> None:
    with connect_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET court_cash = court_cash + ? WHERE discord_id = ?", (delta, discord_id))
        conn.commit()


def execute_trade_swap(
    sender_user_id: int,
    receiver_user_id: int,
    sender_instance_ids: Iterable[str],
    receiver_instance_ids: Iterable[str],
    sender_cash_offer: int,
    receiver_cash_offer: int,
) -> None:
    """
    Atomically swaps ownership of card instances and exchanges court cash.
    """
    with connect_db() as conn:
        c = conn.cursor()
        for instance_id in sender_instance_ids:
            c.execute("UPDATE user_cards SET user_id = ? WHERE instance_id = ?", (receiver_user_id, instance_id))
        for instance_id in receiver_instance_ids:
            c.execute("UPDATE user_cards SET user_id = ? WHERE instance_id = ?", (sender_user_id, instance_id))

        # Cash exchange:
        # - sender loses sender_cash_offer, gains receiver_cash_offer
        # - receiver loses receiver_cash_offer, gains sender_cash_offer
        c.execute("UPDATE users SET court_cash = court_cash - ? WHERE user_id = ?", (sender_cash_offer, sender_user_id))
        c.execute("UPDATE users SET court_cash = court_cash + ? WHERE user_id = ?", (sender_cash_offer, receiver_user_id))
        c.execute("UPDATE users SET court_cash = court_cash - ? WHERE user_id = ?", (receiver_cash_offer, receiver_user_id))
        c.execute("UPDATE users SET court_cash = court_cash + ? WHERE user_id = ?", (receiver_cash_offer, sender_user_id))

        conn.commit()


def execute_giveaway_transfer(
    sender_user_id: int,
    receiver_user_id: int,
    sender_instance_ids: Iterable[str],
    sender_cash_giveaway: int,
) -> None:
    """
    Atomically transfers ownership of card instances and court cash.
    """
    with connect_db() as conn:
        c = conn.cursor()
        for instance_id in sender_instance_ids:
            c.execute("UPDATE user_cards SET user_id = ? WHERE instance_id = ?", (receiver_user_id, instance_id))

        c.execute("UPDATE users SET court_cash = court_cash - ? WHERE user_id = ?", (sender_cash_giveaway, sender_user_id))
        c.execute("UPDATE users SET court_cash = court_cash + ? WHERE user_id = ?", (sender_cash_giveaway, receiver_user_id))

        conn.commit()


# -----------------------------
# Teams
# -----------------------------
TEAM_SLOT_COLUMNS = ["point_guard", "shooting_guard", "small_forward", "power_forward", "center", "sixth_man"]


def create_user_team(discord_id: str, team_name: str, instance_ids: list[str]) -> str:
    if len(instance_ids) != 6:
        return "You must provide exactly six instance IDs, one for each position."

    user_id = get_user_id(discord_id)
    if user_id is None:
        return "User not found. Use `!cards` first to add yourself to the database."

    with connect_db() as conn:
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS teams (
                user_id INTEGER PRIMARY KEY,
                team_name TEXT,
                point_guard TEXT,
                shooting_guard TEXT,
                small_forward TEXT,
                power_forward TEXT,
                center TEXT,
                sixth_man TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        c.execute("SELECT team_name FROM teams WHERE user_id = ?", (user_id,))
        existing_team = c.fetchone()
        if existing_team:
            return f"You already have a team named '{existing_team[0]}'. Use `!rename_team` to make changes to it."

        placeholders = ", ".join(["?"] * 6)
        c.execute(
            f"SELECT card_id, instance_id FROM user_cards WHERE user_id = ? AND instance_id IN ({placeholders})",
            (user_id, *instance_ids),
        )
        owned_cards = c.fetchall()
        if len(owned_cards) != 6:
            return "One or more instance IDs are invalid or do not belong to you."

        card_ids = [card[0] for card in owned_cards]
        if len(set(card_ids)) != 6:
            return "You cannot use the same player in multiple positions."

        c.execute(
            """
            INSERT INTO teams (user_id, team_name, point_guard, shooting_guard, small_forward, power_forward, center, sixth_man)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, team_name, *instance_ids),
        )
        conn.commit()

    return f"Team '{team_name}' created successfully!"


def change_team_name(discord_id: str, new_team_name: str) -> str:
    user_id = get_user_id(discord_id)
    if user_id is None:
        return "User not found. Use `!cards` first to add yourself to the database."

    with connect_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE teams SET team_name = ? WHERE user_id = ?", (new_team_name, user_id))
        conn.commit()
    return f"Team name updated to '{new_team_name}'!"


def update_team_position(discord_id: str, selected_position: str, instance_id: str) -> str:
    user_id = get_user_id(discord_id)
    if user_id is None:
        return "You need to be registered first. Use `!cards` to register."

    with connect_db() as conn:
        c = conn.cursor()

        c.execute("SELECT team_name FROM teams WHERE user_id = ?", (user_id,))
        team_row = c.fetchone()
        if not team_row:
            return "You don't have a team yet! Use `!team <team_name>` first."

        c.execute("SELECT card_id FROM user_cards WHERE instance_id = ? AND user_id = ?", (instance_id, user_id))
        card_row = c.fetchone()
        if not card_row:
            return "You do not own this card or the instance ID is incorrect."

        if selected_position not in TEAM_SLOT_COLUMNS:
            return "Invalid team position."

        c.execute(f"UPDATE teams SET {selected_position} = ? WHERE user_id = ?", (instance_id, user_id))
        conn.commit()

    return f"Your {selected_position.replace('_', ' ').title()} has been updated!"


def user_has_team(discord_id: str) -> bool:
    user_id = get_user_id(discord_id)
    if user_id is None:
        return False
    conn = connect_db()
    try:
        c = conn.cursor()
        c.execute("SELECT 1 FROM teams WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None
    finally:
        conn.close()


def view_team_display(discord_id: str) -> str:
    user_id = get_user_id(discord_id)
    if user_id is None:
        return "User not found. Use `!cards` first to add yourself to the database."

    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT team_name, point_guard, shooting_guard, small_forward, power_forward, center, sixth_man FROM teams WHERE user_id = ?",
            (user_id,),
        )
        team = c.fetchone()
        if team is None:
            return "You do not have a team yet. Use `!team create <team_name>` to create one."

        team_name, pg, sg, sf, pf, c_, sm = team

        # Bulk resolve instance_id -> (player_name, instance_number) with joins
        instance_ids = [x for x in [pg, sg, sf, pf, c_, sm] if x]
        if instance_ids:
            placeholders = ", ".join(["?"] * len(instance_ids))
            c.execute(
                f"""
                SELECT uc.instance_id, cards.player_name, uc.instance_number
                FROM user_cards uc
                JOIN cards ON uc.card_id = cards.card_id
                WHERE uc.instance_id IN ({placeholders})
                """,
                instance_ids,
            )
            rows = c.fetchall()
            resolved = {row[0]: f"{row[1]} #{row[2]}" for row in rows}
        else:
            resolved = {}

        def get_player(instance_id: Optional[str]) -> str:
            if not instance_id:
                return "Empty"
            return resolved.get(instance_id, "Empty")

        return (
            f"**{team_name}**\n"
            f"🏀 Point Guard: {get_player(pg)}\n"
            f"🏀 Shooting Guard: {get_player(sg)}\n"
            f"🏀 Small Forward: {get_player(sf)}\n"
            f"🏀 Power Forward: {get_player(pf)}\n"
            f"🏀 Center: {get_player(c_)}\n"
            f"🏀 Sixth Man: {get_player(sm)}"
        )


# -----------------------------
# Game-oriented team data
# -----------------------------
def get_team_data_for_game(discord_id: str) -> tuple[Optional[str], Optional[list[dict[str, Any]]]]:
    """
    Returns (team_name, team_data) where team_data is a list of dicts containing:
    - player_name, position, offensive_rating, defensive_rating, attributes
    Mirrors the structure previously returned by HOPS_game.get_team_data.
    """
    user_id = get_user_id(discord_id)
    if user_id is None:
        return None, None

    with connect_db() as conn:
        c = conn.cursor()
        c.execute("SELECT team_name FROM teams WHERE user_id = ?", (user_id,))
        team_name_row = c.fetchone()
        if not team_name_row:
            return None, None
        team_name = team_name_row[0]

        c.execute(
            "SELECT point_guard, shooting_guard, small_forward, power_forward, center, sixth_man FROM teams WHERE user_id = ?",
            (user_id,),
        )
        row = c.fetchone()
        if not row:
            return team_name, []

        instance_ids_by_slot = dict(zip(TEAM_SLOT_COLUMNS, row))
        team_data: list[dict[str, Any]] = []

        for slot in TEAM_SLOT_COLUMNS:
            instance_id = instance_ids_by_slot.get(slot)
            if not instance_id:
                continue

            c.execute("SELECT card_id FROM user_cards WHERE instance_id = ?", (instance_id,))
            uc_row = c.fetchone()
            if not uc_row:
                continue
            card_id = uc_row[0]

            c.execute(
                """
                SELECT player_name, position, offensive_rating, defensive_rating, attributes
                FROM cards
                WHERE card_id = ?
                """,
                (card_id,),
            )
            player_row = c.fetchone()
            if not player_row:
                continue

            player_name, position, offensive_rating, defensive_rating, attributes = player_row
            # Cast to floats where appropriate
            try:
                offensive_rating = float(offensive_rating)
            except Exception:
                offensive_rating = 0.0
            try:
                defensive_rating = float(defensive_rating)
            except Exception:
                defensive_rating = 0.0

            # Preserve previous behavior (attributes string, or list-like if stored that way)
            attrs_out: Any
            if isinstance(attributes, str):
                try:
                    parsed = ast.literal_eval(attributes)
                    attrs_out = parsed if parsed is not None else []
                except Exception:
                    attrs_out = attributes
            else:
                attrs_out = attributes

            team_data.append(
                {
                    "card_id": card_id,
                    "player_name": player_name,
                    "position": position,
                    "offensive_rating": offensive_rating,
                    "defensive_rating": defensive_rating,
                    "attributes": attrs_out if attrs_out is not None else [],
                }
            )

        return team_name, team_data


def get_team_full_data_for_discord(discord_id: str) -> tuple[Optional[str], Optional[dict[str, dict[str, Any]]]]:
    """
    Loads all 6 team slots into a single dict so the service layer can render
    the team view and build game-ready ratings without duplicating DB logic.

    Returns: (team_name, slots)
      - slots maps slot_key -> dict(instance_id, instance_number, player_name, position, offensive_rating, defensive_rating, attributes)
    """
    user_id = get_user_id(discord_id)
    if user_id is None:
        return None, None

    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT team_name, point_guard, shooting_guard, small_forward, power_forward, center, sixth_man FROM teams WHERE user_id = ?",
            (user_id,),
        )
        team_row = c.fetchone()
        if not team_row:
            return None, None

        team_name = team_row[0]
        slot_values = team_row[1:]

        slots: dict[str, dict[str, Any]] = {}
        for slot_key, instance_id in zip(TEAM_SLOT_COLUMNS, slot_values):
            if not instance_id:
                continue

            c.execute(
                """
                SELECT uc.instance_id,
                       uc.instance_number,
                       cards.player_name,
                       cards.position,
                       cards.offensive_rating,
                       cards.defensive_rating,
                       cards.attributes,
                       uc.card_id
                FROM user_cards uc
                JOIN cards ON uc.card_id = cards.card_id
                WHERE uc.instance_id = ?
                """,
                (instance_id,),
            )
            row = c.fetchone()
            if not row:
                continue

            instance_id_out, instance_number, player_name, position, off_rating, def_rating, attributes, card_id = row

            try:
                off_rating = float(off_rating)
            except Exception:
                off_rating = 0.0
            try:
                def_rating = float(def_rating)
            except Exception:
                def_rating = 0.0

            slots[slot_key] = {
                "instance_id": instance_id_out,
                "instance_number": instance_number,
                "player_name": player_name,
                "position": position,
                "offensive_rating": off_rating,
                "defensive_rating": def_rating,
                "attributes": attributes,
                "card_id": card_id,
            }

        return team_name, slots

