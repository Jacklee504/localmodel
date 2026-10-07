# Task loader requirements

`load_tasks(path)` reads a UTF-8 JSON file containing an object with a `tasks` list.
Each task must be an object with a nonblank string `id` and `prompt`.
IDs must be unique. An empty task list is invalid.
Return the task list in source order, preserving extra fields.
Raise `ValueError` for invalid JSON, unreadable files, wrong shapes, missing
fields, blank values, or duplicate IDs. Include the task index or ID in errors
where useful. Do not silently skip malformed entries.
