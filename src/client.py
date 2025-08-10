from openai import OpenAI
from config import config

client = OpenAI(api_key=config["api_key"], base_url=config["api_endpoint"])
