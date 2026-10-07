cache = {}


def get_report(user_id, filters, build):
    key = tuple(sorted(filters.items()))
    if key not in cache:
        cache[key] = build(user_id, filters)
    return cache[key]
