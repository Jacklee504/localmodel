from store import save


def put(db, key, value):
    save(db, key, value)
    return {"ok": True}
