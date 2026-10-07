def summarize(records):
    scores = [record["score"] for record in records]
    return {"total": len(scores), "scored": len(scores), "successful": sum(score == 2 for score in scores),
            "average_score": sum(scores) / len(scores)}
