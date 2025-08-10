from json import load, dump
from os import path

try:
    with open(path.expanduser("~/Rovoam/conf.json"), "r") as f:
        config = load(f)
except FileNotFoundError:
    config = {
        "first_run": "yes",
        "api_key": None,
        "api_endpoint": None,
        "auto_confirm": []
    }
    with open(path.expanduser("~/Rovoam/conf.json"), "w") as f:
        dump(config, f)
    print("Default config created. Edit it (add API key) and try again.")
    exit(0)
