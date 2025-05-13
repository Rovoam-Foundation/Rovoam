from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from json import load, dump

try: 
    with open("cli.conf.json") as f:
        config = load(f)
except FileNotFoundError:
    config = {
        "module": "network",
        "object": "superviser",
        "name": "Rovoam",
        "first_run": "yes",
        "auto_confirm": ""
    }
    with open("cli.conf.json", "w") as f:
        dump(config, f)
    exit("Default config created. Edit it (if needed) and try again.")

def confirmation_handler(toolname, description):
    table = {
        "y": True,
        "n": False
    }
    if toolname in config["auto_confirm"].split(" "):
        return True
    console.print(Panel(f"Tool: {toolname}\nFull call: {description}", border_style="blue", title="Confirmation"))
    inp = Prompt.ask("Confirmation", default="Y", choices=["Y", "n"], case_sensitive=False).lower()
    return table[inp]