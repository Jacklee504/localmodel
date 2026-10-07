def score_label(score):
    if not isinstance(score, int) or isinstance(score, bool) or score not in (0, 1, 2):
        raise ValueError("score must be 0, 1 or 2")
    return ("failed", "partial", "successful")[score]
