from __future__ import annotations

from typing import Callable, Optional

from domain.trade_offer import TradeOffer


def parse_offer_items(offer_text: str) -> TradeOffer:
    """
    Parses strings like: "$100 <instance_id> <instance_id>".
    Tokens not starting with "$" are treated as card instance IDs.
    """
    tokens = offer_text.strip().split()
    cash = 0
    instance_ids: list[str] = []

    for token in tokens:
        if token.startswith("$"):
            try:
                cash = int(token[1:])
            except ValueError as e:
                raise ValueError(f"Invalid cash token: {token}") from e
        else:
            instance_ids.append(token)

    return TradeOffer(cash=cash, instance_ids=instance_ids)


def format_instance_ids_for_owner(
    *,
    user_id: int,
    instance_ids: list[str],
    get_card_display_for_instance: Callable[[int, str], Optional[tuple[str, int, str]]],
) -> tuple[list[str], list[str]]:
    """
    Validates each instance_id belongs to user_id via get_card_display_for_instance.
    Returns (display_strings, resolved_instance_ids).
    """
    display_strings: list[str] = []
    resolved_instance_ids: list[str] = []

    for instance_id in instance_ids:
        card = get_card_display_for_instance(user_id, instance_id)
        if not card:
            # Preserve the original invalid token for error messages in the caller.
            raise ValueError(instance_id)
        player_name, instance_number, resolved_instance_id = card
        resolved_instance_ids.append(resolved_instance_id)
        display_strings.append(f"{player_name} #{instance_number} ({resolved_instance_id})")

    return display_strings, resolved_instance_ids

