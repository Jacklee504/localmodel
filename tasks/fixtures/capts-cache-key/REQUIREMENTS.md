# Cache key bug

`cache.py` caches pipeline runs. The cache key is built from the pipeline name and the
filters used, but filters arrive as a dictionary, so the key order depends on how the
caller happened to build the dictionary.

Two callers asking for the same filters in a different order must hit the same cache
entry. Right now they do not, and every miss re-runs an expensive pipeline.

## Requirements

1. The cache key must be identical for two filter dictionaries that contain the same
   items regardless of insertion order.
2. The cache key must still distinguish different filter values.
3. The cache key must distinguish different pipeline names.
4. A filter value that is itself a list or a dict must be handled so that two equal
   values produce the same key.
5. Do not change the public names `build_key` and `get_cached`.
6. Do not change the behaviour of `get_cached` beyond fixing the key.
