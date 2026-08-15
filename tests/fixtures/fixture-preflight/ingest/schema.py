"""Per-partner column rules and the row validation pass."""

RULES = {
    "acme": {"required": ["order_id", "sku", "qty"], "int_cols": ["qty"]},
    "globex": {"required": ["ref", "amount", "currency"], "int_cols": []},
}


def validate_row(partner_id: str, row: dict):
    """Return a short description of the first failing rule, or None if the row is good."""
    rules = RULES.get(partner_id)
    if rules is None:
        return f"no schema declared for partner {partner_id}"

    for col in rules["required"]:
        if not row.get(col):
            return f"missing required column {col}"

    for col in rules["int_cols"]:
        try:
            int(row[col])
        except (TypeError, ValueError):
            return f"column {col} is not an integer"

    return None
