"""Caching for pipeline runs."""


def build_key(pipeline, filters):
    """Build the cache key for a pipeline run."""
    return (pipeline, tuple(filters.items()))


def get_cached(store, pipeline, filters, build):
    """Return a cached result, building it when it is not cached."""
    key = build_key(pipeline, filters)
    if key not in store:
        store[key] = build(pipeline, filters)
    return store[key]
