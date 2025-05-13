from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.prompt import Prompt
import re
import json

def GetReActPrompt(tools: list=None):
    # Build the documentation string for tools, including their __doc__.
    if tools:
        tool_docs = []
        for tool in tools:
            doc = getattr(tool, "__doc__", None)
            if doc and doc.strip():
                tool_docs.append(f"{doc.strip()}")
            else:
                tool_docs.append(f"(No documentation provided)")
        tools_docs = "\n".join(tool_docs)
    else:
        tools_docs = "(No tools available.)"

    return f"""
    You run in a loop of Thought, Action, PAUSE, Observation.
    At the end of the loop you output an Answer. 
    Use Thought to describle your thoughts about the question you have been asked.
    Use Action (if needed) to run one of the tools available to you. (Don't use Markdown in Action)
    When calling actions, use the JSON format.
    Observation will be the result of running those tools.
    
    VERY IMPORTANT:
    - Only use the Action step if you REALLY need to use a tool to answer the question.
    - If you do NOT need to use any tool, DO NOT output an Action step at all. Go directly to Answer.
    - NEVER output fake or empty Action steps like "Action: no need", "Action: none", or similar. This BREAKS the workflow and is forbidden!
    - Action must be a valid tool invocation in correct JSON format. Do not invent or summarize tool usage.
    - If you make an Action, always follow it by PAUSE, and wait for Observation.
    - Until you give an Answer in the correct format the loop will continue.

    Available tools:

    {tools_docs}
    
    Example session:
    
    Question: How much would 200 rubles be in dollars?
    
    Thought: I need to use a currency converter
    Action: {{
        "tool": "currencyConverter",
        "inCurrency": "RUB",
        "value": 200,
        "outCurrency": "USD"
    }}
    PAUSE
    (end of your message)

    (you will be called again)

    (System) Observation: 2,42

    (Output the final answer)
    Answer: 200 rubles is 2.42 dollars.

    INCORRECT USAGE EXAMPLES (do NOT do this!):
    Thought: Можно ответить без инструментов
    Action: нет необходимости
    PAUSE

    CORRECT: Just write an Answer block if no tool is needed.

    Now it's your turn:
    """

def GetClassifierPrompt(categories: list):
    return f"""
    Your task is to categorize the received text. When you receive a message from a user, reply with the category to which the text most closely fits. 

    VERY IMPORTANT:
    - Never say anything other than the name of the category.
    - Don't reply with categories that don't exist.

    Categories:
    {categories}
    """

