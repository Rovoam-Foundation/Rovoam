from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
import base64
from json import load, dump
from network import supervisor as main_agent
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
import sys
from config import config

console = Console()
markdown_enabled = False

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

name = "Rovoam"

def printhelp():
    help = """
## Basics
- In addition to just sending messages to the AI, you can use special commands.
- All commands start with /
- Commands **can** take arguments: `/command arg1 arg2 ...`
- Example: `/image file ./img.jpg`
## List of commands
- help — отображение этой справки
- exit — выход из программы
- image [type] [path or URL] — send image. Example: `/image file ./img.jpg` or `/image url http://...`
- messages — показать все сообщения
- clear — clear history
- trace — show last agent's trace
- markdown [on/off] — turns Markdown hilighting (`/markdown on`, `/markdown off`). By default: off.
"""
    console.print(Panel(Markdown(help), title="Help", border_style="blue"))

def load_image(*args):
    # args: [type, [value]]
    type = None
    value = None
    # Parse args, fallback to prompt if missing
    if len(args) >= 1:
        type = args[0]
        if type not in ["file", "url"]:
            console.print("[red]Incorretc type. Use 'file' or 'url'.")
            return
        if len(args) >= 2:
            value = args[1]
    else:
        type = Prompt.ask("Image type", choices=["file", "url"])

    match type:
        case "file":
            if value is None:
                value = Prompt.ask("[green]path")
            try:
                base64_str = encode_image(value)
                main_agent.image(f"data:image/jpeg;base64,{base64_str}")
            except Exception as e:
                console.print(f"[red]Error loading file: {e}")
        case "url":
            if value is None:
                value = Prompt.ask("[green]URL")
            main_agent.image(value)

def run_interactive():
    global markdown_enabled
    while True:
        if config["first_run"] == "yes":
            inp = Prompt.ask(f"[green]This is your first run of the program. Do you need [blue]totorial?", choices=["Y", "n"], default="Y").lower()
            config["first_run"] = "no"
            with open("conf.json", "w") as f:
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
        if message.startswith("/"):
            parts = message[1:].split()
            if not parts:
                console.print("[red]Пустая команда. Используйте /help для списка команд.")
            else:
                cmd = parts[0]
                args = parts[1:]
                match cmd:
                    case "help":
                        printhelp()
                    case "exit":
                        exit(0)
                    case "image":
                        load_image(*args)
                    case "messages":
                        console.print(Panel(str(main_agent.messages)))
                    case "clear":
                        main_agent.reset()
                    case "trace":
                        console.print(Panel(main_agent.last_trace))
                    case "markdown":
                        if len(args) != 1 or args[0] not in ("on", "off"):
                            console.print("[red]Использование: /markdown on|off")
                        else:
                            markdown_enabled = (args[0] == "on")
                            status = "включена" if markdown_enabled else "выключена"
                            console.print(f"[blue]Подсветка Markdown {status}")
                    case _:
                        console.print("[green]/help [blue]to get list of commands.")
        else:
            console.print(f"[red] {name}")
            response = main_agent(message)
            if markdown_enabled:
                console.print(Markdown(str(response)))
            else:
                console.print(response)    

def run_cli(args):
    global markdown_enabled
    message = " ".join(args)

    while True:
        if message.strip() == "":
            message = Prompt.ask(f"[green]Введите запрос для [red]{name}[/red]")
        console.print(f"[red] {name}")
        response = main_agent(message)
        if markdown_enabled:
            console.print(Markdown(str(response)))
        else:
            console.print(response)
        proceed = Prompt.ask("[green]Завершить чат? [y/n]", choices=["y", "n"], default="y").lower()
        if proceed == "y":
            break
        run_interactive()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Arguments provided, run CLI mode
        run_cli(sys.argv[1:])
    else:
        # No arguments, run interactive mode
        run_interactive()
