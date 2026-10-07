def save_new(name, age):
    return ("new", name, age)


def save_existing(user_id, name, age):
    return (user_id, name, age)


def create_user(name, age):
    if not name:
        raise ValueError("name required")
    if age < 0:
        raise ValueError("age invalid")
    return save_new(name, age)


def update_user(user_id, name, age):
    if not name:
        raise ValueError("name required")
    if age < 0:
        raise ValueError("age invalid")
    return save_existing(user_id, name, age)