class Agent():
    def __init__(
        self,
        client: object,
        model: str,
        system: str=None,
        description: str="",
        tools: list=None,
        maxIterations: int=10,
        verbose: bool=False,
        reset_messages: bool=False,
        confirmation_handler: callable=None
        ):
        """
        Agent supporting инструментальный стиль и механизм запроса подтверждения действий.
        :param confirmation_handler: функция вида handler(reason: str) -> bool,
            должна вернуть True если действие разрешено, False если нет.
            Если не задан — выполнение инструментов запрещено.
        """
        self.client = client
        self.model = model
        self.system = system
        self.__doc__ = description
        self.messages = []
        self.reset_messages = reset_messages
        self.tools = tools
        self.verbose = verbose
        self.maxIterations = maxIterations
        self.last_trace = None  # Store the last trace from the most recent call to exec
        self.confirmation_handler = confirmation_handler
        # Recursively set confirmation_handler for all Agent tools
        def set_handler_recursively(tool):
            # Import Agent locally to avoid issues if not imported at top-level
            if tool is self:
                return
            if hasattr(tool, "__class__") and tool.__class__.__name__ == "Agent":
                tool.confirmation_handler = confirmation_handler
                if hasattr(tool, "tools") and isinstance(tool.tools, list):
                    for subtool in tool.tools:
                        set_handler_recursively(subtool)
        if self.tools:
            for tool in self.tools:
                set_handler_recursively(tool)
        self.reset()

    def __call__(self, message: str=None, role: str="user", call: bool=True, return_trace: bool=None):
        if self.reset_messages:
            self.reset()
        if message is not None:
            self.messages.append({"role": role, "content": message})
        if call == True:
            if return_trace is not None:
                result = self.exec(return_trace=return_trace)
            else:
                result = self.exec(return_trace=self.verbose)
            self.messages.append({"role": "assistant", "content": result})
            return result

    def reset(self):
        self.messages = []
        self.messages.append({"role": "system", "content": GetReActPrompt(self.tools)})
        if self.system is not None:
            self.messages.append({"role": "system", "content": self.system})

    def exec(self, return_trace):
        process_trace = []
    
        # Map tool "names" to callables
        tool_map = {}
        if self.tools:
            for tool in self.tools:
                # Try to get a name from 'name', else __name__, else description, else class name
                name = getattr(tool, "name", None)
                if not name:
                    name = getattr(tool, "__name__", None)
                if not name:
                    descr = getattr(tool, "description", None) or getattr(tool, "__doc__", None)
                    if descr and isinstance(descr, str):
                        m = re.match(r"\s*([^\s:]+)", descr.strip())
                        if m:
                            name = m.group(1).strip()
                if not name:
                    name = tool.__class__.__name__
                tool_map[name] = tool
    
        for iteration in range(self.maxIterations):
            # Compose the API call to the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
            )
            # Handle multimodal or text response from assistant
            assistant_msg = response.choices[0].message
            # If OpenAI API (v2+), .message.content can be string or list of content blocks
            content = getattr(assistant_msg, "content", None)
            if isinstance(content, list):
                # Attempt to recover as text, else store multimodal content
                # For logging, flatten to text for process_trace
                flat_txt = "\n".join([
                    cb.get("text", cb.get("image_url", str(cb)))
                    for cb in content
                ])
                self.messages.append({"role": "assistant", "content": content})
                process_trace.append("Assistant:\n" + flat_txt)
            else:
                # Plain text response
                content = content.strip() if content else response.choices[0].text.strip()
                self.messages.append({"role": "assistant", "content": content})
                process_trace.append("Assistant:\n" + content)
    
            # Check for 'Answer:'
            if "Answer:" in content:
                break
    
            # Look for Action/PAUSE pattern
            m = re.search(r'Action:\s*({.*?})\s*PAUSE', content, re.DOTALL)
            if m:
                action_json = m.group(1)
                try:
                    action = json.loads(action_json)
                    toolname = action.pop("tool", None)
                    # Запрос подтверждения перед выполнением инструмента
                    if toolname and toolname in tool_map:
                        if self.confirmation_handler is None:
                            raise RuntimeError("No confirmation_handler set for Agent, cannot execute tools")
                        confirmed = self.confirmation_handler(toolname, json.dumps(action, ensure_ascii=False))
                        if not confirmed:
                            obs = f"Action '{reason}' cancelled by confirmation handler."
                        else:
                            tool = tool_map[toolname]
                            obs = tool(**action)
                    else:
                        obs = f"Tool '{toolname}' not found."
                except Exception as e:
                    obs = f"Error parsing action or invoking tool: {e}"
                # Observation handling: support image responses
                obs_msg = f"Observation: {obs}"
                # Add to message history
                self.messages.append({"role": "system", "content": obs_msg})
                process_trace.append("System:\n" + str(obs_msg))
            else:
                # No action found—continue
                continue

        # Always store the last trace for retrieval, regardless of return_trace or verbose
        self.last_trace = "\n\n".join(process_trace)

        # Optionally, return the last assistant message (should be the answer)
        if return_trace:
            # Show all process steps (everything that happened in this exec round)
            return self.last_trace
        else:
            for m in reversed(self.messages):
                if m["role"] == "assistant" and "Answer:" in m["content"]:
                    content = m["content"]
                    idx = content.find("Answer:")
                    if idx != -1:
                        # Return only what follows after 'Answer:'
                        answer = content[idx+len("Answer:"):].strip()
                        # Remove extra quotes if present
                        if answer.startswith('"') and answer.endswith('"'):
                            answer = answer[1:-1]
                        return answer
                    else:
                        return content
            # Fallback: return last LLM content
            return self.messages[-1]["content"]
        
    def image(self, url: str):
        self.messages.append(
            {
                "role": "user",
                "content": [{
                    "type": "image_url",
                    "image_url": {
                        "url": url
                    }
                }]
            }
        )

