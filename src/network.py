from openai import OpenAI
from rovoam import Agent
from datetime import datetime
from confirmation import confirmation_handler
from calcurse_agent import scheduler

client = OpenAI(api_key="no", base_url="https://text.pollinations.ai/openai")

# Tools

# Agents

# Superviser Agent

supervisor = Agent(
    client=client, 
    model="openai", 
    system=f"You are Rovoam. An AGI and a universal AI. Your task is to manage other agents, coordinating their work. You must carefully plan the sequence of calls to gather all the necessary data for the next agent. You can use Markdown. Respond in the user's language unless they ask for something else. Now is {datetime.now()}.",
    tools=[],
    maxIterations=20,
    confirmation_handler=confirmation_handler
)
