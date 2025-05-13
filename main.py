from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

import base64
from json import load, dump
from importlib import import_module

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.document import Document

console = Console()

try:
    with open("cli.conf.json", "r") as f:
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

main_agent = getattr(import_module(config["module"]), config["object"])
name = config["name"]

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def printhelp():
    help = """
## Basics
- In addition to simple messages to the AI, commands can be used.
- All commands start with /
- Commands do not take arguments
## List of commands
- help - help command
- exit - exit
- image - image upload dialog menu
- messages - displays all messages (bad)
- clear - reset messages
- trace - print last agent trace
"""
    console.print(Panel(Markdown(help), title="Help", border_style="blue"))

def load_image():
    type = Prompt.ask("Image type", choices=["file", "url"])
    match type:
        case "file":
            path = Prompt.ask("[green]path")
            base64_str = encode_image(path)
            main_agent.image(f"data:image/jpeg;base64,{base64_str}")
        case "url":
            url = Prompt.ask("[green]URL")
            main_agent.image(url)

while True:
    if config["first_run"] == "yes":
        inp = Prompt.ask(f"[green]This is your first run of the program. Do you need [blue]totorial?", choices=["Y", "n"], default="Y").lower()
        config["first_run"] = "no"
        with open("cli.conf.json", "w") as f:
            dump(config, f)
        if inp == "y":
            console.print(Panel(Markdown("""## Messages
Write your message and send using Shift+TAB, a new line can be added with Enter
## Commands
Commands start with / and a full list of commands can be found using /help"""), title="Tutorial", border_style="Blue"))

    console.print(f"[green]Send message to [red]{name}:")

    bindings = KeyBindings()
    @bindings.add('s-tab')
    def _(event):
        buffer = event.app.current_buffer
        event.app.exit(result=buffer.text)
 
    @bindings.add('enter')
    def _(event):
        buffer = event.app.current_buffer
        buffer.insert_text("\n")

    session = PromptSession(key_bindings=bindings, multiline=True)
    with patch_stdout():
        message = session.prompt("")
    console.print(Panel(Markdown(message), title="User", border_style="green"))
    if message.startswith("/"):
        match message:
            case "/help":
                printhelp()
            case "/exit":
                exit(0)
            case "/image":
                load_image()
            case "/messages":
                console.print(Panel(str(main_agent.messages)))
            case "/clear":
                main_agent.reset()
            case "/trace":
                console.print(Panel(main_agent.last_trace))
            case _:
                console.print("[green]/help [blue]to get list of commands.")
    else:
        console.print(Panel(Markdown(main_agent(message)), title=name, border_style="red"))
