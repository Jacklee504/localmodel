import json


def load_tasks(path):
    return json.loads(open(path, encoding="utf-8").read())["tasks"]
