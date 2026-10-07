import json


def load_models(path):
    return json.loads(open(path, encoding="utf-8").read())["models"]
