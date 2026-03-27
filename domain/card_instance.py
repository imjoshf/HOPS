from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class CardInstance:
    instance_id: Optional[str]
    card_id: Optional[int]
    player_name: Optional[str]
    position: Optional[str]
    offensive_rating: float
    defensive_rating: float
    attributes: Any = None

