from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from config import config

console = Console()

def confirmation_handler(toolname, description):
    table = {
        "y": True,
        "n": False
    }
    if toolname in config["auto_confirm"]:
        return True
    console.print(Panel(f"Tool: {toolname}\nFull call: {description}", border_style="blue", title="Confirmation"))
    inp = Prompt.ask("Confirmation", default="Y", choices=["Y", "n"], case_sensitive=False).lower()
    return table[inp]
