from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class TeamSlot:
    instance_id: Optional[str]
    instance_number: Optional[int]
    player_name: Optional[str]
    position: Optional[str]
    card_id: Optional[int]
    offensive_rating: float
    defensive_rating: float
    attributes: Any = None


@dataclass(frozen=True)
class Team:
    team_name: str
    point_guard: TeamSlot
    shooting_guard: TeamSlot
    small_forward: TeamSlot
    power_forward: TeamSlot
    center: TeamSlot
    sixth_man: TeamSlot

    def slots_in_order(self) -> list[tuple[str, TeamSlot]]:
        return [
            ("point_guard", self.point_guard),
            ("shooting_guard", self.shooting_guard),
            ("small_forward", self.small_forward),
            ("power_forward", self.power_forward),
            ("center", self.center),
            ("sixth_man", self.sixth_man),
        ]

