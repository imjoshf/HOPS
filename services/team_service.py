from __future__ import annotations

import ast
from typing import Any, Optional

from domain.card_instance import CardInstance
from domain.team import Team, TeamSlot
from storage.repositories import get_team_full_data_for_discord


# Note: We keep this service as the single place that transforms persisted
# team slot rows into the objects used by both display and game simulation.


def _parse_attributes(attrs: Any) -> Any:
    if attrs is None:
        return []
    if not isinstance(attrs, str):
        return attrs
    try:
        parsed = ast.literal_eval(attrs)
        return parsed if parsed is not None else []
    except Exception:
        return attrs


def get_team_from_db(discord_id: str) -> Optional[Team]:
    """
    Loads a 6-slot team and returns a domain Team object.
    """
    team_name, full_slots = get_team_full_data_for_discord(discord_id)
    if team_name is None or full_slots is None:
        return None

    def slot_or_empty(slot_key: str) -> TeamSlot:
        raw = full_slots.get(slot_key) if full_slots else None
        if not raw:
            return TeamSlot(
                instance_id=None,
                instance_number=None,
                player_name=None,
                position=None,
                card_id=None,
                offensive_rating=0.0,
                defensive_rating=0.0,
                attributes=[],
            )
        return TeamSlot(
            instance_id=raw["instance_id"],
            instance_number=raw["instance_number"],
            player_name=raw["player_name"],
            position=raw["position"],
            card_id=raw.get("card_id"),
            offensive_rating=raw["offensive_rating"],
            defensive_rating=raw["defensive_rating"],
            attributes=raw.get("attributes", []),
        )

    # full_slots keys should match TEAM_SLOT_COLUMNS
    return Team(
        team_name=team_name,
        point_guard=slot_or_empty("point_guard"),
        shooting_guard=slot_or_empty("shooting_guard"),
        small_forward=slot_or_empty("small_forward"),
        power_forward=slot_or_empty("power_forward"),
        center=slot_or_empty("center"),
        sixth_man=slot_or_empty("sixth_man"),
    )


def render_team_view(team: Team) -> str:
    def get_player_text(slot: TeamSlot) -> str:
        if not slot.instance_id or not slot.player_name or slot.instance_number is None:
            return "Empty"
        return f"{slot.player_name} #{slot.instance_number}"

    parts = [f"**{team.team_name}**"]
    for slot_key, slot in team.slots_in_order():
        label = slot_key.replace("_", " ").title()
        emoji = "🏀"
        parts.append(f"{emoji} {label}: {get_player_text(slot)}")
    return "\n".join(parts)


def build_game_team_data(team: Team) -> list[CardInstance]:
    """
    Builds a list of CardInstance objects for the game simulation.
    """
    out: list[CardInstance] = []
    for _slot_key, slot in team.slots_in_order():
        if not slot.instance_id or not slot.player_name:
            continue
        out.append(
            CardInstance(
                instance_id=slot.instance_id,
                card_id=slot.card_id,
                player_name=slot.player_name,
                position=slot.position,
                offensive_rating=float(slot.offensive_rating),
                defensive_rating=float(slot.defensive_rating),
                attributes=_parse_attributes(slot.attributes),
            )
        )
    return out


def get_team_game_team_data(discord_id: str) -> tuple[Optional[str], Optional[list[CardInstance]]]:
    team = get_team_from_db(discord_id)
    if team is None:
        return None, None
    return team.team_name, build_game_team_data(team)


def calculate_off_def_totals(team_data: list[CardInstance]) -> tuple[float, float]:
    total_off = sum(float(player.offensive_rating or 0) for player in team_data)
    total_def = sum(float(player.defensive_rating or 0) for player in team_data)
    return total_off, total_def

