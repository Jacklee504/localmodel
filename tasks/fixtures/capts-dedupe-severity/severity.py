"""Severity lookup for pipeline changes."""

SEVERITIES = {
    "removed": 1.0,
    "renamed": 0.9,
    "dependency_removed": 0.8,
    "modified": 0.7,
    "value_changed": 0.5,
    "dependency_added": 0.2,
}


def severity_for(change_type):
    """Return the severity weight for a change type."""
    return SEVERITIES.get(change_type, 0.0)


def severity_label(change_type):
    """Return a human label for a change type."""
    if change_type not in SEVERITIES:
        return "unknown"
    if SEVERITIES[change_type] >= 0.7:
        return "high"
    if SEVERITIES[change_type] >= 0.4:
        return "medium"
    return "low"
