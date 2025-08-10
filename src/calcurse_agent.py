from rovoam import Agent
from client import client
from datetime import datetime

scheduler = Agent(
    client=client,
    model="openai-large",
    tools=[],
    system=f"You're an agent for task planning and scheduling. Today is {str(datetime.now().time)}"
)

