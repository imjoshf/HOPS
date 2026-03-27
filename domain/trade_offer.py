from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeOffer:
    """
    A parsed offer: a court cash amount plus a list of card instance IDs.
    """

    cash: int
    instance_ids: list[str]