class Chat():
    def __init__(
        self, 
        client: object, 
        model: str, 
        system: str=None, 
        description: str="", 
        reset_messages: bool=False
        ):
        self.client = client
        self.model = model
        self.system = system
        self.__doc__ = description
        self.messages = []
        self.reset_messages = reset_messages
        self.reset()

    def __call__(self, message: str=None, role: str="user", call: bool=True, return_trace: bool=None):
        if self.reset_messages:
            self.reset()
        if message is not None:
            self.messages.append({"role": role, "content": message})
        if call == True:
            result = self.exec()
            self.messages.append({"role": "assistant", "content": result})
            return result

    def reset(self):
        self.messages = []
        if self.system is not None:
            self.messages.append({"role": "system", "content": self.system})

    def exec(self):
        response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
        )
        return response.choices[0].message.content
        
    def image(self, url: str):
        self.messages.append(
            {
                "role": "user",
                "content": [{
                    "type": "image_url",
                    "image_url": {
                        "url": url
                    }
                }]
            }
        )

class Classifier():
    def __init__(
        self, 
        client: object, 
        model: str, 
        categories: list, 
        description: str=""
        ):
        self.client = client
        self.model = model
        self.categories = categories
        self.__doc__ = description
        self.messages = [{"role": "system", "content": GetClassifierPrompt(self.categories)}]

    def __call__(self, message: str=None, role: str="user", call: bool=True):
        if message is not None:
            self.messages.append({"role": role, "content": message})
        if call == True:
            result = self.exec()
            return result

    def reset(self):
        self.messages = []


    def exec(self):
        response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
        )
        return response.choices[0].message.content
        
    def image(self, url: str):
        self.messages.append(
            {
                "role": "user",
                "content": [{
                    "type": "image_url",
                    "image_url": {
                        "url": url
                    }
                }]
            }
        )

def visualize_agent(agent, max_depth=3):
    """
    Render agent and its tools/sub-agents as a pretty graph in the terminal
    using 'rich'. Node numbers correspond to the list for viewing __doc__ strings.
    """

    console = Console()
    nodes = []

    def scan(obj, depth, parent_num):
        node_type = type(obj).__name__
        if node_type == "Agent":
            node_name = (
                getattr(obj, "__doc__", None) or
                "Agent"
            )
        else:
            node_name = getattr(obj, "name", None) or getattr(obj, "__name__", None) or node_type
        node_doc = getattr(obj, "__doc__", "") or "(No documentation)"
        node = {
            "type": node_type,
            "name": node_name,
            "doc": node_doc.strip(),
            "depth": depth,
            "parent_num": parent_num,
        }
        nodes.append(node)
        this_num = len(nodes)
        # For Tree rendering: return tree node
        label = f"[bold cyan]{this_num}.[/bold cyan] [green]{node_type}[/green] [yellow]{node_name}[/yellow]"
        tree = Tree(label)
        if hasattr(obj, 'tools') and isinstance(obj.tools, list) and depth < max_depth:
            for tool in obj.tools:
                child_tree = scan(tool, depth + 1, this_num)
                if child_tree:
                    tree.add(child_tree)
        return tree

    root_tree = scan(agent, depth=0, parent_num=0)

    console.print(Panel.fit(root_tree, title="Agent Graph", subtitle="Numbers correspond to node info below", border_style="blue"))

    # Print legend with numbers and type/name
    console.print("[bold]Node Legend:[/bold]")
    for idx, n in enumerate(nodes, 1):
        console.print(f"[bold cyan]{idx}.[/bold cyan] [green]{n['type']}[/green] [yellow]{n['name']}[/yellow]")

    while True:
        pick = Prompt.ask("\nEnter node number to view __doc__ (Enter to exit)", default="")
        if not pick.strip():
            break
        try:
            num = int(pick)
            if 1 <= num <= len(nodes):
                doc = nodes[num-1]["doc"] or "(No documentation)"
                console.print(Panel.fit(doc, title=f"Docstring for node {num}: {nodes[num-1]['name']}", subtitle=nodes[num-1]["type"], border_style="green"))
            else:
                console.print("[red]Invalid node number[/red]")
        except Exception:
            console.print("[red]Please enter a valid number[/red]")
