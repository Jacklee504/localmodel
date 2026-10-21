"""A small ledger of deal records."""


def normalise_entry(entry):
    """Return the entry with its amount as an int and its kind lowercased."""
    amount = entry.get("amount", 0)
    kind = entry.get("kind", "")
    return {"amount": int(amount), "kind": kind.lower(), "ref": entry.get("ref")}


def total_amount(entries):
    """Return the sum of the normalised amounts."""
    return sum(normalise_entry(entry)["amount"] for entry in entries)


def group_by_kind(entries):
    """Return a mapping of kind to the number of entries with that kind."""
    counts = {}
    for entry in entries:
        kind = normalise_entry(entry)["kind"]
        counts[kind] = counts.get(kind, 0) + 1
    return counts
